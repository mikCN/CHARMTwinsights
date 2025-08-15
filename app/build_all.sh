#!/bin/bash

# Build script for CHARMTwinsights
# This script builds both application images and model images in the correct order

set -e  # Exit on any error

echo "Building CHARMTwinsights..."

# Parse command line arguments
DOCKER_ARGS=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cache|--progress=*|--pull)
            DOCKER_ARGS="$DOCKER_ARGS $1"
            shift
            ;;
        *)
            echo "Unknown option $1"
            echo "Usage: $0 [--no-cache] [--progress=plain] [--pull]"
            exit 1
            ;;
    esac
done

echo "Step 1/2: Building model images..."
cd model_server/models
./build_model_images.sh $DOCKER_ARGS
cd ../..

echo "Step 2/2: Building application images..."
docker compose build $DOCKER_ARGS

echo "Build complete! You can now run:"
echo "   docker compose up --detach"
