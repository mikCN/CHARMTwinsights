#!/bin/bash

## Builds the example Iris model Docker image
# configurable tags:
TAGS="-t irismodel:latest -t irismodel:1.0.0"


# get the project root directory, using git
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

# location of the Dockerfile is "$PROJECT_ROOT/tools/irismodel/Dockerfile"
# we want to build it and apply all the tags
DOCKERBASE="$PROJECT_ROOT/tools/model_server_models/irismodel"
DOCKERFILE="$DOCKERBASE/Dockerfile"
# build the Docker image
docker build --no-cache $TAGS -f $DOCKERFILE $DOCKERBASE