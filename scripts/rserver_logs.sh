#!/bin/bash

## Shows the logs of the HAPI FHIR server
## Number of lines to show is configurable

# just get the logs with tail defined by $HAPI_LOGS_TAIL
RSERVER_LOGS_TAIL=${RSERVER_LOGS_TAIL:-100}








# get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# get the project root directory, using git
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
# get the docker-compose file
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/app/docker-compose.yml"
# get the docker-compose command
DOCKER_COMPOSE_CMD="docker-compose -f $DOCKER_COMPOSE_FILE"
# get the docker-compose target
TARGET="rserver"


# get the logs from the HAPI FHIR server
$DOCKER_COMPOSE_CMD logs --tail $RSERVER_LOGS_TAIL $TARGET