#!/bin/bash

## Provides the status of various docker things.
## Nothing to configure.



# get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# get the project root directory, using git
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
# get the docker-compose file
APP_COMPOSE_FILE="$PROJECT_ROOT/app/docker-compose.yml"
TOOLS_COMPOSE_FILE="$PROJECT_ROOT/tools/docker-compose.yml"

echo -e "APP COMPOSE CONTAINERS:"
docker-compose -f "$APP_COMPOSE_FILE" ps -a

echo -e "\n\nTOOLS COMPOSE CONTAINERS:"
docker-compose -f "$TOOLS_COMPOSE_FILE" ps -a

echo -e "\n\nALL CONTAINERS:"
docker ps -a