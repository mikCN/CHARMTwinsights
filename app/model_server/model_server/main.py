import json
import shutil
import uuid
import os
import tarfile
import io
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import docker

app = FastAPI()
client = docker.from_env()

registered_models = {}

class RegisterRequest(BaseModel):
    image: str  # e.g., "irismodel:1.0.0"

def extract_file(container, path, dest):
    bits, stat = container.get_archive(path)
    with tarfile.open(fileobj=io.BytesIO(b''.join(bits))) as tar:
        for member in tar.getmembers():
            f = tar.extractfile(member)
            if f:
                with open(dest, "wb") as out:
                    out.write(f.read())
                return
    raise FileNotFoundError(f"{path} not found in container.")

@app.post("/models")
def register_model(req: RegisterRequest):
    image = req.image
    # 1. Pull image (if needed)
    try:
        client.images.pull(image)
    except Exception:
        # Try to use local image if pull fails
        try:
            client.images.get(image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image not found locally or in registry: {e}")

    # 2. Create container (don't start)
    container = client.containers.create(image)
    tempdir = f"/tmp/modelreg_{uuid.uuid4().hex}"
    os.makedirs(tempdir, exist_ok=True)
    temp_json_path = None
    try:
        # 3. Extract examples.json and README.md
        ex_path = os.path.join(tempdir, "examples.json")
        readme_path = os.path.join(tempdir, "README.md")
        extract_file(container, "/app/examples.json", ex_path)
        extract_file(container, "/app/README.md", readme_path)

        # 3b. Write a temp copy in /shared-tmp for Docker handoff
        temp_json_path = os.path.join("/shared-tmp", f"examples_{uuid.uuid4().hex}.json")
        with open(ex_path, "r") as f:
            ex_json = json.load(f)
        with open(temp_json_path, "w") as tf:
            json.dump(ex_json, tf)
            tf.flush()

        # 4. Validate predict runs
        output = client.containers.run(
            image,
            command=["./predict", f"/shared-tmp/{os.path.basename(temp_json_path)}"],
            volumes={
                "app_shared_tmp": {"bind": "/shared-tmp", "mode": "rw"}
            },
            remove=True,
            stdout=True,
            stderr=True
        )

        try:
            preds = json.loads(output.decode())
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Prediction did not return valid JSON: {e}")

        # 5. Register model
        with open(readme_path, "r") as f:
            readme = f.read()
        registered_models[image] = {
            "readme": readme,
            "examples": ex_json
        }
        return {"status": "ok", "image": image, "predictions": preds}
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=400, detail=f"Missing file: {fnf}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {e}")
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)
        container.remove()
        # Remove temp shared file
        if temp_json_path and os.path.exists(temp_json_path):
            os.remove(temp_json_path)

@app.get("/models")
def list_models():
    return list(registered_models.keys())

@app.get("/models/{image_tag}")
def model_info(image_tag: str):
    model = registered_models.get(image_tag)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model
