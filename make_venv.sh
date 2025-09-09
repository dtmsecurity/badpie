#!/bin/bash

rm -rf ./test-venv-project

# Create and move into project directory
mkdir -p test-venv-project && cd test-venv-project || exit 1

# Create virtual environment if it doesn't exist
python3 -m venv test-env

# Activate the virtual environment
source test-env/bin/activate

# Confirm activation
echo "Virtual environment activated: $(which python)"
exec bash

