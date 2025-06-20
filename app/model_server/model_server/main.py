import json
import shutil
import uuid
import os
import tarfile
import io
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import docker
from pymongo import MongoClient
from typing import List, Any

app = FastAPI()
client = docker.from_env()

# === MongoDB connection ===
MONGO_HOST = os.environ.get("MONGO_HOST", "mongo")
MONGO_PORT = int(os.environ.get("MONGO_PORT", 27017))
MONGO_DB = os.environ.get("MONGO_DB", "modeldb")

mongo_client = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
db = mongo_client[MONGO_DB]
models_collection = db.models

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
        try:
            client.images.get(image)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Image not found locally or in registry: {e}")

    container = client.containers.create(image)
    tempdir = f"/tmp/modelreg_{uuid.uuid4().hex}"
    os.makedirs(tempdir, exist_ok=True)
    temp_json_path = None
    try:
        ex_path = os.path.join(tempdir, "examples.json")
        readme_path = os.path.join(tempdir, "README.md")
        extract_file(container, "/app/examples.json", ex_path)
        extract_file(container, "/app/README.md", readme_path)

        temp_json_path = os.path.join("/shared-tmp", f"examples_{uuid.uuid4().hex}.json")
        with open(ex_path, "r") as f:
            ex_json = json.load(f)
        with open(temp_json_path, "w") as tf:
            json.dump(ex_json, tf)
            tf.flush()

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

        with open(readme_path, "r") as f:
            readme = f.read()

        # Store in MongoDB
        doc = {
            "image": image,
            "readme": readme,
            "examples": ex_json
        }
        # Upsert (replace if exists, insert if new)
        models_collection.replace_one({"image": image}, doc, upsert=True)

        return {"status": "ok", "image": image, "predictions": preds}
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=400, detail=f"Missing file: {fnf}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {e}")
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)
        container.remove()
        if temp_json_path and os.path.exists(temp_json_path):
            os.remove(temp_json_path)

@app.get("/models")
def list_models():
    # List all models (just show image names for brevity)
    return [m["image"] for m in models_collection.find({}, {"_id": 0, "image": 1})]

@app.get("/models/{image_tag}")
def model_info(image_tag: str):
    m = models_collection.find_one({"image": image_tag})
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    m.pop("_id", None)  # Remove Mongo's internal ID for cleaner output
    return m

@app.get("/models/{image_tag}/readme")
def get_model_readme(image_tag: str):
    m = models_collection.find_one({"image": image_tag})
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"readme": m.get("readme", "")}

@app.get("/models/{image_tag}/examples")
def get_model_examples(image_tag: str):
    m = models_collection.find_one({"image": image_tag})
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"examples": m.get("examples", [])}



@app.post("/predict")
def predict(
    image: str = Body(..., embed=True),
    input: List[Any] = Body(..., embed=True)  # can also use `input: list | dict = Body(...)` for flexibility
):
    # 1. Confirm the model is registered
    m = models_collection.find_one({"image": image})
    if not m:
        raise HTTPException(status_code=404, detail="Model not registered")

    # 2. Write input to /shared-tmp as a temp file
    temp_filename = f"input_{uuid.uuid4().hex}.json"
    temp_path = os.path.join("/shared-tmp", temp_filename)
    with open(temp_path, "w") as f:
        json.dump(input, f)
        f.flush()

    # 3. Run the model container to generate prediction
    try:
        output = client.containers.run(
            image,
            command=["./predict", f"/shared-tmp/{temp_filename}"],
            volumes={
                "app_shared_tmp": {"bind": "/shared-tmp", "mode": "rw"}
            },
            remove=True,
            stdout=True,
            stderr=True
        )
        preds = json.loads(output.decode())
        return {"predictions": preds}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
