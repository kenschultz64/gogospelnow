# Specification: Graceful Shutdown & Universal Launcher

## 1. Graceful Shutdown
**Objective:** Allow users to safely terminate the application directly from the web interface.

### Requirements:
- **UI:** Add a "Close App" or "Shutdown" button to the Gradio interface (likely in a "System" or "Settings" tab/area).
- **Behavior:**
    - Clicking the button should trigger a confirmation (optional, but good practice) or immediately initiate shutdown.
    - The system must stop all running threads (transcription, translation, audio playback, listener server).
    - The Gradio server and FastAPI app must terminate.
    - The process should exit cleanly (exit code 0).

## 2. Universal Launcher Installer
**Objective:** Provide a simple "one-click" setup script that creates a desktop shortcut for the user's operating system.

### Requirements:
- **Script:** A Python script (`install_launcher.py`) that can be run from the installed environment.
- **OS Detection:** Automatically detect Windows, Linux, or macOS.
- **Path Resolution:** Determine the absolute path of the current installation to point the shortcut to the correct start script (`launch.bat` or `start_translator.sh`).
- **Artifacts:**
    - **Windows:** Create a `.lnk` shortcut on the User's Desktop (using `winshell` or `pyshortcuts` if available, or VBScript generation to avoid dependencies).
    - **Linux:** Create a `.desktop` file in `~/Desktop` and/or `~/.local/share/applications/`.
    - **macOS:** Create a `.command` file or `.app` bundle wrapper on the Desktop.
- **Icon:** Use the existing project icon if available.

## 3. User Experience
- The user runs `python install_launcher.py` (or a wrapper script) once.
- A shortcut appears on their desktop.
- Double-clicking the shortcut starts the app.
- Clicking "Shutdown" in the app closes the window and stops the background processes.
