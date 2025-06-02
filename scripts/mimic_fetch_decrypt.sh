#!/bin/bash


# get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# get the project root directory, using git
PROJECT_ROOT="$(git rev-parse --show-toplevel)"

FILE_ROOT="$PROJECT_ROOT/tools/output/mimic_data/mimic_iv_100pt_demo"

mkdir -p "$PROJECT_ROOT/tools/output/mimic_data"

# Download the MIMIC-IV demo dataset from Google Drive
curl "https://drive.usercontent.google.com/download?id=1UBfaFQF1kuXTlwZEom7AQG_kmWHOi1Xg&confirm=y" -o "$FILE_ROOT.tar.gz.gpg"

# Decrypt the downloaded file using GPG - it will ask for the passphrase
gpg -o "$FILE_ROOT.tar.gz" --decrypt "$FILE_ROOT.tar.gz.gpg"

tar -xzf "$FILE_ROOT.tar.gz" -C "$PROJECT_ROOT/tools/output/mimic_data"