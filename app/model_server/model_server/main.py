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

def _run_model_container(image: str, input_data: any) -> dict:
    """Run a model container with file-based I/O and capture stdout/stderr"""
    session_id = uuid.uuid4().hex
    input_file = f"input_{session_id}.json"
    output_file = f"output_{session_id}.json"
    
    input_path = os.path.join("/shared-tmp", input_file)
    output_path = os.path.join("/shared-tmp", output_file)
    
    try:
        # Write input data to file
        with open(input_path, "w") as f:
            json.dump(input_data, f)
            f.flush()

        # Run the model container with both input and output file paths
        logger.info(f"Running model {image} with file-based I/O...")
        
        # First try the new file-based I/O pattern
        try:
            container_result = client.containers.run(
                image,
                command=["./predict", f"/shared-tmp/{input_file}", f"/shared-tmp/{output_file}"],
                volumes={
                    "app_shared_tmp": {"bind": "/shared-tmp", "mode": "rw"}
                },
                remove=True,
                stdout=True,
                stderr=True,
                detach=False
            )
            
            # Check if output file was created (new pattern worked)
            if os.path.exists(output_path):
                logger.info(f"Model {image} uses new file-based I/O pattern")
                new_pattern_used = True
            else:
                raise Exception("Model did not create output file - falling back to legacy pattern")
                
        except Exception as e:
            logger.warning(f"New I/O pattern failed for {image}, trying legacy pattern: {e}")
            new_pattern_used = False
            
            # Fallback to old stdout-based pattern
            container_result = client.containers.run(
                image,
                command=["./predict", f"/shared-tmp/{input_file}"],
                volumes={
                    "app_shared_tmp": {"bind": "/shared-tmp", "mode": "rw"}
                },
                remove=True,
                stdout=True,
                stderr=True,
                detach=False
            )
            
            # Parse predictions from stdout (legacy pattern)
            try:
                stdout_output = container_result.decode('utf-8') if container_result else ""
                predictions = json.loads(stdout_output.strip())
                
                # Create output file for consistency
                with open(output_path, 'w') as f:
                    json.dump(predictions, f)
                    
                logger.info(f"Model {image} uses legacy stdout pattern - converted to file-based")
            except json.JSONDecodeError as json_err:
                raise Exception(f"Legacy pattern failed - stdout is not valid JSON: {json_err}")
        
        # Capture and parse stdout/stderr from container result
        raw_output = container_result.decode('utf-8') if container_result else ""
        
        # Try to split stdout/stderr based on simple heuristics
        # In new pattern, models should send informational messages to stderr
        # and only results to stdout
        lines = raw_output.split('\n')
        stdout_lines = []
        stderr_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:  # Skip empty lines
                continue
                
            # Simple heuristic: lines with certain patterns go to stderr
            stderr_indicators = [
                'Loading', 'Processing', 'Generated', 'written to', 'Error:', 'Warning:',
                'Model loaded', 'Completed processing', 'records', 'Starting', 'Successfully generated'
            ]
            
            if any(phrase in line for phrase in stderr_indicators):
                stderr_lines.append(line)
            else:
                stdout_lines.append(line)
        
        stdout_output = '\n'.join(stdout_lines).strip()
        stderr_output = '\n'.join(stderr_lines).strip()

        # Read predictions from output file
        if not os.path.exists(output_path):
            raise Exception(f"Model did not create output file: {output_file}")
        
        with open(output_path, 'r') as f:
            predictions = json.load(f)
        
        logger.info(f"Model {image} execution successful")
        
        return {
            "predictions": predictions,
            "stdout": stdout_output,
            "stderr": stderr_output,
            "model_logs": {
                "input_file": input_file,
                "output_file": output_file,
                "session_id": session_id
            }
        }
        
    except json.JSONDecodeError as e:
        raise Exception(f"Model output file contains invalid JSON: {e}")
    except Exception as e:
        # If output file doesn't exist, try to get any error info from stdout
        error_info = container_result.decode('utf-8') if 'container_result' in locals() else "No output"
        raise Exception(f"Model execution failed: {e}. Container output: {error_info}")
    finally:
        # Clean up temporary files
        for temp_file in [input_path, output_path]:
            if os.path.exists(temp_file):
                os.remove(temp_file)

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

    try:
        # Test the model with provided examples
        logger.info(f"Testing model {image} with examples...")
        result = _run_model_container(image, metadata["examples"])
        
        preds = result["predictions"]
        logger.info(f"Model {image} test successful")
        
        # Log any stderr output during registration
        if result["stderr"]:
            logger.info(f"Model {image} stderr during registration: {result['stderr']}")

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

        return {
            "status": "ok", 
            "image": image, 
            "example_predictions": preds,
            "registration_logs": {
                "stdout": result["stdout"],
                "stderr": result["stderr"]
            }
        }
    except Exception as e:
        logger.error(f"Registration failed for {image}: {e}")
        raise

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
    """Make a prediction using a registered model with file-based I/O"""
    # 1. Confirm the model is registered
    m = models_collection.find_one({"image": image})
    if not m:
        raise HTTPException(status_code=404, detail="Model not registered")

    # 2. Run the model with file-based I/O
    try:
        result = _run_model_container(image, input)
        return {
            "predictions": result["predictions"],
            "stdout": result["stdout"],
            "stderr": result["stderr"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

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
