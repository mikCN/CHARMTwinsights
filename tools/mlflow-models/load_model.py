import tarfile
import mlflow.pyfunc
import os

# === CONFIG ===
archive_path = "model_export.tar.gz"
extract_path = "model_extracted"

# === STEP 1: Extract the .tar.gz file ===
with tarfile.open(archive_path, "r:gz") as tar:
    tar.extractall(path=extract_path)

# Path to extracted MLflow model directory
model_path = os.path.join(extract_path, "model_export")

# === STEP 2: Load model using mlflow.pyfunc ===
model = mlflow.pyfunc.load_model(model_path)

# === STEP 3: Print metadata ===
print("\n--- Model Info ---")
print(f"Path: {model_path}")
print(f"Python model class: {type(model)}")

print("\n--- Model Signature ---")
try:
    input_schema = model.metadata.get_input_schema()
    print("Input schema:", input_schema)
    output_schema = model.metadata.get_output_schema()
    print("Output schema:", output_schema)
except Exception as e:
    print("No signature found:", e)

print("\n--- Model Artifact URI ---")
print(model.metadata.artifact_path)
