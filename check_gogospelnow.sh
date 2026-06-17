#!/usr/bin/env bash
# ============================================================================
# GoGospelNow Health Check — verifies every component + gives recommendations
# ============================================================================
# Run anytime:  ./check_gogospelnow.sh
# Works on:     macOS, Linux, Windows (Git Bash / WSL)
# ============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
PASS=0; WARN=0; FAIL=0

check() {
    local label="$1"; shift
    echo -n "  $label ... "
    if "$@" >/dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"; PASS=$((PASS+1))
    else
        echo -e "${RED}FAIL${NC}"; FAIL=$((FAIL+1))
    fi
}

warn_check() {
    local label="$1"; shift
    echo -n "  $label ... "
    if "$@" >/dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"; PASS=$((PASS+1))
    else
        echo -e "${YELLOW}WARN${NC}"; WARN=$((WARN+1))
    fi
}

OS="$(uname -s)"
ARCH="$(uname -m)"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   GoGospelNow — System Health Check                     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  System: ${OS} / ${ARCH}"
echo ""

# ── Hardware ───────────────────────────────────────────────────────────────
echo -e "${CYAN}── Hardware ──${NC}"

# Memory
if [ "$OS" = "Darwin" ]; then
    MEM_GB=$(( $(sysctl -n hw.memsize 2>/dev/null) / 1073741824 ))
    CPU_CORES=$(sysctl -n hw.ncpu 2>/dev/null)
    IS_APPLE_SILICON=$(sysctl -n machdep.cpu.brand_string 2>/dev/null | grep -c "Apple" || true)
else
    MEM_GB=$(( $(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}') / 1048576 ))
    CPU_CORES=$(nproc 2>/dev/null)
    IS_APPLE_SILICON=0
fi
echo "  Memory: ${MEM_GB} GB"
echo "  CPU cores: ${CPU_CORES}"

if [ "$MEM_GB" -ge 32 ]; then
    echo -e "  ${GREEN}✓ Plenty of RAM for high-quality models${NC}"
elif [ "$MEM_GB" -ge 16 ]; then
    echo -e "  ${GREEN}✓ Good for small/medium Whisper + translategemma${NC}"
else
    echo -e "  ${YELLOW}⚠  Under 16GB — use Whisper 'tiny' or 'base'${NC}"
fi

# ── Docker ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Docker ──${NC}"

if command -v docker >/dev/null 2>&1; then
    if docker ps >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓ Docker Engine is running${NC}"
        PASS=$((PASS+1))
    else
        echo -e "  ${YELLOW}⚠  Docker installed but not running. Start Docker Desktop.${NC}"
        echo "     Also enable: Settings → General → Start Docker Desktop when you log in"
        WARN=$((WARN+1))
    fi
elif curl -s http://localhost:8880/v1/models >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓ Docker Engine is running (Kokoro TTS detected)${NC}"
    PASS=$((PASS+1))
else
    echo -e "  ${RED}✗  Docker not found. Install from docker.com/products/docker-desktop/${NC}"
    FAIL=$((FAIL+1))
fi

# ── Kokoro TTS ─────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Kokoro TTS (text-to-speech) ──${NC}"

KOKORO_OK=false
if curl -s http://localhost:8880/v1/models >/dev/null 2>&1; then
    VOICES=$(curl -s http://localhost:8880/v1/models | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['data']))" 2>/dev/null || echo "?")
    echo -e "  ${GREEN}✓ Kokoro TTS running (${VOICES} voice models)${NC}"
    PASS=$((PASS+1))
    KOKORO_OK=true
else
    echo -e "  ${YELLOW}⚠  Kokoro TTS not on port 8880. Run:${NC}"
    echo "      docker pull ghcr.io/remsky/kokoro-fastapi-cpu:latest"
    echo "      docker run -d --name kokoro-tts -p 8880:8880 --restart unless-stopped ghcr.io/remsky/kokoro-fastapi-cpu:latest"
    WARN=$((WARN+1))
fi

# ── Ollama ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Ollama (translation engine) ──${NC}"

OLLAMA_OK=false
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓ Ollama running${NC}"
    PASS=$((PASS+1))
    OLLAMA_OK=true
    
    MODELS=$(curl -s http://localhost:11434/api/tags | python3 -c "
import json,sys
models = json.load(sys.stdin)['models']
for m in models:
    size_gb = m['size'] / 1e9
    name = m['name']
    params = m.get('details',{}).get('parameter_size','?')
    print(f'    - {name} ({params}, {size_gb:.1f} GB)')
" 2>/dev/null)
    echo "$MODELS"
    
    # Check for translation model
    if echo "$MODELS" | grep -q "translategemma"; then
        echo -e "  ${GREEN}✓ translategemma model found (recommended)${NC}"
    else
        echo -e "  ${YELLOW}⚠  translategemma not found. Pull it: ollama pull translategemma${NC}"
        WARN=$((WARN+1))
    fi
else
    echo -e "  ${RED}✗  Ollama not running on port 11434${NC}"
    echo "      macOS:   Open Ollama from Applications"
    echo "      Linux:   ollama serve"
    echo "      Windows: Start Ollama from Start Menu"
    FAIL=$((FAIL+1))
fi

# ── Python & dependencies ─────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Python Environment ──${NC}"

# Find Python
PYTHON=""
for py in "$HOME/local/opt/miniforge3/envs/ggn/bin/python3" python3 python; do
    if "$py" --version >/dev/null 2>&1; then
        PYTHON="$py"
        PYVER=$("$py" --version 2>&1)
        break
    fi
done

if [ -n "$PYTHON" ]; then
    echo -e "  ${GREEN}✓ Python found: ${PYVER}${NC}"
    PASS=$((PASS+1))
    
    # Check key packages
    for pkg in torch faster_whisper gradio sounddevice pyaudio; do
        if "$PYTHON" -c "import $pkg" 2>/dev/null; then
            :
        else
            echo -e "  ${YELLOW}⚠  Package '$pkg' missing. Run: pip install -r requirements.txt${NC}"
            WARN=$((WARN+1))
        fi
    done
    
    # PyTorch device
    DEVICE=$("$PYTHON" -c "
import torch
if torch.cuda.is_available(): print('CUDA GPU')
elif torch.backends.mps.is_available(): print('Metal GPU (Apple)')
else: print('CPU only')
" 2>/dev/null || echo "unknown")
    echo "  Compute device: $DEVICE"
else
    echo -e "  ${RED}✗  Python 3 not found. Run the installer script.${NC}"
    FAIL=$((FAIL+1))
fi

# ── FFmpeg ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── FFmpeg (audio processing) ──${NC}"

FFMPEG_FOUND=false
if command -v ffmpeg >/dev/null 2>&1; then
    FFMPEG_FOUND=true
elif [ -x "$HOME/local/opt/miniforge3/bin/ffmpeg" ]; then
    FFMPEG_FOUND=true
fi
if [ "$FFMPEG_FOUND" = true ]; then
    echo -e "  ${GREEN}✓ FFmpeg found${NC}"
    PASS=$((PASS+1))
else
    echo -e "  ${YELLOW}⚠  FFmpeg not found. conda install -c conda-forge ffmpeg${NC}"
    WARN=$((WARN+1))
fi

# ── PortAudio ──────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── PortAudio (PyAudio backend) ──${NC}"

if [ -n "$PYTHON" ]; then
    PYAU_VER=$("$PYTHON" -c "import pyaudio; print(pyaudio.__version__)" 2>/dev/null || echo "")
    if [ -n "$PYAU_VER" ]; then
        echo -e "  ${GREEN}✓ PyAudio ${PYAU_VER}${NC}"
        PASS=$((PASS+1))
    else
        echo -e "  ${YELLOW}⚠  PyAudio not installed. Run: pip install PyAudio${NC}"
        WARN=$((WARN+1))
    fi
else
    echo -e "  ${YELLOW}⚠  Python not available — skipping PyAudio check${NC}"
    WARN=$((WARN+1))
fi

# ── Audio ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Audio Devices ──${NC}"

if [ -n "$PYTHON" ]; then
    DEVICES=$("$PYTHON" -c "
import sounddevice as sd
devs = sd.query_devices()
for i, d in enumerate(devs):
    io = 'IN' if d['max_input_channels'] > 0 else ''
    io += 'OUT' if d['max_output_channels'] > 0 else ''
    print(f'  [{i}] {d[\"name\"]} ({io})')
" 2>/dev/null)
    if [ -n "$DEVICES" ]; then
        echo "$DEVICES"
        IN_COUNT=$(echo "$DEVICES" | grep -c "IN" || true)
        if [ "$IN_COUNT" -gt 0 ]; then
            echo -e "  ${GREEN}✓ $IN_COUNT input device(s) found${NC}"
            PASS=$((PASS+1))
        else
            echo -e "  ${YELLOW}⚠  No microphone found. Plug in a USB mic or use built-in.${NC}"
            WARN=$((WARN+1))
        fi
    else
        echo -e "  ${YELLOW}⚠  Could not query audio devices${NC}"
        WARN=$((WARN+1))
    fi
fi

# ── App ports ──────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}── Application ──${NC}"

if curl -s -o /dev/null -w '' http://localhost:7860 2>/dev/null; then
    echo -e "  ${GREEN}✓ Translator running on http://localhost:7860${NC}"
    PASS=$((PASS+1))
else
    echo -e "  ${YELLOW}⚠  Translator not currently running. Start it from your launcher.${NC}"
    WARN=$((WARN+1))
fi

# ── Recommendations ───────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Recommendations                                       ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$MEM_GB" -ge 32 ]; then
    echo "  Whisper model:     medium    (best accuracy)"
    echo "  Compute device:    GPU (CUDA or Metal)"
    echo "  CPU threads:       4"
elif [ "$MEM_GB" -ge 16 ]; then
    echo "  Whisper model:     small     (good balance)"
    echo "  Compute device:    Metal GPU (Mac) / CPU (Linux/Win)"
    echo "  CPU threads:       4"
else
    echo "  Whisper model:     base      (fastest for low RAM)"
    echo "  Compute device:    CPU only"
    echo "  CPU threads:       2"
fi

if [ "$OLLAMA_OK" = true ] && [ "$MEM_GB" -ge 16 ]; then
    echo "  Translation model: translategemma     (4.3B, ~3.3 GB, fast)"
elif [ "$OLLAMA_OK" = true ] && [ "$MEM_GB" -ge 32 ]; then
    echo "  Translation model: qwen3.5:9b or gemma4:12b   (higher quality)"
fi

echo "  Settings page:     http://localhost:7860 → Settings tab"

if [ "$OS" = "Darwin" ] || [ "$OS" = "MINGW" ] || [ "$OS" = "MSYS" ]; then
    echo "  Docker auto-start: Docker Desktop → Settings → General → Start on login"
fi
echo ""

# Missing critical items
if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED}  ⚠  $FAIL critical issue(s) found. Fix these before using the translator.${NC}"
    echo ""
    echo "  Run the installer to fix automatically:"
    if [ "$OS" = "Darwin" ]; then
        echo "    ./install_gogospelnow.sh"
    elif [ "$OS" = "Linux" ]; then
        echo "    ./install_linux.sh"
    else
        echo "    install_windows.ps1"
    fi
fi

if [ "$WARN" -gt 0 ]; then
    echo -e "${YELLOW}  ⚡ $WARN warning(s). The translator will work but may be limited.${NC}"
fi

if [ "$FAIL" -eq 0 ] && [ "$WARN" -eq 0 ]; then
    echo -e "${GREEN}  ✅ All checks passed! Your system is ready for real-time translation.${NC}"
fi

echo ""
echo "  ───────────────────────────────────────────────"
echo -e "  Results: ${GREEN}${PASS} passed${NC}, ${YELLOW}${WARN} warnings${NC}, ${RED}${FAIL} failed${NC}"
echo ""
