#!/usr/bin/env bash
set -o pipefail -o errexit

# The bot are using non-zero exit codes to signal state.
# Should be restarted until it returns a exit code of zero.
while true; do
    python3 bootstrap.py && exit
done