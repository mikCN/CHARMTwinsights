#!/bin/bash

## Generates synthetic patient data using Synthea
## Removes any previously generated data first (but not anything uploaded to HAPI)

## These params may also be configured when running, ala
## NUM_YEARS=1 NUM_PATIENTS=10 scripts/synthea_data_gen.sh

export NUM_YEARS=${NUM_YEARS:-1}
# apparently the NUM_PATIENTS param sets the number of ALIVE patients in synthea, deceased patients may also be generated...
export NUM_PATIENTS=${NUM_PATIENTS:-5}
# -a sets patient age range
# -s sets random seed
export EXTRA_ARGS="\
        -a 1-90 -s 42 \
        --physiology.generators.enabled true \
        --physiology.state.enabled true \
"







# get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# get the project root directory, using git
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
# get the docker-compose file
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/tools/docker-compose.yml"
# get the docker-compose command
DOCKER_COMPOSE_CMD="docker-compose -f $DOCKER_COMPOSE_FILE"
# get the docker-compose target
TARGET="synthea"

# build the services first
$DOCKER_COMPOSE_CMD build

# then bring up the services
$DOCKER_COMPOSE_CMD run --rm --remove-orphans $TARGET

echo -e "\n\nData generated in $PROJECT_ROOT/tools/output/synthea"