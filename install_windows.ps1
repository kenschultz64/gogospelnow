# ============================================================================
# GoGospelNow Real-Time Preaching Translator — One-Click Installer (Windows)
# ============================================================================
# Run this on a fresh Windows 10/11 machine. It installs EVERYTHING: Docker,
# Ollama, Kokoro TTS, Python, Whisper, and the translator app.
#
# USAGE: Right-click this file → "Run with PowerShell"
#   OR: Open PowerShell as Administrator, cd to this file's folder, run:
#       Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#       .\install_windows.ps1
# ============================================================================

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "GoGospelNow Installer"

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   GoGospelNow — Real-Time Preaching Translator          ║" -ForegroundColor Cyan
Write-Host "║   Complete Installer for Windows                        ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

function step($msg)  { Write-Host "`n▶ $msg" -ForegroundColor Green }
function ok($msg)    { Write-Host "✓ $msg" -ForegroundColor Green }
function warn($msg)  { Write-Host "⚠  $msg" -ForegroundColor Yellow }
function fail($msg)  { Write-Host "✗  $msg" -ForegroundColor Red }

$MINIFORGE_DIR = "$env:USERPROFILE\local\opt\miniforge3"
$PROJECT_DIR   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ARCH = if ([Environment]::Is64BitOperatingSystem) { "x86_64" } else { "x86" }

# ── 1. Python ──────────────────────────────────────────────────────────────
step "1/8: Python 3.12"

$pythonOk = $false
try {
    $pyVer = & python --version 2>$null
    if ($pyVer -match "3\.(1[2-9]|[2-9])") {
        ok "Python $pyVer already installed"
        $pythonOk = $true
    }
} catch {}

if (-not $pythonOk) {
    # Try winget first (Windows 11 built-in)
    try {
        Write-Host "Installing Python 3.12 via winget..."
        winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null
    } catch {
        warn "winget not available, downloading Python manually..."
        $pyUrl = "https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe"
        $pyInstaller = "$env:TEMP\python-installer.exe"
        Invoke-WebRequest -Uri $pyUrl -OutFile $pyInstaller
        Start-Process -FilePath $pyInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1" -Wait
        Remove-Item $pyInstaller
    }
    
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    try {
        $pyVer = & python --version 2>$null
        if ($pyVer -match "3\.1[2-9]") {
            ok "Python $pyVer installed"
            $pythonOk = $true
        }
    } catch {
        fail "Python installation failed. Please install manually from https://www.python.org/downloads/"
        Write-Host "Make sure to check 'Add Python to PATH' during installation."
        Write-Host "Then re-run this script."
        Read-Host "Press Enter after installing Python"
    }
}

# ── 2. Docker Desktop ──────────────────────────────────────────────────────
step "2/8: Docker Desktop (text-to-speech engine)"

$dockerOk = $false
try {
    docker ps 2>$null | Out-Null
    ok "Docker Desktop already running"
    $dockerOk = $true
} catch {}

if (-not $dockerOk) {
    if (Test-Path "C:\Program Files\Docker\Docker\resources\bin\docker.exe") {
        warn "Docker Desktop installed but not running"
        Write-Host "  Opening Docker Desktop — please wait..."
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
        for ($i = 0; $i -lt 30; $i++) {
            try { docker ps 2>$null | Out-Null; $dockerOk = $true; ok "Docker is ready"; break }
            catch { Start-Sleep -Seconds 3 }
        }
        if (-not $dockerOk) {
            fail "Docker didn't start. Please open it manually and re-run this script."
            exit 1
        }
    }
    else {
        Write-Host ""
        Write-Host "  Docker Desktop is not installed." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  ┌─────────────────────────────────────────────────────────┐"
        Write-Host "  │  STEP 1: Install Docker Desktop                        │"
        Write-Host "  │                                                         │"
        Write-Host "  │  1. Download: docker.com/products/docker-desktop/       │"
        Write-Host "  │  2. Run Docker Desktop Installer.exe                    │"
        Write-Host "  │  3. Restart if prompted                                │"
        Write-Host "  │  4. Open Docker Desktop and accept license              │"
        Write-Host "  │  5. Wait for green 'Engine running' in bottom-left      │"
        Write-Host "  │                                                         │"
        Write-Host "  │  STEP 2: Re-run this installer script                   │"
        Write-Host "  │                                                         │"
        Write-Host "  │  The installer will pick up where it left off.          │"
        Write-Host "  └─────────────────────────────────────────────────────────┘"
        Write-Host ""
        Start-Process "https://www.docker.com/products/docker-desktop/"
        Write-Host "  After Docker is running, re-run: .\install_windows.ps1"
        Read-Host "Press Enter to exit"
        exit 0
    }
}

# ── 3. Kokoro TTS ──────────────────────────────────────────────────────────
step "3/8: Kokoro TTS (text-to-speech voices)"

try {
    $null = Invoke-WebRequest -Uri "http://localhost:8880/v1/models" -UseBasicParsing -TimeoutSec 3
    ok "Kokoro TTS already running"
} catch {
    if ($dockerOk) {
        Write-Host "Pulling Kokoro TTS container..."
        docker pull ghcr.io/remsky/kokoro-fastapi-cpu:latest 2>&1 | Select-Object -Last 3
        
        docker rm -f kokoro-tts 2>$null
        docker run -d --name kokoro-tts `
            -p 8880:8880 `
            --restart unless-stopped `
            ghcr.io/remsky/kokoro-fastapi-cpu:latest
        
        for ($i = 0; $i -lt 20; $i++) {
            try {
                $null = Invoke-WebRequest -Uri "http://localhost:8880/v1/models" -UseBasicParsing -TimeoutSec 2
                ok "Kokoro TTS is ready"; break
            } catch { Start-Sleep -Seconds 3 }
        }
    } else {
        warn "Skipping Kokoro TTS — Docker not available"
    }
}

# ── 4. Ollama ──────────────────────────────────────────────────────────────
step "4/8: Ollama (AI translation engine)"

$ollamaOk = $false
try {
    $null = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3
    ok "Ollama already running"
    $ollamaOk = $true
} catch {}

if (-not $ollamaOk) {
    $ollamaExe = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaExe) {
        warn "Ollama installed but not running. Starting..."
        Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    } else {
        Write-Host "Downloading Ollama..."
        $ollamaInstaller = "$env:TEMP\OllamaSetup.exe"
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $ollamaInstaller
        Start-Process -FilePath $ollamaInstaller -ArgumentList "/S" -Wait
        Remove-Item $ollamaInstaller
        Write-Host "Starting Ollama..."
    }
    
    for ($i = 0; $i -lt 20; $i++) {
        try {
            $null = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 2
            $ollamaOk = $true; ok "Ollama is ready"; break
        } catch { Start-Sleep -Seconds 3 }
    }
}

# ── 5. Miniforge + Python environment ──────────────────────────────────────
step "5/8: Python environment + dependencies"

if (-not (Test-Path "$MINIFORGE_DIR\Scripts\conda.exe")) {
    Write-Host "Installing Miniforge (Python 3.12)..."
    $miniforgeUrl = if ($ARCH -eq "x86_64") {
        "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe"
    } else {
        fail "32-bit Windows not supported for AI workloads"
        exit 1
    }
    $miniforgeInstaller = "$env:TEMP\Miniforge3-installer.exe"
    Invoke-WebRequest -Uri $miniforgeUrl -OutFile $miniforgeInstaller
    Start-Process -FilePath $miniforgeInstaller -ArgumentList "/S /D=$MINIFORGE_DIR" -Wait
    Remove-Item $miniforgeInstaller
    ok "Miniforge installed"
} else {
    ok "Python environment already installed"
}

$env:Path = "$MINIFORGE_DIR;$MINIFORGE_DIR\Scripts;$MINIFORGE_DIR\Library\bin;$env:Path"
& "$MINIFORGE_DIR\Scripts\conda.exe" init powershell 2>&1 | Out-Null

# Check if ggn env exists
$envs = & "$MINIFORGE_DIR\Scripts\conda.exe" env list 2>$null
if ($envs -match "ggn") {
    ok "App environment exists"
} else {
    & "$MINIFORGE_DIR\Scripts\conda.exe" create -y -n ggn python=3.12 2>&1 | Select-Object -Last 3
}

# Activate and install
& "$MINIFORGE_DIR\Scripts\conda.exe" install -y -n ggn -c conda-forge ffmpeg portaudio 2>&1 | Select-Object -Last 3

# Install Python deps
Write-Host "Installing Python packages (this may take 10-15 minutes)..."
& "$MINIFORGE_DIR\envs\ggn\python.exe" -m pip install -r "$PROJECT_DIR\requirements.txt" 2>&1 | Select-Object -Last 8
ok "Python packages installed"

# ── 6. Translation model ──────────────────────────────────────────────────
step "6/8: Translation AI model"

if ($ollamaOk) {
    # Check if translategemma exists
    $models = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing | ConvertFrom-Json
    $hasModel = ($models.models | Where-Object { $_.name -match "translategemma" }).Count -gt 0
    
    if ($hasModel) {
        ok "Translation model already available"
    } else {
        Write-Host "Downloading translategemma (~3.3 GB)..."
        Write-Host "This may take 5-15 minutes depending on your internet speed."
        ollama pull translategemma
        ok "Model downloaded"
    }
}

# ── 7. Settings ────────────────────────────────────────────────────────────
step "7/8: Configuring settings"

& "$MINIFORGE_DIR\envs\ggn\python.exe" -c @"
import json
try:
    s = json.load(open('settings.json'))
except:
    s = {}
s['translation_server'] = 'http://localhost:11434'
s['tts_server_url'] = 'http://localhost:8880/v1'
s['translation_provider'] = 'Ollama'
json.dump(s, open('settings.json', 'w'), indent=2)
"@
ok "Settings configured"

# ── 8. Desktop launcher ───────────────────────────────────────────────────
step "8/8: Desktop launcher"

$launcherPath = "$env:USERPROFILE\Desktop\GoGospelNow Translator.bat"
@"
@echo off
set "PATH=$MINIFORGE_DIR;$MINIFORGE_DIR\Scripts;$MINIFORGE_DIR\Library\bin;%PATH%"
call "$MINIFORGE_DIR\Scripts\activate.bat" ggn
cd /d "$PROJECT_DIR"
start http://localhost:7860/?__theme=dark
python main.py
pause
"@ | Out-File -FilePath $launcherPath -Encoding ASCII

# Also create Start Menu shortcut
$startMenu = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
New-Item -ItemType Directory -Force -Path "$startMenu\GoGospelNow" | Out-Null
Copy-Item $launcherPath "$startMenu\GoGospelNow\GoGospelNow Translator.bat" -Force

ok "Launcher created on Desktop and Start Menu"

# ── Done ───────────────────────────────────────────────────────────────────
echo ""
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║           ✅  Installation Complete!                    ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# Start the app
Write-Host "Starting GoGospelNow Translator..."
$env:Path = "$MINIFORGE_DIR;$MINIFORGE_DIR\Scripts;$MINIFORGE_DIR\Library\bin;$env:Path"
Start-Process -FilePath "$MINIFORGE_DIR\envs\ggn\python.exe" -ArgumentList "$PROJECT_DIR\main.py" -WindowStyle Minimized
Start-Sleep -Seconds 6
Start-Process "http://localhost:7860/?__theme=dark"

Write-Host ""
Write-Host "  To start later: double-click 'GoGospelNow Translator' on your Desktop"
Write-Host "  Or find it in: Start Menu → GoGospelNow → GoGospelNow Translator"
Write-Host ""
Write-Host "  Recommended settings:"
Write-Host "    Whisper Model:   small"
Write-Host "    Compute Device:  CUDA GPU (if NVIDIA) or CPU Only"
Write-Host "    Compute Type:    float16 (GPU) / int8 (CPU)"
Write-Host "    Translation:     translategemma"
Write-Host ""
Write-Host "  Settings page: http://localhost:7860 (click the Settings tab)"
Write-Host ""

Read-Host "Press Enter to close this window (the translator keeps running)"
