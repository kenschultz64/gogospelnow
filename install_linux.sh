#!/usr/bin/env bash
# ============================================================================
# GoGospelNow Real-Time Preaching Translator — One-Click Installer (Linux)
# ============================================================================
# Run this on a fresh Linux machine. It installs EVERYTHING: Docker, Ollama,
# Kokoro TTS, Python, Whisper, and the translator app. No terminal knowledge needed.
#
# USAGE: chmod +x install_linux.sh && ./install_linux.sh
#
# Tested on: Ubuntu 24.04, Fedora 41, Debian 12
# ============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
step()  { echo -e "\n${GREEN}▶${NC} $1"; }
warn()  { echo -e "${YELLOW}⚠  $1${NC}"; }
ok()    { echo -e "${GREEN}✓${NC} $1"; }
fail()  { echo -e "${RED}✗  $1${NC}"; }

MINIFORGE_DIR="$HOME/local/opt/miniforge3"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   GoGospelNow — Real-Time Preaching Translator          ║${NC}"
echo -e "${CYAN}║   Complete Installer for Linux                          ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── Detect distro ─────────────────────────────────────────────────────────
step "Detecting Linux distribution..."

if command -v apt-get >/dev/null 2>&1; then
    PKG_MGR="apt"
    INSTALL_CMD="sudo apt-get install -y"
    DOCKER_PKG="docker.io"
    DISTRO="Debian/Ubuntu"
elif command -v dnf >/dev/null 2>&1; then
    PKG_MGR="dnf"
    INSTALL_CMD="sudo dnf install -y"
    DOCKER_PKG="docker"
    DISTRO="Fedora/RHEL"
elif command -v pacman >/dev/null 2>&1; then
    PKG_MGR="pacman"
    INSTALL_CMD="sudo pacman -S --noconfirm"
    DOCKER_PKG="docker"
    DISTRO="Arch"
elif command -v zypper >/dev/null 2>&1; then
    PKG_MGR="zypper"
    INSTALL_CMD="sudo zypper install -y"
    DOCKER_PKG="docker"
    DISTRO="openSUSE"
else
    fail "Could not detect package manager. Please install Docker manually."
    DISTRO="unknown"
fi

ARCH=$(uname -m)
if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    MINIFORGE_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh"
else
    MINIFORGE_URL="https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
fi

ok "$DISTRO ($ARCH)"

# ── 1. Docker ──────────────────────────────────────────────────────────────
step "1/8: Docker (runs the text-to-speech engine)"

DOCKER_READY=false
if docker ps >/dev/null 2>&1; then
    ok "Docker already installed and running"
    DOCKER_READY=true
elif command -v docker >/dev/null 2>&1; then
    warn "Docker installed but not running"
    sudo systemctl start docker 2>/dev/null || true
    if docker ps >/dev/null 2>&1; then
        ok "Docker started"
        DOCKER_READY=true
    fi
fi

if [ "$DOCKER_READY" = false ] && [ "$DISTRO" != "unknown" ]; then
    echo "Installing Docker Engine..."
    if [ "$PKG_MGR" = "apt" ]; then
        sudo apt-get update -qq
        $INSTALL_CMD docker.io docker-compose-v2 2>&1 | tail -3
    else
        $INSTALL_CMD $DOCKER_PKG 2>&1 | tail -3
    fi
    sudo systemctl enable docker 2>/dev/null || true
    sudo systemctl start docker 2>/dev/null || true
    sudo usermod -aG docker "$USER" 2>/dev/null || true
    
    if docker ps >/dev/null 2>&1; then
        ok "Docker installed and running"
        DOCKER_READY=true
    else
        warn "Docker installed but may need a logout/login to work"
        echo "  After this script finishes, log out and back in, then re-run."
    fi
fi

# ── 2. Kokoro TTS ──────────────────────────────────────────────────────────
step "2/8: Kokoro TTS (text-to-speech voices)"

if curl -s http://localhost:8880/v1/models >/dev/null 2>&1; then
    ok "Kokoro TTS already running"
elif [ "$DOCKER_READY" = true ]; then
    echo "Pulling Kokoro TTS container..."
    docker pull ghcr.io/remsky/kokoro-fastapi-cpu:latest 2>&1 | tail -3
    docker rm -f kokoro-tts 2>/dev/null || true
    docker run -d --name kokoro-tts \
        -p 8880:8880 \
        --restart unless-stopped \
        ghcr.io/remsky/kokoro-fastapi-cpu:latest
    
    for i in $(seq 1 20); do
        if curl -s http://localhost:8880/v1/models >/dev/null 2>&1; then
            ok "Kokoro TTS is ready"; break
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
    ok "Ollama already running"
    OLLAMA_READY=true
elif command -v ollama >/dev/null 2>&1; then
    warn "Ollama installed but not running"
    ollama serve &
    sleep 3
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        ok "Ollama started"; OLLAMA_READY=true
    fi
fi

if [ "$OLLAMA_READY" = false ]; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh 2>&1 | tail -5
    
    # Start ollama serve in background
    ollama serve > /dev/null 2>&1 &
    for i in $(seq 1 15); do
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            ok "Ollama is ready"; OLLAMA_READY=true; break
        fi
        sleep 2
    done
    
    if [ "$OLLAMA_READY" = false ]; then
        fail "Ollama did not start"
    fi
fi

# ── 4. Miniforge (Python) ──────────────────────────────────────────────────
step "4/8: Python environment"

if [ -f "$MINIFORGE_DIR/bin/conda" ]; then
    ok "Python environment already installed"
else
    echo "Installing Miniforge (Python 3.12)..."
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

conda run -n ggn conda install -y -c conda-forge ffmpeg portaudio 2>&1 | tail -3
ok "System libraries ready"

cd "$PROJECT_DIR"
conda run -n ggn pip install -r requirements.txt 2>&1 | tail -5
ok "Python packages installed"

# ── 6. Translation model ──────────────────────────────────────────────────
step "6/8: Translation AI model"

if [ "$OLLAMA_READY" = true ]; then
    EXISTING=$(curl -s http://localhost:11434/api/tags | python3 -c \
        "import json,sys; print(','.join(m['name'] for m in json.load(sys.stdin)['models']))" 2>/dev/null || echo "")
    
    if echo "$EXISTING" | grep -q "translategemma"; then
        ok "Translation model already available"
    else
        echo "Downloading translategemma (~3.3 GB)..."
        ollama pull translategemma
        ok "Model downloaded"
    fi
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

# Create .desktop file
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

ICON_PATH="$PROJECT_DIR/icon.png"
if [ ! -f "$ICON_PATH" ]; then
    ICON_PATH="$PROJECT_DIR/icon.ico"
fi

cat > "$DESKTOP_DIR/gogospelnow.desktop" << DESKTOP
[Desktop Entry]
Name=GoGospelNow Translator
Comment=Real-Time Preaching Translator
Exec=bash -c 'export PATH=$MINIFORGE_DIR/bin:\$PATH && source $MINIFORGE_DIR/etc/profile.d/conda.sh && conda activate ggn && cd $PROJECT_DIR && python3 main.py'
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Audio;Translation;
StartupWMClass=gogospelnow
DESKTOP

# Also copy to Desktop for easy access
cp "$DESKTOP_DIR/gogospelnow.desktop" "$HOME/Desktop/gogospelnow.desktop" 2>/dev/null || true

ok "Desktop launcher created"

# ── Done ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           ✅  Installation Complete!                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Start the app
export PATH="$MINIFORGE_DIR/bin:$PATH"
source "$MINIFORGE_DIR/etc/profile.d/conda.sh"
conda run -n ggn python3 main.py > /tmp/gogospelnow.log 2>&1 &

# Wait up to 90s for first startup (whisper model download)
for i in $(seq 1 30); do
    if curl -s -o /dev/null -w '' http://localhost:7860 2>/dev/null; then
        echo -e "  ${GREEN}Translator is running at:${NC} http://localhost:7860"
        if command -v xdg-open >/dev/null 2>&1; then
            xdg-open "http://localhost:7860?__theme=dark" 2>/dev/null || true
        fi
        break
    fi
    sleep 3
done

if ! curl -s -o /dev/null -w '' http://localhost:7860 2>/dev/null; then
    echo "  First start takes ~60s (downloading voice model)."
    echo "  To start later: find 'GoGospelNow Translator' in your app launcher."
fi

echo ""
echo "  Next time: find 'GoGospelNow Translator' in your app launcher."
echo ""
