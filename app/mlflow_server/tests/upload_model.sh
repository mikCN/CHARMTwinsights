#!/bin/bash

# file: app/mlflow_server/tests/upload_model.sh
# This script uploads a 'packaged' model to the MLflow server.

MODEL_ZIP="model_exports/iris_model_export.zip"

curl -X POST "localhost:8003/models" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@${MODEL_ZIP}"
