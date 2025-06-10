#!/bin/bash

# file: app/mlflow_server/tests/query_metadata.sh

# This testing script queries the MLflow server for model metadata.

set -e

BASEURL="localhost:8003"

echo "=== List all models (latest version only) ==="
curl -s "$BASEURL/models"
echo
echo

MODEL_NAME="iris_model"
VERSION="1.0.0"

echo "=== Get latest version of $MODEL_NAME ==="
curl -s "$BASEURL/models/$MODEL_NAME"
echo
echo

echo "=== Get $MODEL_NAME version $VERSION ==="
curl -s "$BASEURL/models/$MODEL_NAME/$VERSION"
echo
echo