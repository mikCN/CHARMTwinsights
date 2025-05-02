#!/bin/bash

## Starst the atlastdb. Nothing to configure



# get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# get the project root directory, using git
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
# get the docker-compose file
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/app/docker-compose.yml"
# get the docker-compose command
DOCKER_COMPOSE_CMD="docker-compose -f $DOCKER_COMPOSE_FILE"
# get the docker-compose target
TARGET="broadsea-atlasdb"

if [[ $(uname -m) == *"arm64"* ]]; then
  export DOCKER_ARCH="linux/arm64"
else
  export DOCKER_ARCH="linux/amd64"
fi

$DOCKER_COMPOSE_CMD up -d --force-recreate --remove-orphans $TARGET
