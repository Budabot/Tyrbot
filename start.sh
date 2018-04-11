#!/usr/bin/env bash
set -o pipefail -o errexit

# The bot are using non-zero exit codes to signal state
# Exit on a non-zero exit code.
# This should be changed.
while true; do
    python3 bootstrap.py && exit
done