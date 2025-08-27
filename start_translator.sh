#!/usr/bin/env bash
set -euo pipefail

# Real-Time Preaching Translator launcher
# Usage: ./start_translator.sh [--host 0.0.0.0] [--port 7860]
# Notes:
# - Expects external services running (Ollama on 11434, Kokoro FastAPI on 8880)
# - Uses local virtualenv if available; otherwise falls back to system python

HOST=""
PORT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      HOST="$2"; shift 2;;
    --port)
      PORT="$2"; shift 2;;
    *)
      echo "Unknown option: $1"; exit 1;;
  esac
done

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Virtual environment setup
# Preferred order: $VENV_NAME (if set) -> venv -> venv_py313 -> translator_env
VENV_NAME="${VENV_NAME:-venv}"
if [[ -f "$PROJECT_DIR/$VENV_NAME/bin/activate" ]]; then
  source "$PROJECT_DIR/$VENV_NAME/bin/activate"
elif [[ -f "$PROJECT_DIR/venv/bin/activate" ]]; then
  source "$PROJECT_DIR/venv/bin/activate"
elif [[ -f "$PROJECT_DIR/venv_py313/bin/activate" ]]; then
  source "$PROJECT_DIR/venv_py313/bin/activate"
elif [[ -f "$PROJECT_DIR/translator_env/bin/activate" ]]; then
  source "$PROJECT_DIR/translator_env/bin/activate"
else
  echo "[INFO] No local venv found. Creating '$VENV_NAME' and installing requirements..."
  PYTHON_BOOT="python3"
  command -v python3 >/dev/null 2>&1 || PYTHON_BOOT="python"
  "$PYTHON_BOOT" -m venv "$PROJECT_DIR/$VENV_NAME"
  # shellcheck disable=SC1090
  source "$PROJECT_DIR/$VENV_NAME/bin/activate"
  python -m pip install --upgrade pip
  if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
    pip install -r "$PROJECT_DIR/requirements.txt"
  else
    echo "[WARNING] requirements.txt not found; continuing with empty venv."
  fi
fi

# Confirm external system deps (offer guided install on macOS/Linux)
have_ffmpeg=true
command -v ffmpeg >/dev/null 2>&1 || have_ffmpeg=false

if [[ "$have_ffmpeg" = false ]]; then
  echo "[WARNING] ffmpeg not found. Some audio features will not work."
  # Attempt best-effort guided install for macOS/Linux
  OS_NAME="$(uname -s)"
  if [[ "$OS_NAME" == "Darwin" || "$OS_NAME" == "Linux" ]]; then
    echo "You can install required system packages automatically (admin privileges may be required)."
    echo "Packages: ffmpeg portaudio libsndfile"
    read -r -p "Install system packages now? [y/N] " RESP
    if [[ "${RESP:-N}" =~ ^[Yy]$ ]]; then
      if [[ "$OS_NAME" == "Darwin" ]]; then
        if command -v brew >/dev/null 2>&1; then
          echo "[INFO] Installing with Homebrew..."
          brew install ffmpeg portaudio libsndfile || true
        else
          echo "[ERROR] Homebrew not found. Install Homebrew from https://brew.sh and re-run."
        fi
      else
        # Linux: detect package manager
        if command -v apt >/dev/null 2>&1 || command -v apt-get >/dev/null 2>&1; then
          echo "[INFO] Installing with apt... (you may be prompted for sudo password)"
          sudo apt update || true
          sudo apt install -y ffmpeg portaudio19-dev libsndfile1 || true
        elif command -v dnf >/dev/null 2>&1; then
          echo "[INFO] Installing with dnf..."
          sudo dnf install -y ffmpeg portaudio-devel libsndfile || true
        elif command -v pacman >/dev/null 2>&1; then
          echo "[INFO] Installing with pacman..."
          sudo pacman -Syu --noconfirm ffmpeg portaudio libsndfile || true
        else
          echo "[ERROR] Unsupported package manager. Please install ffmpeg, portaudio, and libsndfile manually."
        fi
      fi
    else
      echo "[INFO] Skipping system package install. See DEPLOYMENT_GUIDE.md for instructions."
    fi
  else
    echo "[INFO] Automatic install not available on this OS. See DEPLOYMENT_GUIDE.md."
  fi
fi

# Inform about lockfile reproducibility
if [[ -f requirements.lock ]]; then
  echo "[INFO] Using pinned dependencies from requirements.lock (ensure you've installed them)."
fi

PYTHON_BIN="python"
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

# Allow passing host/port to gradio if app supports it via env vars
if [[ -n "$HOST" ]]; then export GRADIO_SERVER_NAME="$HOST"; fi
if [[ -n "$PORT" ]]; then export GRADIO_SERVER_PORT="$PORT"; fi

# Launch app
echo "Starting GoGospelNow Translator..."
"$PYTHON_BIN" main.py &

# Wait for the server to initialize
echo "Waiting for the server to initialize..."
sleep 5

# Open the application in the default web browser
echo "Launching application in the default browser..."
URL="http://localhost:7860"
if [[ "$(uname)" == "Darwin" ]]; then
  open "$URL"
elif [[ "$(uname)" == "Linux" ]]; then
  xdg-open "$URL"
else
  echo "Could not detect OS to open browser automatically."
  echo "Please open your web browser and navigate to $URL"
fi