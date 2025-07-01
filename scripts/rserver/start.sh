#!/bin/bash

## Starst the rserver. Since this requires HAPI, it also starts the HAPI FHIR server, and the postgres database, if necessary.
## Nothing to configure



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

$DOCKER_COMPOSE_CMD build rserver

$DOCKER_COMPOSE_CMD up -d --force-recreate --remove-orphans $TARGET
# Wait for it to come up, it will return 200 on / when ready
echo "Waiting for rserver to be ready..."
until curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/ | grep -q "200"; do
  echo "rserver is not ready yet. Retrying in 5 seconds..."
  sleep 5
done
echo "rserver is up and ready for requests! You can access it at http://localhost:8001"