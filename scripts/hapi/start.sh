#!/bin/bash

## Starst the HAPI FHIR server, and the postgres database if necessary
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
TARGET="hapi"

$DOCKER_COMPOSE_CMD up -d --force-recreate --remove-orphans $TARGET

# Wait for the HAPI FHIR server to be ready
echo "Waiting for HAPI FHIR server to be ready..."
until curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/fhir/metadata | grep -q "200"; do
  echo "HAPI FHIR server is not ready yet. Retrying in 5 seconds..."
  sleep 5
done

echo "HAPI FHIR server is up and ready for requests! You can access it at http://localhost:8080"