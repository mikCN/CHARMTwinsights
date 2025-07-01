#!/bin/bash

## This script cleans up the postgres data directory for the HAPI FHIR server
## Effectively removing any previously ingested data
## Nothing to configure



# get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# get the project root directory, using git
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

# we just want to remove everything in app/hapi/postgres_data
# this is the volume that is mounted to the postgres container

# we shouldn't do this if the postgres container is running
if [ "$(docker ps -q -f name=hapi_db)" ]; then
  echo "The HAPI FHIR server is running. Please remove it first with hapi_stop.sh"
  exit 1
fi

# if there's no files in app/hapi/postgres_data, we don't need to do anything
if [ -z "$(ls -A "$PROJECT_ROOT/app/hapi/postgres_data")" ]; then
  echo "No files in $PROJECT_ROOT/app/hapi/postgres_data"
  exit 0
fi

# it's a complete mystery to me, but 
# running rm -rf $PROJECT_ROOT/app/hapi/postgres_data/* doesn't work in this script, but does on the command line
# so we just blow away the whole directory and recreate it
rm -rf "$PROJECT_ROOT/app/hapi/postgres_data"
mkdir -p "$PROJECT_ROOT/app/hapi/postgres_data"

echo -e "\n\nRemoved all files in $PROJECT_ROOT/app/hapi/postgres_data"