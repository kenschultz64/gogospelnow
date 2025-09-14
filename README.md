# GoGospelNow Real-Time Preaching Translator

[![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png)](https://www.buymeacoffee.com/gogospelnow)

## Quick Start (read this first)

The GoGospelNow Translator program uses three background technologies to work: **Docker**, **Kokoro-Fast-TTS**, and **Ollama**. You will also need to download some AI models through Ollama.com for the translator to work. This gives you flexibility based on the processing power of your device. I would suggest something of 2–4 billion parameters for computers without a large GPU. There is a list of suggested models.  

If you do not have Docker or Ollama installed, install them first. Then install some translation models and clone the repo from GitHub or download from gogospelnow.com and set up the Python environment.

---

### Step 1: Install Docker and Ollama (once)
1. Install Docker: https://www.docker.com/
   - Desktop (macOS/Windows): https://www.docker.com/products/docker-desktop/
   - Linux Engine docs: https://docs.docker.com/engine/install/
2. Install Ollama: https://ollama.com/
3. ✅ Verify installation:
   - Run Docker Desktop (macOS/Windows) or check Docker service (Linux).
   - Confirm Docker is installed:
     ```bash
     docker --version
     ```
   - Confirm Ollama is installed and running: open your terminal and type the command.
     ```bash
     ollama run gemma3n:e2b
     ```
   - Check Ollama service at: http://localhost:11434

---

### Step 2: Clone this repository - (If you do not have git on your system go to https://git-scm.com/downloads)
```bash
git clone https://github.com/kenschultz64/gogospelnow.git
cd gogospelnow
```
✅ Verify: Ensure you see the project files by running:
```bash
ls   # or dir on Windows
```

---

### Step 3: Create and activate a virtual environment
- **Linux/macOS:**
  1. Create environment:
     ```bash
     python3 -m venv venv
     ```
  2. Activate:
     ```bash
     source venv/bin/activate
     ```
  3. ✅ Verify activation: Your terminal prompt should now show `(venv)` at the start.

- **Windows:**
  1. Create environment:
     ```powershell
     python -m venv venv
     ```
  2. Activate:
     ```powershell
     venv\Scripts\activate
     ```
--- 

### Step 4: Install FFmpeg and PortAudio

The app needs **FFmpeg** for audio processing and **PortAudio** for microphone support.

#### macOS 🍎
1. Install Homebrew (if not installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. Install packages:
   ```bash
   brew install ffmpeg portaudio libsndfile
   ```
3. ✅ Verify installation:
   ```bash
   ffmpeg -version 
   ```
  #### Linux 🐧
- **Debian/Ubuntu:**
  ```bash
  sudo apt-get update
  sudo apt-get install ffmpeg portaudio19-dev libsndfile1
  ```
- **Fedora/RHEL:**
  ```bash
  sudo dnf install ffmpeg portaudio-devel libsndfile
  ```
- **Arch Linux:**
  ```bash
  sudo pacman -S ffmpeg portaudio libsndfile
  ```
- ✅ Verify installation:
  ```bash
  ffmpeg -version
  ```
#### Windows 🪟
1. Download FFmpeg:
   - Go to [FFmpeg Builds](https://www.gyan.dev/ffmpeg/builds/)
   - Download **ffmpeg-release-full.7z**
   - Extract with [7-Zip](https://www.7-zip.org/) or right click on file and use windows extract tool.
   - Rename folder to `ffmpeg` and move to `C:\ffmpeg`
2. Add FFmpeg to Path:
   - Open **System Properties → Environment Variables → Path → New**
   - Add: `C:\ffmpeg\bin`
   - ✅ Verify:
     ```powershell
     ffmpeg -version
     ```
3. Install PortAudio:
   ```powershell
   pip install pyaudio
   ```
4. ✅ Verify:
   ```powershell
   #### Linux 🐧
- **Debian/Ubuntu:**
  ```bash
  sudo apt-get update
  sudo apt-get install ffmpeg portaudio19-dev libsndfile1
  ```
- **Fedora/RHEL:**
  ```bash
  sudo dnf install ffmpeg portaudio-devel libsndfile
  ```
- **Arch Linux:**
  ```bash
  sudo pacman -S ffmpeg portaudio libsndfile
  ```
- ✅ Verify installation:
  ```bash
  ffmpeg -version | head -n1
  python3 -c "import sounddevice as sd; print('PortAudio:', sd.get_portaudio_version())"
  ```

#### Windows 🪟
1. Download FFmpeg:
   - Go to [FFmpeg Builds](https://www.gyan.dev/ffmpeg/builds/)
   - Download **ffmpeg-release-full.7z**
   - Extract with [7-Zip](https://www.7-zip.org/)
   - Rename folder to `ffmpeg` and move to `C:\ffmpeg`
2. Add FFmpeg to Path:
   - Open **System Properties → Environment Variables → Path → New**
   - Add: `C:\ffmpeg\bin`
   - ✅ Verify:
     ```powershell
     ffmpeg -version
     ```
3. Install PortAudio:
   ```powershell
   pip install pyaudio
   ```
4. ✅ Verify:
   ```powershell
   python -c "import sounddevice as sd; print('PortAudio:', sd.get_portaudio_version())"
   ```

--- 
### Step 5: Install Python dependencies in activated directory (example (venv) PS 
```bash
pip install -r requirements.txt
```
✅ Verify: No errors should appear, and you should see installed packages with:
```bash
pip list
```

---

### Step 6: Install and Start Kokoro TTS

Run one of the following:

- **CPU:**
  ```bash
  docker run -d --restart unless-stopped --name kokoro-cpu -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu
  ```

- **GPU:**
  ```bash
  docker run -d --gpus all --restart unless-stopped --name kokoro-gpu -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-gpu
  ```

✅ Verify:
```bash
docker ps
curl http://localhost:8880/v1/voices
```
You should see a list of available voices.

---

### Step 7: Pull Ollama Models

Choose one or more (smaller models = faster):
```bash
ollama pull llama3.2:3b-instruct-q4_K_M
ollama pull gemma3n:e2b
ollama pull gemma3:4b
ollama pull granite3.3:2b
```

✅ Verify:
```bash
ollama list
```
You should see your installed models listed.

---

### Step 8: Run the App

1. Activate your virtual environment (if not active).
2. Start the app:
   ```bash
   python main.py
   ```
3. Open browser: http://localhost:7860 (tested with Chrome).

✅ Verify: The translator UI should load in your browser.

---

## Features

- Transcription: Faster-Whisper with configurable models and device/precision
- Translation: Local LLM via Ollama HTTP API
- TTS: Kokoro FastAPI server with many voices
- Real-time pipeline with buffering and VAD controls
- Presets for CPU, Balanced, and Quality
- Translation history logging

---

## Avoid Audio Loopback
Note translation audio should be isolated from the microphone or the program will loop back trying to interpret again what has been translated. Suggested use would be using an aux send to the computer’s input for the mic signal. Then use another aux send to output audio to a transmitter to send the translated audio to individual receivers with headphones. Also could be used with Bluetooth headphones depending on the distance and devices needed. Have built a version that broadcasts audio to a phone app but it is not yet ready for release.

![Audio Setup Diagram](docs/audio-setup.png)

---

[![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png)](https://www.buymeacoffee.com/gogospelnow)

