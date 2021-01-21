#!/usr/bin/env bash

PYTHON_BINARY=python3
if ! [ -x "$(command -v $PYTHON_BINARY)" ]; then
  PYTHON_BINARY=python
fi

$PYTHON_BINARY --version

# Ensure virtualenv is present. This is not always the case
$PYTHON_BINARY -m pip install virtualenv --user

# Create and activate the virtualenv. This can be done even if it already exists
# and will ensure setuptools, wheel and pip are up to date
$PYTHON_BINARY -m virtualenv venv
source venv/bin/activate

# From there on we use 'pip' and 'python' (refers to versions in the virtualenv)
pip install -r requirements.txt

set -o pipefail -o errexit

# The bot uses non-zero exit codes to signal state.
# The bot will restart until it returns an exit code of zero.
while true; do
    python bootstrap.py && exit
    sleep 1
done
