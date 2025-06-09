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

# Create unique index on (author_slug, name_slug, version)
db.models.create_index(
    [("author_slug", 1), ("name_slug", 1), ("version", 1)], unique=True
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

        # Duplication check (MongoDB unique index also enforces this, but let's be user-friendly)
        if db.models.find_one({"author_slug": author_slug, "name_slug": name_slug, "version": version}):
            raise HTTPException(
                status_code=400,
                detail="Model with this author, name, and version already exists."
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

REQUIRED_FIELDS = ["name", "author", "version", "description", "tags"]
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
    # You can make author flexible, but could check for email here if you want
    if not isinstance(metadata["tags"], list):
        raise HTTPException(status_code=400, detail="Tags must be a list.")
    if not isinstance(metadata["version"], str):
        raise HTTPException(status_code=400, detail="Version must be a string.")
