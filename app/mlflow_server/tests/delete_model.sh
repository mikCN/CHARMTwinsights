#!/bin/bash

# file: app/mlflow_server/tests/delete_model.sh
# Usage: ./delete_model.sh [MODEL_NAME] [VERSION]
# Example: ./delete_model.sh iris_model 1.0.0

set -e

BASEURL="localhost:8003"
MODEL_NAME="${1:-iris_model}"
VERSION="${2:-1.0.0}"

echo "=== Deleting $MODEL_NAME version $VERSION ==="
curl -i -X DELETE "$BASEURL/models/$MODEL_NAME/$VERSION"
echo
echo

echo "=== Should be 404 after delete ==="
curl -i "$BASEURL/models/$MODEL_NAME/$VERSION"
echo
