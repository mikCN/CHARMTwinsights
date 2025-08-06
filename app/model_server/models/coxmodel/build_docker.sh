#!/bin/bash

# Usage: ./build_docker.sh [build args]
# e.g. ./build_docker.sh --no-cache


TAGS=(
  "coxmodel:latest"
)

args="$@"

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
docker build $args ${TAGS[@]/#/-t } -f "$SCRIPT_DIR/Dockerfile" "$SCRIPT_DIR"