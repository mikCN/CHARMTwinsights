# file: app/mlflow_server/tests/build_model.py

## This script trains a logistic regression model on the Iris and Wine datasets,
## saves it using MLflow, adds metadata, and packages it into a zip file.
## We expect these 'packages' to be sent to the model serving API for deployment.

import os
import zipfile
import shutil
import json
import mlflow.sklearn
from mlflow.models.signature import infer_signature
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.datasets import load_iris, load_wine
import pandas as pd

EXPORT_DIR = "model_exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

def train_model(dataset_func, model_name: str):
    data = dataset_func(as_frame=True)
    X = data.data
    y = data.target
    X_train, X_test, y_train, y_test = train_test_split(X, y)
    model = LogisticRegression(max_iter=250, solver="liblinear")  # fast & compatible
    model.fit(X_train, y_train)
    return model, X_train, X_test, model_name

def save_mlflow_model(model, X_train, model_name: str):
    signature = infer_signature(X_train, model.predict(X_train))
    model_dir = os.path.join(EXPORT_DIR, f"{model_name}_export")
    mlflow.sklearn.save_model(
        sk_model=model,
        path=model_dir,
        signature=signature
    )
    return model_dir

def write_metadata(model_dir, metadata: dict):
    metadata_path = os.path.join(model_dir, "model_metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

def archive_model(model_dir: str):
    archive_path = f"{model_dir}.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(model_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, os.path.dirname(model_dir))
                zipf.write(abs_path, rel_path)
    print(f"Packaged model: {archive_path}")
    return archive_path

def main():
    for dataset_func, model_name in [
        (load_iris, "iris_model"),
        (load_wine, "wine_model")
    ]:
        model, X_train, X_test, name = train_model(dataset_func, model_name)
        model_dir = save_mlflow_model(model, X_train, name)
        # Add user-editable metadata - all required, tags can be empty
        signature = infer_signature(X_train, model.predict(X_train))
        signature_dict = signature.to_dict() if signature else None
        metadata = {
            "name": name,
            "author": "Shawn O'Neil",
            "description": f"A logistic regression classifier for {name.replace('_model', '')} data.",
            "version": "1.0.0",
            "tags": [name, "sklearn", "logreg", "example"],
            "signature": signature_dict  # <-- required and always present
        }

        write_metadata(model_dir, metadata)
        archive_model(model_dir)
        # Remove the model directory after archiving
        shutil.rmtree(model_dir)

if __name__ == "__main__":
    main()
