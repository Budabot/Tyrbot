#!/usr/bin/env bash

# Ensure virtualenv is present. This is not always the case
python3 -m pip install virtualenv --user

# Create and activate the virtualenv. This can be done even if it already exists
# and will ensure setuptools, wheel and pip are up to date
python3 -m virtualenv venv
source venv/bin/activate

# From there on we use 'pip' and 'python' (refers to versions in the virtualenv)
pip install -U -r requirements.txt

set -o pipefail -o errexit

# The bot uses non-zero exit codes to signal state.
# The bot will restart until it returns an exit code of zero.
while true; do
    python bootstrap.py && exit
    sleep 1
done
