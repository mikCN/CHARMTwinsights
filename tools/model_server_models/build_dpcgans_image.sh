#!/bin/bash

## Builds the example Iris model Docker image
# configurable tags:
TAGS="-t dpcgansmodel:latest -t dpcgansmodel:0.1.0"


# get the project root directory, using git
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

DOCKERBASE="$PROJECT_ROOT/tools/model_server_models/dpcgansmodel"
DOCKERFILE="$DOCKERBASE/Dockerfile"

docker build --no-cache $TAGS -f $DOCKERFILE $DOCKERBASE