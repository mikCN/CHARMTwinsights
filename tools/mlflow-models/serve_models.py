import os
import tarfile
import mlflow.pyfunc
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uvicorn

MODEL_DIR = "models"
EXTRACTED_DIR = "models_extracted"

app = FastAPI()
loaded_models = {}

# === Load and extract all .tar.gz models ===
os.makedirs(EXTRACTED_DIR, exist_ok=True)

for fname in os.listdir(MODEL_DIR):
    if fname.endswith(".tar.gz"):
        model_name = fname.replace("_export.tar.gz", "")
        extract_path = os.path.join(EXTRACTED_DIR, model_name)
        os.makedirs(extract_path, exist_ok=True)

        with tarfile.open(os.path.join(MODEL_DIR, fname), "r:gz") as tar:
            tar.extractall(path=extract_path)

        # Load with mlflow.pyfunc
        model_path = os.path.join(extract_path, f"{model_name}_export")
        loaded_models[model_name] = mlflow.pyfunc.load_model(model_path)

# === Request body for predictions ===
class InferenceRequest(BaseModel):
    data: List[Dict[str, Any]]

# === Endpoints ===

@app.get("/models")
def list_models():
    return {"models": list(loaded_models.keys())}

@app.get("/models/{model_name}")
def model_info(model_name: str):
    if model_name not in loaded_models:
        raise HTTPException(status_code=404, detail="Model not found")

    model = loaded_models[model_name]
    meta = model.metadata

    return {
        "model_name": model_name,
        "artifact_path": meta.artifact_path,
        "utc_time_created": meta.utc_time_created,
        "flavors": meta.flavors,
        "run_id": meta.run_id,
        "input_schema": str(meta.get_input_schema().to_dict() if meta.get_input_schema() else None),
        "output_schema": str(meta.get_output_schema().to_dict() if meta.get_output_schema() else None),
    }

@app.post("/predict/{model_name}")
def predict(model_name: str, request: InferenceRequest):
    if model_name not in loaded_models:
        raise HTTPException(status_code=404, detail="Model not found")

    model = loaded_models[model_name]
    try:
        input_df = pd.DataFrame(request.data)
        preds = model.predict(input_df)
        return {"predictions": preds.tolist()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Inference error: {str(e)}")

# === Run locally ===
if __name__ == "__main__":
    uvicorn.run("serve_models:app", host="0.0.0.0", port=8000, reload=True)
