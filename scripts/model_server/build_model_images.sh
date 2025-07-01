#!/bin/bash

## Starts the model server and backing mongo db if necessary.
## Nothing to configure



# get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# get the project root directory, using git
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

echo -e "\nBuilding DPCGAN model Docker image...\n"
$PROJECT_ROOT/tools/model_server_models/build_dpcgans_image.sh

echo -e "\nBuilding Iris model Docker image...\n"
$PROJECT_ROOT/tools/model_server_models/build_iris_image.sh

echo -e "\n"