#!/bin/bash

# Usage: ./build_docker.sh [build args]
# e.g. ./build_docker.sh --no-cache


TAGS=(
  "dpcgansmodel:latest"
  "dpcgansmodel:0.1.0"
)

args="$@"

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
docker build $args ${TAGS[@]/#/-t } -f "$SCRIPT_DIR/Dockerfile" "$SCRIPT_DIR"