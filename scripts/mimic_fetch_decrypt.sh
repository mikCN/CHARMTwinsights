#!/bin/bash


# get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# get the project root directory, using git
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

mkdir -p "$PROJECT_ROOT/scripts/mimic_data"

cd "$PROJECT_ROOT/scripts/mimic_data"

# Download the MIMIC-IV demo dataset from Google Drive
curl "https://drive.usercontent.google.com/download?id=1UBfaFQF1kuXTlwZEom7AQG_kmWHOi1Xg&confirm=y" -o "$FILE_ROOT.tar.gz.gpg"

# Decrypt the downloaded file using GPG - it will ask for the passphrase
gpg -o "$FILE_ROOT.tar.gz" --decrypt "$FILE_ROOT.tar.gz.gpg"

tar -xzf "$FILE_ROOT.tar.gz"