#!/usr/bin/env bash
# ============================================================================
# GoGospelNow — One-Command Installer (macOS & Linux)
# ============================================================================
# Run this single command from any terminal:
#
#   curl -fsSL https://raw.githubusercontent.com/kenschultz64/gogospelnow/main/install.sh | bash
#
# It auto-detects your OS, clones the repo, and runs the full installer.
# ============================================================================
set -euo pipefail

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║   GoGospelNow — One-Command Installer                   ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

OS="$(uname -s)"

if [ "$OS" = "Darwin" ]; then
    echo "Detected: macOS"
elif [ "$OS" = "Linux" ]; then
    echo "Detected: Linux"
else
    echo "Unsupported OS: $OS"
    echo "For Windows, download install_windows.ps1 from:"
    echo "  https://github.com/kenschultz64/gogospelnow"
    exit 1
fi

REPO_URL="https://github.com/kenschultz64/gogospelnow.git"
REPO_DIR="$HOME/gogospelnow"

# Clone or update the repo
if [ -d "$REPO_DIR/.git" ]; then
    echo "Repo already exists, updating..."
    cd "$REPO_DIR"
    git pull --ff-only 2>/dev/null || true
else
    echo "Downloading GoGospelNow..."
    # Try git clone first, fall back to ZIP download
    if command -v git >/dev/null 2>&1; then
        git clone "$REPO_URL" "$REPO_DIR"
    else
        echo "git not found. Downloading ZIP instead..."
        if command -v curl >/dev/null 2>&1; then
            curl -fsSLo /tmp/gogospelnow.zip "https://github.com/kenschultz64/gogospelnow/archive/refs/heads/main.zip"
        elif command -v wget >/dev/null 2>&1; then
            wget -q -O /tmp/gogospelnow.zip "https://github.com/kenschultz64/gogospelnow/archive/refs/heads/main.zip"
        fi
        unzip -qo /tmp/gogospelnow.zip -d "$HOME"
        mv "$HOME/gogospelnow-main" "$REPO_DIR" 2>/dev/null || true
        rm -f /tmp/gogospelnow.zip
    fi
fi

cd "$REPO_DIR"

# Run the OS-specific installer
if [ "$OS" = "Darwin" ]; then
    echo ""
    echo "Starting macOS installer..."
    bash install_gogospelnow.sh
elif [ "$OS" = "Linux" ]; then
    echo ""
    echo "Starting Linux installer..."
    bash install_linux.sh
fi
