#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Check for venv
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found. Please run installation steps first."
    exit 1
fi

python3 main.py