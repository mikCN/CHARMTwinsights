#!/bin/bash

## Cleans out all docker containers and networks
## Nothing to configure.




# show a warning that this will clean out all docker containers and networks
echo "WARNING: This will remove all docker containers and networks created by docker-compose or otherwise. This includes containers that are not part of the CHARMTwinsight project!!"

# read on the same line
read -r -p "Are you sure you want to continue? (y/n): " answer
if [[ "$answer" != "y" ]]; then
  echo "Aborting..."
  exit 1
fi

# get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# get the project root directory, using git
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

# Stop all running containers
docker stop $(docker ps -aq) 2>/dev/null || echo "No remaining containers to stop"

# Remove all containers
docker rm $(docker ps -aq) 2>/dev/null || echo "No remaining containers to remove"

# Remove all networks created by docker-compose
docker network prune -f