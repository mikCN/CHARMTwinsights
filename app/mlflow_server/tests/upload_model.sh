#!/bin/bash
MODEL_ZIP="model_exports/iris_model_export.zip"

curl -X POST "localhost:8003/models" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@${MODEL_ZIP}"
