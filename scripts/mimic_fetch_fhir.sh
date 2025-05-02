#!/bin/bash





# get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# get the project root directory, using git
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

# first need to get the users' physionet username
read -p "PhysioNet username: " PHYSIONET_USERNAME

mkdir -p $PROJECT_ROOT/tools/output/physionet_mimic_fhir
wget -r -N -c -np --user $PHYSIONET_USERNAME --ask-password https://physionet.org/files/mimic-iv-fhir/2.1/ -P $PROJECT_ROOT/tools/output/physionet_mimic_fhir