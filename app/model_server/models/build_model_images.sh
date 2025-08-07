#!/bin/bash

# Usage: ./build_model_images.sh [build args]
# e.g. ./build_model_images.sh --no-cache

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

args="$@"

# for each subdirectory, if it contains a build_docker.sh file, run it
for dir in "$SCRIPT_DIR"/*/; do
  if [ -f "$dir/build_docker.sh" ]; then
    echo "Building Docker image for $(basename "$dir")"
    (cd "$dir" && ./build_docker.sh "$args")
  else
    echo "No build_docker.sh found in $(basename "$dir"), skipping."
  fi
done