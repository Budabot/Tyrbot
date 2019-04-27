#!/usr/bin/env bash

export DOCKER_HOST=$(route -n | awk '/UG[ \t]/{print $2}')
echo "$(route -n | awk '/UG[ \t]/{print $2}')      docker_host" >> /etc/hosts

set -o pipefail -o errexit

# The bot uses non-zero exit codes to signal state.
# Should be restarted until it returns an exit code of zero.
while true; do
    git pull
    pip3 install -U -r requirements.txt
    python3 bootstrap.py && exit
    sleep 1
done