#!/usr/bin/env bash

pip install -U -r requirements.txt

set -o pipefail -o errexit

# The bot uses non-zero exit codes to signal state.
# Should be restarted until it returns an exit code of zero.
while true; do
    python3 bootstrap.py && exit
    sleep 1
done