#!/bin/bash

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

# for each subdirectory, if it contains a register_model_image.sh file, run it
for dir in "$SCRIPT_DIR"/*/; do
  if [ -f "$dir/register_model_image.sh" ]; then
    echo -e "\n\nRegistering model image for $(basename "$dir")"
    (cd "$dir" && ./register_model_image.sh)
  else
    echo "No register_model_image.sh found in $(basename "$dir"), skipping."
  fi
done