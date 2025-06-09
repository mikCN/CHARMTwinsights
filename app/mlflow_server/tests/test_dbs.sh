#!/bin/bash
set -e

echo "=== Test Mongo ==="
curl localhost:8003/test/mongo
echo -e "\n"

echo "=== Test MinIO Upload ==="
curl -X POST -F "file=@testfile.txt" localhost:8003/test/minio/upload
echo -e "\n"

echo "=== Test MinIO Download ==="
curl localhost:8003/test/minio/download/testfile.txt
echo -e "\n"
