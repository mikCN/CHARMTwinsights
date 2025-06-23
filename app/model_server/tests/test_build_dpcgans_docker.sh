#!/bin/bash

## Builds the example Iris model Docker image
# configurable tags:
TAGS="-t dpcgansmodel:latest -t dpcgansmodel:1.2.0"


# get the project root directory, using git
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

# location of the Dockerfile is "$PROJECT_ROOT/tools/irismodel/Dockerfile"
# we want to build it and apply all the tags
DOCKERBASE="$PROJECT_ROOT/app/model_server/tests/dpcgansmodel"
DOCKERFILE="$DOCKERBASE/Dockerfile"
# build the Docker image
docker build --no-cache $TAGS -f $DOCKERFILE $DOCKERBASE