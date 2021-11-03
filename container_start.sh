#!/usr/bin/env ash

set -o pipefail -o errexit

# Let container runtime handle restart
python bootstrap.py && exit
