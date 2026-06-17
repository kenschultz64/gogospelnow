#!/usr/bin/env bash
# ============================================================================
# GoGospelNow Real-Time Preaching Translator — One-Click Installer (macOS)
# ============================================================================
# Run this on a fresh Mac. It installs EVERYTHING: Docker, Ollama, Kokoro TTS,
# Python, Whisper, and the translator app itself. No terminal knowledge needed.
#
# USAGE: Open Terminal, drag this file in, press Enter.
# ============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
step()  { echo -e "\n${GREEN}▶${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠  $1${NC}"; }
ok()    { echo -e "${GREEN}✓${NC} $1"; }
fail()  { echo -e "${RED}✗  $1${NC}"; }

# ── Architecture detection ────────────────────────────────────────────────
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    MINIFORGE_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Darwin-arm64.sh"
    OLLAMA_URL="https://ollama.com/download/Ollama-darwin.zip"
else
    MINIFORGE_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Darwin-x86_64.sh"
    OLLAMA_URL="https://ollama.com/download/Ollama-darwin.zip"
fi

MINIFORGE_DIR="$HOME/local/opt/miniforge3"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   GoGospelNow — Real-Time Preaching Translator          ║${NC}"
echo -e "${CYAN}║   Complete Installer for macOS                          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "This will install: Docker Desktop, Ollama, Kokoro TTS, Python,"
echo "and the GoGospelNow translator. About 8 GB of downloads."
echo ""

# ── 1. Docker Desktop ─────────────────────────────────────────────────────
step "1/8: Docker Desktop (runs the text-to-speech engine)"

DOCKER_READY=false
if docker ps >/dev/null 2>&1; then
    ok "Docker Desktop already installed and running"
    DOCKER_READY=true
elif [ -d "/Applications/Docker.app" ]; then
    echo "  Opening Docker Desktop — please wait..."
    open -a Docker 2>/dev/null || true
    for i in $(seq 1 30); do
        if docker ps >/dev/null 2>&1; then ok "Docker is ready"; DOCKER_READY=true; break; fi
        sleep 2
    done
    if [ "$DOCKER_READY" = false ]; then
        fail "Docker didn't start in time. Please open it manually and re-run this script."
        exit 1
    fi
fi

if [ "$DOCKER_READY" = false ]; then
    echo ""
    echo -e "  ${YELLOW}Docker Desktop is not installed.${NC}"
    echo ""
    echo "  ┌─────────────────────────────────────────────────────────┐"
    echo "  │  STEP 1: Install Docker Desktop                        │"
    echo "  │                                                         │"
    echo "  │  1. Download: docker.com/products/docker-desktop/       │"
    echo "  │  2. Open the .dmg file                                  │"
    echo "  │  3. Drag Docker into Applications                       │"
    echo "  │  4. Open Docker from Applications (needs password)      │"
    echo "  │  5. Wait for the green 'Engine running' indicator       │"
    echo "  │                                                         │"
    echo "  │  STEP 2: Re-run this installer script                   │"
    echo "  │                                                         │"
    echo "  │  The installer will pick up where it left off.          │"
    echo "  └─────────────────────────────────────────────────────────┘"
    echo ""
    
    # Offer to download
    echo -n "  Download Docker Desktop now? [Y/n] "
    read -r DL
    if [ "$DL" != "n" ] && [ "$DL" != "N" ]; then
        DOCKER_DMG="/tmp/Docker.dmg"
        if [ "$ARCH" = "arm64" ]; then
            curl -fsSLo "$DOCKER_DMG" "https://desktop.docker.com/mac/main/arm64/Docker.dmg"
        else
            curl -fsSLo "$DOCKER_DMG" "https://desktop.docker.com/mac/main/amd64/Docker.dmg"
        fi
        open "$DOCKER_DMG" 2>/dev/null || hdiutil attach "$DOCKER_DMG" -nobrowse 2>/dev/null || true
        echo "  Installer downloaded and opened."
    fi
    
    echo ""
    echo "  After Docker is running, re-run: ./install_gogospelnow.sh"
    exit 0
fi

# ── 2. Kokoro TTS container ───────────────────────────────────────────────
step "2/8: Kokoro TTS (text-to-speech voices)"

if curl -s http://localhost:8880/v1/models >/dev/null 2>&1; then
    ok "Kokoro TTS already running on port 8880"
elif [ "$DOCKER_READY" = true ]; then
    echo "Pulling Kokoro TTS container (first time may take a few minutes)..."
    docker pull ghcr.io/remsky/kokoro-fastapi-cpu:latest 2>&1 | tail -3
    
    # Stop existing container if any
    docker rm -f kokoro-tts 2>/dev/null || true
    
    echo "Starting Kokoro TTS..."
    docker run -d --name kokoro-tts \
        -p 8880:8880 \
        --restart unless-stopped \
        ghcr.io/remsky/kokoro-fastapi-cpu:latest
    
    # Wait for it to be ready
    for i in $(seq 1 20); do
        if curl -s http://localhost:8880/v1/models >/dev/null 2>&1; then
            ok "Kokoro TTS is ready"
            break
        fi
        sleep 3
    done
else
    warn "Skipping Kokoro TTS — Docker not available"
fi

# ── 3. Ollama ──────────────────────────────────────────────────────────────
step "3/8: Ollama (AI translation engine)"

OLLAMA_READY=false
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    ok "Ollama already running on port 11434"
    OLLAMA_READY=true
elif [ -d "/Applications/Ollama.app" ]; then
    warn "Ollama is installed but not running"
    echo "  Opening Ollama..."
    open -a Ollama 2>/dev/null || true
    for i in $(seq 1 15); do
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            ok "Ollama is ready"; OLLAMA_READY=true; break
        fi
        sleep 2
    done
fi

if [ "$OLLAMA_READY" = false ]; then
    echo "Downloading and installing Ollama..."
    OLLAMA_ZIP="/tmp/Ollama.zip"
    curl -fsSLo "$OLLAMA_ZIP" "$OLLAMA_URL"
    
    echo "Extracting to /Applications..."
    # Remove old version if present
    if [ -d "/Applications/Ollama.app" ]; then
        rm -rf "/Applications/Ollama.app" 2>/dev/null || \
        { fail "Need permission to update Ollama. Please drag Ollama from the zip to Applications manually."; \
          open /tmp; }
    fi
    unzip -qo "$OLLAMA_ZIP" -d /Applications/ 2>/dev/null || {
        warn "Could not extract to /Applications automatically."
        echo "  Opening the zip file — please drag Ollama to Applications."
        open /tmp/Ollama.zip 2>/dev/null || open /tmp
        echo -n "  After installing Ollama, press Enter to continue... "
        read -r
    }
    rm -f "$OLLAMA_ZIP"
    
    # Launch Ollama
    echo "Starting Ollama..."
    open -a Ollama 2>/dev/null || true
    for i in $(seq 1 20); do
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            ok "Ollama is ready"; OLLAMA_READY=true; break
        fi
        sleep 3
    done
    
    if [ "$OLLAMA_READY" = false ]; then
        fail "Ollama did not start. Please open it from Applications manually."
        echo "  The rest of the install will continue, but translation won't work."
    fi
fi

# ── 4. Miniforge (Python) ──────────────────────────────────────────────────
step "4/8: Python environment"

if [ -f "$MINIFORGE_DIR/bin/conda" ]; then
    ok "Python environment already installed"
else
    echo "Installing Miniforge (Python 3.12, no admin password needed)..."
    mkdir -p "$HOME/local/opt"
    curl -fsSLo /tmp/Miniforge3-installer.sh "$MINIFORGE_URL"
    bash /tmp/Miniforge3-installer.sh -b -p "$MINIFORGE_DIR"
    rm /tmp/Miniforge3-installer.sh
    ok "Python installed"
fi

export PATH="$MINIFORGE_DIR/bin:$PATH"
source "$MINIFORGE_DIR/etc/profile.d/conda.sh"

# ── 5. Conda environment + dependencies ───────────────────────────────────
step "5/8: Installing app dependencies"

if conda env list | grep -q "^ggn "; then
    ok "App environment exists"
else
    conda create -y -n ggn python=3.12 2>&1 | tail -3
fi

conda activate ggn
conda install -y -c conda-forge ffmpeg portaudio 2>&1 | tail -3
ok "System libraries ready"

cd "$PROJECT_DIR"
pip install -r requirements.txt 2>&1 | tail -5
ok "Python packages installed"

# ── 6. Translation model ──────────────────────────────────────────────────
step "6/8: Translation AI model"

if [ "$OLLAMA_READY" = true ]; then
    EXISTING=$(curl -s http://localhost:11434/api/tags | python3 -c \
        "import json,sys; print(','.join(m['name'] for m in json.load(sys.stdin)['models']))" 2>/dev/null || echo "")
    
    if echo "$EXISTING" | grep -q "translategemma"; then
        ok "Translation model already available: $EXISTING"
    else
        echo "Downloading translation model (translategemma, ~3.3 GB)..."
        echo "This may take 5-15 minutes depending on your internet speed."
        ollama pull translategemma
        ok "Model downloaded"
    fi
else
    warn "Skipping model download — Ollama not running"
fi

# ── 7. Settings ────────────────────────────────────────────────────────────
step "7/8: Configuring settings"

python3 -c "
import json
try:
    s = json.load(open('settings.json'))
except:
    s = {}
s['translation_server'] = 'http://localhost:11434'
s['tts_server_url'] = 'http://localhost:8880/v1'
s['translation_provider'] = 'Ollama'
json.dump(s, open('settings.json', 'w'), indent=2)
"
ok "Settings configured"

# ── 8. Desktop launcher ───────────────────────────────────────────────────
step "8/8: Desktop launcher"

APP_DIR="$HOME/Desktop/GoGospelNow Translator.app"
mkdir -p "$APP_DIR/Contents/MacOS" "$APP_DIR/Contents/Resources"

# Icon
if [ -f "$PROJECT_DIR/icon.png" ]; then
    sips -s format icns "$PROJECT_DIR/icon.png" --out "$APP_DIR/Contents/Resources/AppIcon.icns" 2>/dev/null || true
fi

cat > "$APP_DIR/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>GoGospelNow Translator</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.gogospelnow.translator</string>
    <key>CFBundleName</key>
    <string>GoGospelNow Translator</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>2.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

cat > "$APP_DIR/Contents/MacOS/GoGospelNow Translator" << LAUNCHER
#!/bin/bash
export PATH="$MINIFORGE_DIR/bin:\$PATH"
source "$MINIFORGE_DIR/etc/profile.d/conda.sh"
conda activate ggn
cd "$PROJECT_DIR"
python3 main.py &
SERVER_PID=\$!
sleep 4
URL="http://localhost:7860?__theme=dark"
if [ -d "/Applications/Google Chrome.app" ]; then
    open -a "Google Chrome" "\$URL"
elif [ -d "/Applications/Safari.app" ]; then
    open -a "Safari" "\$URL"
else
    open "\$URL"
fi
wait \$SERVER_PID
LAUNCHER
chmod +x "$APP_DIR/Contents/MacOS/GoGospelNow Translator"
ok "Desktop launcher created"

# ── Done ───────────────────────────────────────────────────────────────────

# Quick health check
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           ✅  Installation Complete!                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Start the app if it's not already running
if ! curl -s -o /dev/null -w '' http://localhost:7860 2>/dev/null; then
    echo "Starting GoGospelNow Translator..."
    export PATH="$MINIFORGE_DIR/bin:$PATH"
    source "$MINIFORGE_DIR/etc/profile.d/conda.sh"
    conda activate ggn
    cd "$PROJECT_DIR"
    python3 main.py > /tmp/gogospelnow.log 2>&1 &
    sleep 5
fi

if curl -s -o /dev/null -w '' http://localhost:7860 2>/dev/null; then
    echo -e "  ${GREEN}Translator is running at:${NC} http://localhost:7860"
    open "http://localhost:7860?__theme=dark" 2>/dev/null || true
else
    echo "  To start: double-click 'GoGospelNow Translator' on your Desktop"
fi

echo ""
echo "  ┌─────────────────────────────────────────────┐"
echo "  │  RECOMMENDED SETTINGS (M4 Mac / 16GB):      │"
echo "  │    Whisper Model:   small                    │"
echo "  │    Compute Device:  Metal GPU                │"
echo "  │    Compute Type:    float16                  │"
echo "  │    CPU Threads:     4                        │"
echo "  │    Translation:     translategemma             │"
echo "  └─────────────────────────────────────────────┘"
echo ""
echo "  Settings page: http://localhost:7860 (click the Settings tab)"
echo "  For help:       https://github.com/kenschultz64/gogospelnow"
echo ""
