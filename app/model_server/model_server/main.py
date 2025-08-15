import json
import shutil
import uuid
import os
import logging
import time
import glob
from pathlib import Path
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import docker
from pymongo import MongoClient
from typing import List, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
client = docker.from_env()

# === MongoDB connection ===
MONGO_HOST = os.environ.get("MODEL_SERVER_MONGO_HOST", "model_server_db")
MONGO_PORT = int(os.environ.get("MODEL_SERVER_MONGO_PORT", 27017))
MONGO_DB = os.environ.get("MODEL_SERVER_MONGO_DB", "modeldb")

mongo_client = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
db = mongo_client[MONGO_DB]
models_collection = db.models

# Path to built-in model metadata
BUILTIN_MODELS_PATH = os.environ.get("BUILTIN_MODELS_PATH", "/app/builtin_models")

class RegisterRequest(BaseModel):
    image: str  # e.g., "irismodel:1.0.0"
    title: str
    short_description: str
    authors: str
    examples: List[Any]
    readme: str

def wait_for_mongodb():
    """Wait for MongoDB to be ready"""
    max_retries = 30
    for attempt in range(max_retries):
        try:
            mongo_client.admin.command('ping')
            logger.info("MongoDB is ready")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                logger.info(f"Waiting for MongoDB... (attempt {attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                logger.error(f"Failed to connect to MongoDB after {max_retries} attempts: {e}")
                raise

def _register_model_internal(metadata: dict) -> dict:
    """Internal model registration function that can be called during startup"""
    image = metadata["image"]
    
    # 1. Check if image exists locally
    try:
        client.images.get(image)
        logger.info(f"Found local image: {image}")
    except Exception as e:
        logger.error(f"Image not found locally: {image} - {e}")
        raise Exception(f"Image not found locally: {image}")

    temp_json_path = None
    try:
        # Write provided examples to /shared-tmp as a temp file
        temp_json_path = os.path.join("/shared-tmp", f"examples_{uuid.uuid4().hex}.json")
        with open(temp_json_path, "w") as tf:
            json.dump(metadata["examples"], tf)
            tf.flush()

        # Try running prediction using the provided examples as test input
        logger.info(f"Testing model {image} with examples...")
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
            logger.info(f"Model {image} test successful")
        except Exception as e:
            logger.error(f"Model {image} prediction did not return valid JSON: {e}. Output was: {output.decode()}")
            raise Exception(f"Prediction did not return valid JSON: {e}")

        # Store in MongoDB
        doc = {
            "image": image,
            "title": metadata["title"],
            "short_description": metadata["short_description"],
            "authors": metadata["authors"],
            "readme": metadata["readme"],
            "examples": metadata["examples"]
        }
        # Upsert (replace if exists, insert if new)
        models_collection.replace_one({"image": image}, doc, upsert=True)
        logger.info(f"Successfully registered model: {image}")

        return {"status": "ok", "image": image, "example_predictions": preds}
    except Exception as e:
        logger.error(f"Registration failed for {image}: {e}")
        raise
    finally:
        if temp_json_path and os.path.exists(temp_json_path):
            os.remove(temp_json_path)

def load_builtin_models():
    """Load and register built-in models from metadata files"""
    logger.info("Starting auto-registration of built-in models...")
    
    if not os.path.exists(BUILTIN_MODELS_PATH):
        logger.warning(f"Built-in models path does not exist: {BUILTIN_MODELS_PATH}")
        return
    
    # Find all model_metadata.json files
    metadata_files = glob.glob(os.path.join(BUILTIN_MODELS_PATH, "*/model_metadata.json"))
    
    if not metadata_files:
        logger.warning(f"No model metadata files found in: {BUILTIN_MODELS_PATH}")
        return
    
    registered_count = 0
    failed_count = 0
    
    for metadata_file in metadata_files:
        model_name = Path(metadata_file).parent.name
        try:
            logger.info(f"Loading metadata for model: {model_name}")
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            # Register the model
            _register_model_internal(metadata)
            registered_count += 1
            
        except Exception as e:
            logger.error(f"Failed to register built-in model {model_name}: {e}")
            failed_count += 1
    
    logger.info(f"Built-in model registration complete: {registered_count} successful, {failed_count} failed")
    
    if failed_count > 0:
        raise Exception(f"Failed to register {failed_count} built-in models")

@app.on_event("startup")
async def startup_event():
    """Initialize built-in models on startup"""
    logger.info("Model server starting up...")
    
    # Wait for MongoDB to be ready
    wait_for_mongodb()
    
    # Load and register built-in models
    try:
        load_builtin_models()
        logger.info("Model server startup complete")
    except Exception as e:
        logger.error(f"Failed to load built-in models: {e}")
        # Don't fail startup, but log the error
        # In production, you might want to fail startup instead

@app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        # Check MongoDB connection
        mongo_client.admin.command('ping')
        
        # Check if we have any models registered
        model_count = models_collection.count_documents({})
        
        return {
            "status": "healthy",
            "models_registered": model_count,
            "mongodb_connected": True
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "mongodb_connected": False
        }

@app.post("/models")
def register_model(req: RegisterRequest):
    """Register a model via API"""
    try:
        # Convert request to metadata dict
        metadata = {
            "image": req.image,
            "title": req.title,
            "short_description": req.short_description,
            "authors": req.authors,
            "examples": req.examples,
            "readme": req.readme
        }
        
        # Try to pull image if not available locally
        try:
            client.images.pull(req.image)
        except Exception:
            pass  # Image might already be local
        
        return _register_model_internal(metadata)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {e}")

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
