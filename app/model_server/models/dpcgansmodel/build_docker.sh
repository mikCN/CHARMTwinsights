#!/bin/bash

TAGS=(
  "dpcgansmodel:latest"
  "dpcgansmodel:0.1.0"
)


SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
docker build --no-cache ${TAGS[@]/#/-t } -f "$SCRIPT_DIR/Dockerfile" "$SCRIPT_DIR"