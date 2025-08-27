#!/usr/bin/env bash
set -euo pipefail

# GoGospel installer (Linux)
# - Creates a virtualenv
# - Installs Python deps from requirements.txt
# - Prints how to run the app

PROJECT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
cd "$PROJECT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-venv}"
REQ_FILE="requirements.txt"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Error: python3 not found. Please install Python 3.9+ and try again." >&2
  exit 1
fi

# Create venv if missing
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment at $VENV_DIR ..."
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# Activate venv
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

# Upgrade pip and wheel
pip install -U pip wheel

# Install deps
if [ -f "$REQ_FILE" ]; then
  echo "Installing dependencies from $REQ_FILE ..."
  pip install -r "$REQ_FILE"
else
  echo "Warning: $REQ_FILE not found. Skipping dependency install."
fi

echo
echo "Installation complete. To run the app:" 
echo "1) source $PROJECT_DIR/$VENV_DIR/bin/activate"
echo "2) python main.py"
echo
