# GoGospelNow Real-Time Preaching Translator

[![Watch the video](https://img.youtube.com/vi/WRzqXt095PQ/0.jpg)](https://www.youtube.com/watch?v=WRzqXt095PQ)
[![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png)](https://www.buymeacoffee.com/gogospelnow)

## What You Need to Know Before Starting

The GoGospelNow Translator uses three background technologies:
- **Python** (version 3.11 or higher) - the programming language
- **Docker** - runs the text-to-speech service
- **Ollama** - runs the AI translation models

This guide will walk you through installing everything step-by-step. **Choose your operating system below and follow ALL the steps in order:**

- [Windows Installation Instructions](#windows-installation-)
- [macOS Installation Instructions](#macos-installation-)
- [Linux Installation Instructions](#linux-installation-)

After installation, see [Running the Translator](#running-the-translator) to start using the program.

---

# Windows Installation 🪟

Follow these steps in order. Do not skip any steps.

## Step 1: Check Python Version

1. Open **Command Prompt** or **PowerShell**:
   - Press `Windows Key + R`
   - Type `cmd` and press Enter

2. Check if Python is installed:
   ```powershell
   python --version
   ```

3. **If you see "Python 3.11" or higher** (like 3.12, 3.13), you're good! Skip to Step 2.

4. **If you see a version lower than 3.11 OR get an error**, you need to install Python:
   - Go to https://www.python.org/downloads/
   - Click the yellow "Download Python" button (get the latest version)
   - Run the installer
   - ⚠️ **IMPORTANT**: Check the box "Add Python to PATH" at the bottom of the installer
   - Click "Install Now"
   - After installation, close and reopen Command Prompt
   - Verify: `python --version` should now show 3.11 or higher

---

## Step 2: Install Docker

1. Go to https://www.docker.com/products/docker-desktop/
2. Click "Download for Windows"
3. Run the installer (Docker Desktop Installer.exe)
4. Follow the installation wizard (use default settings)
5. Restart your computer when prompted
6. After restart, launch **Docker Desktop** from the Start menu
7. Wait for Docker to start (you'll see a green icon in the system tray)

✅ **Verify Docker is working:**
```powershell
docker --version
```
You should see something like "Docker version 24.x.x"

---

## Step 3: Install Ollama

1. Go to https://ollama.com/download
2. Click "Download for Windows"
3. Run the installer (OllamaSetup.exe)
4. Follow the installation wizard
5. Ollama will start automatically after installation

✅ **Verify Ollama is working:**
```powershell
ollama --version
```
You should see the Ollama version number.

---

## Step 4: Install Git (if needed)

1. Check if Git is already installed:
   ```powershell
   git --version
   ```

2. **If you get an error**, install Git:
   - Go to https://git-scm.com/downloads
   - Click "Download for Windows"
   - Run the installer
   - Use all default settings (just keep clicking "Next")
   - After installation, close and reopen Command Prompt

---

## Step 5: Download the GoGospelNow Program

1. Open Command Prompt or PowerShell
2. Navigate to where you want to install (for example, your Documents folder):
   ```powershell
   cd Documents
   ```

3. Download the program:
   ```powershell
   git clone https://github.com/kenschultz64/gogospelnow.git
   ```

4. Go into the program folder:
   ```powershell
   cd gogospelnow
   ```

✅ **Verify:** You should see the program files:
```powershell
dir
```

---

## Step 6: Create Python Virtual Environment

1. Make sure you're in the gogospelnow folder (from Step 5)

2. Create a virtual environment:
   ```powershell
   python -m venv venv
   ```

3. Activate the virtual environment:
   ```powershell
   venv\Scripts\activate
   ```

✅ **Verify:** Your command prompt should now show `(venv)` at the beginning of the line.

---

## Step 7: Install FFmpeg (Audio Processing)

1. Go to https://www.gyan.dev/ffmpeg/builds/
2. Download **ffmpeg-release-full.7z** (the first link under "release builds")
3. Extract the downloaded file:
   - Right-click the file
   - Choose "Extract All" (or use 7-Zip if you have it)
4. Rename the extracted folder to just `ffmpeg`
5. Move the `ffmpeg` folder to `C:\` (so the path is `C:\ffmpeg`)

6. Add FFmpeg to your system PATH:
   - Press `Windows Key` and type "environment variables"
   - Click "Edit the system environment variables"
   - Click "Environment Variables" button
   - Under "System variables", find and select "Path"
   - Click "Edit"
   - Click "New"
   - Type: `C:\ffmpeg\bin`
   - Click "OK" on all windows
   - **Close and reopen Command Prompt**

✅ **Verify FFmpeg is working:**
```powershell
ffmpeg -version
```

---

## Step 8: Install Python Dependencies

1. Make sure your virtual environment is activated (you should see `(venv)` in your prompt)
2. If not activated, run: `venv\Scripts\activate`

3. Install required Python packages:
   ```powershell
   pip install -r requirements.txt
   ```
   This will take a few minutes. Wait for it to complete.

✅ **Verify:** No error messages should appear. Check installed packages:
```powershell
pip list
```

---

## Step 9: Start the Text-to-Speech Service

Choose ONE of these commands based on your computer:

**If you have a gaming computer with an NVIDIA graphics card:**
```powershell
docker run -d --gpus all --restart unless-stopped --name kokoro-gpu -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-gpu
```

**If you have a regular computer (no gaming graphics card):**
```powershell
docker run -d --restart unless-stopped --name kokoro-cpu -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu
```

This will download and start the text-to-speech service. It may take several minutes the first time.

✅ **Verify it's running:**
```powershell
docker ps
```
You should see a container named "kokoro-cpu" or "kokoro-gpu" running.

---

## Step 10: Download AI Translation Models

You need at least one translation model. For most computers, start with a smaller model:

**Recommended for most computers (choose ONE):**
```powershell
ollama pull gemma3n:e2b
```

**Other options (you can install multiple):**
```powershell
ollama pull llama3.2:3b-instruct-q4_K_M
```
```powershell
ollama pull granite3.3:2b
```

Each model will take several minutes to download.

✅ **Verify your models are installed:**
```powershell
ollama list
```
You should see your downloaded models listed.

---

## Step 11: Test the Translator

1. Make sure your virtual environment is activated (you should see `(venv)`)
2. If not, activate it: `venv\Scripts\activate`

3. Start the translator:
   ```powershell
   python main.py
   ```

4. **Keep this Command Prompt window open!** The program needs it to stay running.

5. Open your web browser (Chrome recommended) and go to:
   ```
   http://localhost:7860
   ```

✅ **Verify:** You should see the GoGospelNow translator interface in your browser.

6. **For future use:** After you've verified everything works, you can use the shortcut:
   - Double-click `launch.bat` in the gogospelnow folder

---

# macOS Installation 🍎

Follow these steps in order. Do not skip any steps.

## Step 1: Check Python Version

1. Open **Terminal**:
   - Press `Command + Space`
   - Type "Terminal" and press Enter

2. Check if Python 3.11 or higher is installed:
   ```bash
   python3 --version
   ```

3. **If you see "Python 3.11" or higher** (like 3.12, 3.13), you're good! Skip to Step 2.

4. **If you see a version lower than 3.11**, you need to install a newer version:
   - Go to https://www.python.org/downloads/
   - Click the yellow "Download Python" button (get the latest version)
   - Open the downloaded .pkg file
   - Follow the installation wizard
   - After installation, close and reopen Terminal
   - Verify: `python3 --version` should now show 3.11 or higher

---

## Step 2: Install Homebrew (Package Manager)

Homebrew makes it easy to install software on Mac.

1. Check if Homebrew is already installed:
   ```bash
   brew --version
   ```

2. **If you get an error**, install Homebrew:
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   - Press Enter when prompted
   - Enter your Mac password when asked (you won't see it as you type)
   - Wait for installation to complete (may take several minutes)

✅ **Verify Homebrew is installed:**
```bash
brew --version
```

---

## Step 3: Install Docker

1. Go to https://www.docker.com/products/docker-desktop/
2. Click "Download for Mac"
   - Choose the correct version for your Mac:
     - **Apple Silicon** (M1, M2, M3 chips) - newer Macs
     - **Intel Chip** - older Macs
3. Open the downloaded .dmg file
4. Drag Docker to your Applications folder
5. Open Docker from Applications
6. Follow the setup wizard
7. Enter your Mac password when prompted
8. Wait for Docker to start (you'll see a whale icon in the menu bar)

✅ **Verify Docker is working:**
```bash
docker --version
```

---

## Step 4: Install Ollama

1. Go to https://ollama.com/download
2. Click "Download for macOS"
3. Open the downloaded file
4. Drag Ollama to your Applications folder
5. Open Ollama from Applications
6. Ollama will appear in your menu bar (top of screen)

✅ **Verify Ollama is working:**
```bash
ollama --version
```

---

## Step 5: Install Git (if needed)

Git is usually pre-installed on macOS, but let's check:

1. Check if Git is installed:
   ```bash
   git --version
   ```

2. **If you get an error**, macOS will prompt you to install Command Line Tools. Click "Install" and follow the prompts.

---

## Step 6: Download the GoGospelNow Program

1. In Terminal, navigate to where you want to install (for example, your Documents folder):
   ```bash
   cd ~/Documents
   ```

2. Download the program:
   ```bash
   git clone https://github.com/kenschultz64/gogospelnow.git
   ```

3. Go into the program folder:
   ```bash
   cd gogospelnow
   ```

✅ **Verify:** You should see the program files:
```bash
ls
```

---

## Step 7: Create Python Virtual Environment

1. Make sure you're in the gogospelnow folder (from Step 6)

2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   ```

3. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

✅ **Verify:** Your terminal prompt should now show `(venv)` at the beginning.

---

## Step 8: Install Required Software (FFmpeg, PortAudio, etc.)

1. Install audio and GUI packages:
   ```bash
   brew install ffmpeg portaudio libsndfile python-tk@3.11
   ```
   This will take several minutes.

✅ **Verify installations:**
```bash
ffmpeg -version
```
```bash
python3 -m tkinter
```
A small window should appear (you can close it).

---

## Step 9: Install Python Dependencies

1. Make sure your virtual environment is activated (you should see `(venv)` in your prompt)
2. If not activated, run: `source venv/bin/activate`

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
   This will take a few minutes. Wait for it to complete.

✅ **Verify:** No error messages should appear. Check installed packages:
```bash
pip list
```

---

## Step 10: Start the Text-to-Speech Service

Choose ONE of these commands based on your Mac:

**If you have an Apple Silicon Mac (M1, M2, M3) or Intel Mac with dedicated graphics:**
```bash
docker run -d --gpus all --restart unless-stopped --name kokoro-gpu -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-gpu
```

**If you have an older Intel Mac:**
```bash
docker run -d --restart unless-stopped --name kokoro-cpu -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu
```

This will download and start the text-to-speech service. It may take several minutes the first time.

✅ **Verify it's running:**
```bash
docker ps
```
You should see a container named "kokoro-cpu" or "kokoro-gpu" running.

---

## Step 11: Download AI Translation Models

You need at least one translation model. For most computers, start with a smaller model:

**Recommended for most computers (choose ONE):**
```bash
ollama pull gemma3n:e2b
```

**Other options (you can install multiple):**
```bash
ollama pull llama3.2:3b-instruct-q4_K_M
```
```bash
ollama pull granite3.3:2b
```

Each model will take several minutes to download.

✅ **Verify your models are installed:**
```bash
ollama list
```
You should see your downloaded models listed.

---

## Step 12: Test the Translator

1. Make sure your virtual environment is activated (you should see `(venv)`)
2. If not, activate it: `source venv/bin/activate`

3. Start the translator:
   ```bash
   python main.py
   ```

4. **Keep this Terminal window open!** The program needs it to stay running.

5. Open your web browser (Chrome recommended) and go to:
   ```
   http://localhost:7860
   ```

✅ **Verify:** You should see the GoGospelNow translator interface in your browser.

6. **For future use:** After you've verified everything works, you can use the shortcut:
   - In Terminal, navigate to the gogospelnow folder
   - Run: `./start_translator.sh`

---

# Linux Installation 🐧

Follow these steps in order. Do not skip any steps.

## Step 1: Check Python Version

1. Open **Terminal** (usually Ctrl+Alt+T)

2. Check if Python 3.11 or higher is installed:
   ```bash
   python3 --version
   ```

3. **If you see "Python 3.11" or higher** (like 3.12, 3.13), you're good! Skip to Step 2.

4. **If you see a version lower than 3.11**, install a newer version:

   **For Ubuntu/Debian:**
   ```bash
   sudo apt update
   sudo apt install software-properties-common
   sudo add-apt-repository ppa:deadsnakes/ppa
   sudo apt update
   sudo apt install python3.11 python3.11-venv python3.11-dev
   ```

   **For Fedora/RHEL:**
   ```bash
   sudo dnf install python3.11 python3.11-devel
   ```

   **For Arch Linux:**
   ```bash
   sudo pacman -S python
   ```

✅ **Verify:** `python3.11 --version` should show 3.11 or higher

---

## Step 2: Install Docker

**For Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

**For Fedora/RHEL:**
```bash
sudo dnf install docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

**For Arch Linux:**
```bash
sudo pacman -S docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

**Important:** After running these commands, log out and log back in for the docker group changes to take effect.

✅ **Verify Docker is working:**
```bash
docker --version
```

---

## Step 3: Install Ollama

1. Download and install Ollama:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. Start Ollama service:
   ```bash
   sudo systemctl start ollama
   sudo systemctl enable ollama
   ```

✅ **Verify Ollama is working:**
```bash
ollama --version
```

---

## Step 4: Install Git (if needed)

1. Check if Git is installed:
   ```bash
   git --version
   ```

2. **If you get an error**, install Git:

   **For Ubuntu/Debian:**
   ```bash
   sudo apt install git
   ```

   **For Fedora/RHEL:**
   ```bash
   sudo dnf install git
   ```

   **For Arch Linux:**
   ```bash
   sudo pacman -S git
   ```

---

## Step 5: Download the GoGospelNow Program

1. Navigate to where you want to install (for example, your home folder):
   ```bash
   cd ~
   ```

2. Download the program:
   ```bash
   git clone https://github.com/kenschultz64/gogospelnow.git
   ```

3. Go into the program folder:
   ```bash
   cd gogospelnow
   ```

✅ **Verify:** You should see the program files:
```bash
ls
```

---

## Step 6: Create Python Virtual Environment

1. Make sure you're in the gogospelnow folder (from Step 5)

2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   ```
   (If you installed Python 3.11 specifically, use: `python3.11 -m venv venv`)

3. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

✅ **Verify:** Your terminal prompt should now show `(venv)` at the beginning.

---

## Step 7: Install Required Software (FFmpeg, PortAudio, etc.)

**For Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg portaudio19-dev libsndfile1 python3-tk
```

**For Fedora/RHEL:**
```bash
sudo dnf install ffmpeg portaudio-devel libsndfile python3-tkinter
```

**For Arch Linux:**
```bash
sudo pacman -S ffmpeg portaudio libsndfile tk
```

✅ **Verify installations:**
```bash
ffmpeg -version
```
```bash
python3 -m tkinter
```
A small window should appear (you can close it).

---

## Step 8: Install Python Dependencies

1. Make sure your virtual environment is activated (you should see `(venv)` in your prompt)
2. If not activated, run: `source venv/bin/activate`

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
   This will take a few minutes. Wait for it to complete.

✅ **Verify:** No error messages should appear. Check installed packages:
```bash
pip list
```

---

## Step 9: Start the Text-to-Speech Service

Choose ONE of these commands based on your computer:

**If you have an NVIDIA graphics card with CUDA support:**
```bash
docker run -d --gpus all --restart unless-stopped --name kokoro-gpu -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-gpu
```

**If you have a regular computer (no gaming graphics card):**
```bash
docker run -d --restart unless-stopped --name kokoro-cpu -p 8880:8880 ghcr.io/remsky/kokoro-fastapi-cpu
```

This will download and start the text-to-speech service. It may take several minutes the first time.

✅ **Verify it's running:**
```bash
docker ps
```
You should see a container named "kokoro-cpu" or "kokoro-gpu" running.

---

## Step 10: Download AI Translation Models

You need at least one translation model. For most computers, start with a smaller model:

**Recommended for most computers (choose ONE):**
```bash
ollama pull gemma3n:e2b
```

**Other options (you can install multiple):**
```bash
ollama pull llama3.2:3b-instruct-q4_K_M
```
```bash
ollama pull granite3.3:2b
```

Each model will take several minutes to download.

✅ **Verify your models are installed:**
```bash
ollama list
```
You should see your downloaded models listed.

---

## Step 11: Test the Translator

1. Make sure your virtual environment is activated (you should see `(venv)`)
2. If not, activate it: `source venv/bin/activate`

3. Start the translator:
   ```bash
   python main.py
   ```

4. **Keep this Terminal window open!** The program needs it to stay running.

5. Open your web browser (Chrome recommended) and go to:
   ```
   http://localhost:7860
   ```

✅ **Verify:** You should see the GoGospelNow translator interface in your browser.

6. **For future use:** After you've verified everything works, you can use the shortcut:
   - In Terminal, navigate to the gogospelnow folder
   - Run: `./start_translator.sh`

---

# Running the Translator

After you've completed the installation for your operating system:

## Starting the Program

**Windows:**
- Double-click `launch.bat` in the gogospelnow folder
- OR open Command Prompt, navigate to the folder, and run: `python main.py`

**macOS/Linux:**
- Open Terminal, navigate to the gogospelnow folder
- Run: `./start_translator.sh`
- OR run: `python main.py`

## Using the Translator

1. Keep the terminal/command prompt window open while using the program
2. Open your web browser and go to: http://localhost:7860
3. The translator interface will load
4. Select your translation model from the dropdown
5. Choose your source and target languages
6. Click "Start" to begin translating 
---

## Features

- **Transcription:** Faster-Whisper with configurable selectable models.
- **Translation:** Local LLM via Ollama API so you can use the latest open-source models as they are released.
- **TTS:** 
  - **Local:** Kokoro FastAPI server supporting **9 languages** (American/British English, Spanish, French, Italian, Brazilian Portuguese, Japanese, Chinese, and Hindi).
  - **Cloud:** Google Cloud TTS supporting **30+ languages** (requires API key).
- **Secondary Output Monitor:** Dedicated translation display window that can be moved to any connected monitor.
  - **Smart Monitor Selection:** Monitors are numbered left-to-right (Monitor 1, Monitor 2, etc.) for intuitive selection.
  - **Custom Window Sizes:** Set custom Width × Height for the display window, or use preset resolutions.
  - **Worship-Friendly Close Button:** Subtle close button that's nearly invisible (appears on hover). Press Escape key to close.
  - **Hotkey Support:** Press 'M' to cycle through monitors, Escape to close.
  - **Cross-Platform:** Works on Windows, macOS, and Linux.
- **Performance Tuning:** Manual control over all timing and VAD parameters via sliders.
- **Expanded API Support:** Integrate with major cloud AI providers including OpenAI, Groq, xAI (Grok), and Mistral, in addition to local Ollama models.
- **History:** Translation history logging.
- **Offline Capable:** Works completely locally (Internet required only for setup and Google Cloud TTS).

---

## Configuring Cloud Translation Providers (Optional)

You can configure the translator to use cloud-based LLMs for potentially higher quality or faster translations. This requires API keys from the respective providers.

1.  **Open the Settings Tab** in the application interface.
2.  **Enter your API Keys** for the services you wish to use:
    *   **OpenAI:** `https://platform.openai.com/api-keys`
    *   **Groq:** `https://console.groq.com/keys`
    *   **Grok (xAI):** `https://console.x.ai/`
    *   **Mistral:** `https://console.mistral.ai/api-keys`
3.  **Click "Save Server Settings".**
4.  **Select the Provider** in the main "Speech Translator" tab using the "Translation Provider" dropdown.

---

## Configuring Google Cloud Text-to-Speech (Optional)

If you want to use Google Cloud Text-to-Speech voices in addition to the local Kokoro voices, you'll need to set up a Google Cloud API key. **This is optional** - the translator works perfectly with just the local Kokoro voices.

### Getting Your Google Cloud API Key

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the "Cloud Text-to-Speech API" for your project
4. Go to "APIs & Services" → "Credentials"
5. Click "Create Credentials" → "API Key"
6. Copy your API key (it will look like: `AIzaSyC...`)

### Securely Adding Your API Key

**IMPORTANT:** Never hardcode your API key in files that might be shared or committed to version control. Use environment variables instead.

#### Windows:

1. Open Command Prompt or PowerShell
2. Set the environment variable for the current session:
   ```powershell
   $env:GOOGLE_API_KEY="your-api-key-here"
   ```

3. To make it permanent (persists after reboot):
   ```powershell
   setx GOOGLE_API_KEY "your-api-key-here"
   ```
   Then close and reopen your terminal.

4. Verify it's set:
   ```powershell
   echo $env:GOOGLE_API_KEY
   ```

#### macOS/Linux:

1. Open Terminal
2. Edit your shell configuration file:
   - For bash: `nano ~/.bashrc` or `nano ~/.bash_profile`
   - For zsh (default on newer macOS): `nano ~/.zshrc`

3. Add this line at the end of the file:
   ```bash
   export GOOGLE_API_KEY="your-api-key-here"
   ```

4. Save and exit (Ctrl+X, then Y, then Enter in nano)

5. Reload your configuration:
   ```bash
   source ~/.bashrc    # or ~/.zshrc or ~/.bash_profile
   ```

6. Verify it's set:
   ```bash
   echo $GOOGLE_API_KEY
   ```

### Using the API Key

Once the environment variable is set:
1. Restart the translator application
2. The program will automatically detect and use your Google API key
3. You'll now have access to Google Cloud voices in addition to Kokoro voices

**Security Note:** The API key is stored as an environment variable on your computer only. It's never saved in the program files or shared publicly.

---

## Avoid Audio Loopback
Note translation audio should be isolated from the microphone or the program will loop back trying to interpret again what has been translated. Suggested use would be using an aux send to the computer’s input for the mic signal. Then use another aux send to output audio to a transmitter to send the translated audio to individual receivers with headphones. Also could be used with Bluetooth headphones depending on the distance and devices needed. Have built a version that broadcasts audio to a phone app but it is not yet ready for release.

![Audio Setup Diagram](docs/audio-setup.png)
[![Watch the video](https://img.youtube.com/vi/ZdBDW6Pw4qE/0.jpg)](https://www.youtube.com/watch?v=ZdBDW6Pw4qE&t=11s)
---

## Additional Documentation

For more detailed information, please refer to these additional guides:

- **[TTS Supported Languages](TTS_SUPPORTED_LANGUAGES.md)** - Complete list of Kokoro and Google Cloud Text-to-Speech voices
- **[Performance Tuning Guide](PERFORMANCE_TUNING_GUIDE.md)** - Optimize the translator for your computer's hardware
- **[Tuning Guide](TUNING.md)** - Advanced configuration and settings
- **[Security Setup](SECURITY_SETUP.md)** - Best practices for securing your installation
- **[Updates](UPDATES.md)** - Changelog and version history
- **[Third Party Licenses](THIRD_PARTY.md)** - Open source licenses and attributions

---

[![Buy Me A Coffee](https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png)](https://www.buymeacoffee.com/gogospelnow)

