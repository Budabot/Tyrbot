#!/usr/bin/env bash

set -o pipefail -o errexit

. .venv/bin/activate
# Let container runtime handle restart
python bootstrap.py && exit
