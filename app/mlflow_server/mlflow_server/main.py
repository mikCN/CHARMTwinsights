## file: app/mlflow_server/mlflow_server/main.py

## OVERVIEW
# This is a FastAPI application that serves as a simple ML model registry.
# It allows users to upload ML models in a zip format, stores metadata in MongoDB,
# and saves the actual model files in MinIO (an S3-compatible object storage).
# The application provides endpoints to list models, get model details, and upload new models.

# PLANNED FEATURES
# Add signature information provided by mlflow to mongo db for use in GETs of model details
# Model deletion
# Model prediction endpoint

# Model prediction will be handled by mlflow, but it is yet to be determined exactly how.
# Options:
#  - use mlflow's built-in serving capabilities; this is difficult because we want to multiple serve models via this singlular API, not on different ports (unless that can be figured out)
#  - use the mlflow command-line applicaton and run a subprocess to serve the model; to be determined if on sync or async endpoint
#  - load models in memory using the same environment as this API


# Challenges with model prediction serving:
#  - mlflow models specify their dependencies in a conda.yaml; isolating and managing virtual envs allows different dependencies sets, but adds complexity 
#  - because models and their environments may be large, we may need to handle model loading and unloading dynamically and efficiently
#  - because it may take time to load a model and/or install its dependencies, we may need a model 'status' endpoint to check if a model is ready
#  - we'll need to be able to handle concurrent requests


import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from pymongo import MongoClient
from minio import Minio
from minio.error import S3Error
from bson import ObjectId
import io
import tempfile
import zipfile
import json
import re
from fastapi import HTTPException
from fastapi import Path
from packaging.version import Version, InvalidVersion
from fastapi import status



# === ENV VARS / CONFIG ===
MONGO_HOST = os.environ.get("MONGO_HOST", "mongo")
MONGO_PORT = int(os.environ.get("MONGO_PORT", 27017))
MONGO_DB = os.environ.get("MONGO_DB", "mlflowdb")

MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minio")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minio123")
MINIO_BUCKET = os.environ.get("MINIO_BUCKET", "models")

# === INIT CLIENTS ===
mongo_client = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
db = mongo_client[MONGO_DB]

# Create unique index on name and version
db.models.create_index(
    [("name_slug", 1), ("version", 1)], unique=True
)



minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# Ensure bucket exists
if not minio_client.bucket_exists(MINIO_BUCKET):
    minio_client.make_bucket(MINIO_BUCKET)

app = FastAPI()


def serialize_metadata(doc):
    # Helper: Converts Mongo _id to str and removes internal fields
    out = dict(doc)
    out["model_id"] = str(out.pop("_id"))
    out.pop("minio_key", None)  # Optional: don't expose internal storage
    return out


@app.delete("/models/{model_name}/{version}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model_version(
    model_name: str = Path(..., description="The model name (not slug)"),
    version: str = Path(..., description="The version string")
):
    name_slug = slugify(model_name)
    m = db.models.find_one({"name_slug": name_slug, "version": version})
    if not m:
        raise HTTPException(status_code=404, detail="Model version not found.")

    # Delete file from MinIO
    minio_key = m.get("minio_key")
    if minio_key:
        try:
            minio_client.remove_object(MINIO_BUCKET, minio_key)
        except S3Error:
            pass  # You may want to handle/log

    # Delete metadata from MongoDB
    db.models.delete_one({"_id": m["_id"]})
    return  # 204 No Content



@app.get("/models")
def list_models():
    """List all models (latest version only per model name)."""
    # Group by name_slug, select latest version for each
    models = list(db.models.find())
    result = {}
    for m in models:
        key = m["name_slug"]
        try:
            v = Version(m["version"])
        except InvalidVersion:
            v = m["version"]
        if key not in result or v > result[key][1]:
            result[key] = (m, v)
    return [serialize_metadata(m[0]) for m in result.values()]

@app.get("/models/{model_name}")
def get_latest_model(model_name: str = Path(..., description="The model name (not slug)")):
    name_slug = slugify(model_name)
    # Get all versions for this model, select the latest
    versions = list(db.models.find({"name_slug": name_slug}))
    if not versions:
        raise HTTPException(status_code=404, detail="Model not found.")
    # Sort by version (semantic)
    try:
        latest = max(versions, key=lambda m: Version(m["version"]))
    except Exception:
        # Fallback: lexicographic sort
        latest = max(versions, key=lambda m: m["version"])
    return serialize_metadata(latest)

@app.get("/models/{model_name}/{version}")
def get_model_version(
    model_name: str = Path(..., description="The model name (not slug)"),
    version: str = Path(..., description="The version string"),
):
    name_slug = slugify(model_name)
    m = db.models.find_one({"name_slug": name_slug, "version": version})
    if not m:
        raise HTTPException(status_code=404, detail="Model version not found.")
    return serialize_metadata(m)




@app.post("/models")
async def upload_model(file: UploadFile = File(...)):
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, file.filename)
        with open(zip_path, "wb") as f:
            f.write(await file.read())

        # Unzip for validation
        with zipfile.ZipFile(zip_path, "r") as zipf:
            zipf.extractall(tmpdir)
            # Find model_metadata.json
            meta_path = None
            for root, dirs, files in os.walk(tmpdir):
                if "model_metadata.json" in files:
                    meta_path = os.path.join(root, "model_metadata.json")
                    break
            if not meta_path:
                raise HTTPException(status_code=400, detail="model_metadata.json not found in zip.")
            with open(meta_path, "r") as mf:
                metadata = json.load(mf)

        # Validate and slugify
        validate_metadata(metadata)
        author_slug = slugify(metadata["author"])
        name_slug = slugify(metadata["name"])
        version = metadata["version"]

        # Duplication & Ownership check
        existing_versions = list(db.models.find({"name_slug": name_slug}))

        if not existing_versions:
            # This is the first use of the name_slug; allow upload.
            pass
        else:
            # Name slug already used, must match author, and version must not exist.
            owners = set(m["author_slug"] for m in existing_versions)
            if author_slug not in owners:
                raise HTTPException(
                    status_code=400,
                    detail=f"Model name '{metadata['name']}' is already owned by another author."
                )
            # Now check for duplicate version for this author
            if db.models.find_one({"name_slug": name_slug, "version": version}):
                raise HTTPException(
                    status_code=400,
                    detail=f"Model '{metadata['name']}' version '{version}' already exists for this author."
                )


        # Store the model zip file in MinIO
        minio_key = f"{author_slug}/{name_slug}/{version}/{file.filename}"
        with open(zip_path, "rb") as zip_stream:
            minio_client.put_object(
                MINIO_BUCKET,
                minio_key,
                data=zip_stream,
                length=os.path.getsize(zip_path),
                content_type="application/zip"
            )

        # Save metadata to MongoDB
        metadata_db = {
            **metadata,
            "author_slug": author_slug,
            "name_slug": name_slug,
            "minio_key": minio_key,
            "filename": file.filename,
        }
        model_id = db.models.insert_one(metadata_db).inserted_id

        metadata_db = dict(metadata_db)
        metadata_db.pop("_id", None)
        return {
            "status": "ok",
            "model_id": str(model_id),
            "metadata": metadata_db
        }



@app.get("/test/mongo")
def test_mongo():
    test_coll = db["test"]
    test_doc = {"msg": "Hello from MongoDB"}
    result = test_coll.insert_one(test_doc)
    fetched = test_coll.find_one({"_id": result.inserted_id})

    # Convert ObjectId to string for JSON
    if "_id" in fetched:
        fetched["_id"] = str(fetched["_id"])

    return {"inserted": str(result.inserted_id), "fetched": fetched}


@app.post("/test/minio/upload")
async def test_minio_upload(file: UploadFile = File(...)):
    file_bytes = await file.read()
    try:
        # Wrap bytes in a BytesIO stream
        data_stream = io.BytesIO(file_bytes)
        minio_client.put_object(
            MINIO_BUCKET,
            file.filename,
            data=data_stream,
            length=len(file_bytes),
            content_type=file.content_type or "application/octet-stream"
        )
        return {"status": "uploaded", "filename": file.filename}
    except S3Error as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/test/minio/download/{filename}")
def test_minio_download(filename: str):
    """Download a file from MinIO."""
    try:
        obj = minio_client.get_object(MINIO_BUCKET, filename)
        content = obj.read()
        return {"filename": filename, "size": len(content)}
    except S3Error as e:
        raise HTTPException(status_code=404, detail=str(e))



########## Utility Functions ##########

def slugify(value: str) -> str:
    # Lowercase, replace spaces/punct with underscores, remove anything not a-z, 0-9, or underscore
    value = value.lower()
    value = re.sub(r"[^\w]+", "_", value)
    value = value.strip("_")
    return value

REQUIRED_FIELDS = ["name", "author", "version", "description", "tags", "signature"]
def validate_metadata(metadata: dict):
    # Check presence
    for field in REQUIRED_FIELDS:
        if field not in metadata or not metadata[field]:
            raise HTTPException(
                status_code=400,
                detail=f"Metadata field '{field}' is required."
            )
    # Format checks
    if not re.match(r"^[a-zA-Z0-9_\- ]+$", metadata["name"]):
        raise HTTPException(status_code=400, detail="Model name must be alphanumeric, spaces, underscores, or hyphens.")
    if not isinstance(metadata["tags"], list):
        raise HTTPException(status_code=400, detail="Tags must be a list.")
    if not isinstance(metadata["version"], str):
        raise HTTPException(status_code=400, detail="Version must be a string.")
    if not isinstance(metadata["signature"], dict):
        raise HTTPException(
            status_code=400,
            detail="Signature must be a dict (as generated by MLflow signature tools)."
        )
    # Optional: check for MLflow's expected structure
    if "inputs" not in metadata["signature"] or "outputs" not in metadata["signature"]:
        raise HTTPException(
            status_code=400,
            detail="Signature must include 'inputs' and 'outputs' as generated by MLflow."
        )

