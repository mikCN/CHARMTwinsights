import json
import shutil
import uuid
import os
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import docker
from pymongo import MongoClient
from typing import List, Any

app = FastAPI()
client = docker.from_env()

# === MongoDB connection ===
MONGO_HOST = os.environ.get("MODEL_SERVER_MONGO_HOST", "mongo_model_server")
MONGO_PORT = int(os.environ.get("MODEL_SERVER_MONGO_PORT", 27017))
MONGO_DB = os.environ.get("MODEL_SERVER_MONGO_DB", "modeldb")

mongo_client = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
db = mongo_client[MONGO_DB]
models_collection = db.models

class RegisterRequest(BaseModel):
    image: str  # e.g., "irismodel:1.0.0"
    title: str
    short_description: str
    authors: str
    examples: List[Any]
    readme: str

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

    temp_json_path = None
    try:
        # Write provided examples to /shared-tmp as a temp file
        temp_json_path = os.path.join("/shared-tmp", f"examples_{uuid.uuid4().hex}.json")
        with open(temp_json_path, "w") as tf:
            json.dump(req.examples, tf)
            tf.flush()

        # Try running prediction using the provided examples as test input
        output = client.containers.run(
            image,
            command=["./predict", f"/shared-tmp/{os.path.basename(temp_json_path)}"],
            volumes={
                "app_shared_tmp": {"bind": "/shared-tmp", "mode": "rw"}
            },
            remove=True,
            stdout=True,
            stderr=False
        )

        try:
            preds = json.loads(output.decode())
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Prediction did not return valid JSON: {e}. Output was: {output.decode()}")

        # Store in MongoDB
        doc = {
            "image": image,
            "title": req.title,
            "short_description": req.short_description,
            "authors": req.authors,
            "readme": req.readme,
            "examples": req.examples
        }
        # Upsert (replace if exists, insert if new)
        models_collection.replace_one({"image": image}, doc, upsert=True)

        return {"status": "ok", "image": image, "example_predictions": preds}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {e}")
    finally:
        if temp_json_path and os.path.exists(temp_json_path):
            os.remove(temp_json_path)

@app.post("/predict")
def predict(
    image: str = Body(..., embed=True),
    input: List[Any] = Body(..., embed=True)
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
            stderr=False
        )
        preds = json.loads(output.decode())
        return {"predictions": preds}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}. Output was: {output.decode() if output else 'No output'}")
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/models")
def list_models():
    # Return all models with core metadata (not including README)
    models = []
    for m in models_collection.find({}, {"_id": 0}):
        models.append({
            "image": m["image"],
            "title": m.get("title", ""),
            "short_description": m.get("short_description", ""),
            "authors": m.get("authors", ""),
            "examples": m.get("examples", []),
        })
    return models

@app.get("/models/{image_tag}")
def model_info(image_tag: str):
    m = models_collection.find_one({"image": image_tag})
    if not m:
        raise HTTPException(status_code=404, detail="Model not found")
    # Build response with all metadata, including README
    return {
        "image": m["image"],
        "title": m.get("title", ""),
        "short_description": m.get("short_description", ""),
        "authors": m.get("authors", ""),
        "examples": m.get("examples", []),
        "readme": m.get("readme", ""),
    }
