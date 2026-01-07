#!/usr/bin/env python3
"""
GoGospelNow Universal Launcher Installer

This script creates a desktop shortcut for the GoGospelNow Translator application.
Supports Windows, Linux, and macOS.

Usage:
    python install_launcher.py

The script will:
1. Detect your operating system
2. Create a desktop shortcut pointing to the application
3. Configure it to launch the app and open a browser window
"""

import os
import sys
import platform
import subprocess
from pathlib import Path


def get_project_root():
    """Get the absolute path to the project root directory."""
    return Path(__file__).parent.resolve()


def get_desktop_path():
    """Get the path to the user's Desktop folder."""
    system = platform.system()
    
    if system == "Windows":
        # Try multiple methods to get Desktop path
        desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
        if not desktop.exists():
            desktop = Path(os.environ.get("HOMEDRIVE", "C:")) / os.environ.get("HOMEPATH", "\\Users\\Default") / "Desktop"
        return desktop
    
    elif system == "Darwin":  # macOS
        return Path.home() / "Desktop"
    
    else:  # Linux and others
        # Check XDG user dirs first
        xdg_desktop = os.environ.get("XDG_DESKTOP_DIR")
        if xdg_desktop:
            return Path(xdg_desktop)
        return Path.home() / "Desktop"


def create_windows_shortcut(project_root: Path, desktop: Path) -> bool:
    """
    Create a Windows .lnk shortcut using VBScript (no external dependencies).
    The shortcut will open the browser automatically after starting the server.
    """
    shortcut_path = desktop / "GoGospelNow Translator.lnk"
    launch_script = project_root / "launch.bat"
    icon_path = project_root / "icon.ico"
    
    # Check if icon exists
    if not icon_path.exists():
        print(f"⚠️  Icon file not found at {icon_path}")
        print("   Shortcut will be created without a custom icon.")
        icon_path = None
    
    # Create a wrapper batch file that opens browser after launch
    wrapper_bat = project_root / "launch_with_browser.bat"
    wrapper_content = f'''@echo off
cd /d "{project_root}"
call venv\\Scripts\\activate.bat

REM Start the Python server in a minimized window
start /min "GoGospelNow Server" python main.py

REM Wait for server to start
timeout /t 4 /nobreak > nul

REM Try to open in Chrome, Edge, or Chromium (Firefox has compatibility issues)
REM Check for Chrome first
where chrome >nul 2>&1
if %errorlevel% equ 0 (
    start chrome "http://localhost:7860?__theme=dark"
    goto :done
)

REM Check common Chrome installation paths
if exist "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" (
    start "" "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" "http://localhost:7860?__theme=dark"
    goto :done
)
if exist "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe" (
    start "" "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe" "http://localhost:7860?__theme=dark"
    goto :done
)

REM Try Microsoft Edge (Chromium-based, works well)
where msedge >nul 2>&1
if %errorlevel% equ 0 (
    start msedge "http://localhost:7860?__theme=dark"
    goto :done
)
if exist "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" (
    start "" "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" "http://localhost:7860?__theme=dark"
    goto :done
)

REM Fallback to default browser (may be Firefox, but at least it opens something)
start "" "http://localhost:7860?__theme=dark"

:done
'''
    
    try:
        with open(wrapper_bat, 'w') as f:
            f.write(wrapper_content)
        print(f"✓ Created launcher script: {wrapper_bat}")
    except Exception as e:
        print(f"✗ Failed to create launcher script: {e}")
        return False
    
    # VBScript to create the shortcut with icon
    icon_line = f'shortcut.IconLocation = "{icon_path}"' if icon_path else ''
    vbs_script = f'''
Set WshShell = CreateObject("WScript.Shell")
Set shortcut = WshShell.CreateShortcut("{shortcut_path}")
shortcut.TargetPath = "{wrapper_bat}"
shortcut.WorkingDirectory = "{project_root}"
shortcut.Description = "GoGospelNow Real-Time Preaching Translator"
shortcut.WindowStyle = 7
{icon_line}
shortcut.Save
WScript.Echo "Shortcut created successfully!"
'''
    
    # Write VBS to temp file and execute
    vbs_path = project_root / "create_shortcut.vbs"
    try:
        with open(vbs_path, 'w') as f:
            f.write(vbs_script)
        
        # Execute the VBScript
        result = subprocess.run(
            ["cscript", "//nologo", str(vbs_path)],
            capture_output=True,
            text=True,
            cwd=str(project_root)
        )
        
        if result.returncode == 0:
            print(f"✓ Created desktop shortcut: {shortcut_path}")
            # Clean up VBS file
            vbs_path.unlink()
            return True
        else:
            print(f"✗ VBScript error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Failed to create Windows shortcut: {e}")
        return False


def create_linux_desktop_file(project_root: Path, desktop: Path) -> bool:
    """
    Create a Linux .desktop file for the application.
    """
    shortcut_path = desktop / "gogospelnow.desktop"
    start_script = project_root / "start_translator.sh"
    icon_path = project_root / "listener-app" / "icon.svg"
    
    # Create a wrapper script that also opens the browser
    wrapper_script = project_root / "launch_with_browser.sh"
    wrapper_content = f'''#!/bin/bash
cd "{project_root}"

# Activate virtual environment and start server in background
source venv/bin/activate
python3 main.py &
SERVER_PID=$!

# Wait for server to start
sleep 4

# Open browser - prefer Chrome/Chromium (Firefox has compatibility issues)
URL="http://localhost:7860?__theme=dark"

if command -v google-chrome &> /dev/null; then
    google-chrome "$URL" &
elif command -v google-chrome-stable &> /dev/null; then
    google-chrome-stable "$URL" &
elif command -v chromium &> /dev/null; then
    chromium "$URL" &
elif command -v chromium-browser &> /dev/null; then
    chromium-browser "$URL" &
elif command -v brave-browser &> /dev/null; then
    brave-browser "$URL" &
elif command -v xdg-open &> /dev/null; then
    # Fallback to system default (may be Firefox)
    xdg-open "$URL"
else
    echo "Please open your browser to: $URL"
fi

# Wait for server process
wait $SERVER_PID
'''
    
    try:
        with open(wrapper_script, 'w') as f:
            f.write(wrapper_content)
        os.chmod(wrapper_script, 0o755)
        print(f"✓ Created launcher script: {wrapper_script}")
    except Exception as e:
        print(f"✗ Failed to create launcher script: {e}")
        return False
    
    # .desktop file content
    desktop_content = f'''[Desktop Entry]
Version=1.0
Type=Application
Name=GoGospelNow Translator
Comment=Real-Time Preaching Translator
Exec="{wrapper_script}"
Icon={icon_path}
Terminal=false
Categories=Audio;AudioVideo;Utility;
StartupNotify=true
'''
    
    try:
        with open(shortcut_path, 'w') as f:
            f.write(desktop_content)
        os.chmod(shortcut_path, 0o755)
        print(f"✓ Created desktop shortcut: {shortcut_path}")
        
        # Also copy to applications folder for app menu
        applications_dir = Path.home() / ".local" / "share" / "applications"
        if applications_dir.exists():
            app_shortcut = applications_dir / "gogospelnow.desktop"
            with open(app_shortcut, 'w') as f:
                f.write(desktop_content)
            os.chmod(app_shortcut, 0o755)
            print(f"✓ Added to applications menu: {app_shortcut}")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to create Linux desktop file: {e}")
        return False


def create_macos_command(project_root: Path, desktop: Path) -> bool:
    """
    Create a macOS .command file or .app bundle.
    """
    # Create a .command file (simpler, works well)
    command_path = desktop / "GoGospelNow Translator.command"
    start_script = project_root / "start_translator.sh"
    
    command_content = f'''#!/bin/bash
cd "{project_root}"

# Activate virtual environment and start server in background
source venv/bin/activate
python3 main.py &
SERVER_PID=$!

# Wait for server to start
sleep 4

# Open browser - prefer Chrome or Safari (Firefox has compatibility issues)
URL="http://localhost:7860?__theme=dark"

# Check for Chrome first
if [ -d "/Applications/Google Chrome.app" ]; then
    open -a "Google Chrome" "$URL"
# Then try Safari (works well on macOS)
elif [ -d "/Applications/Safari.app" ]; then
    open -a "Safari" "$URL"
# Try Chromium
elif [ -d "/Applications/Chromium.app" ]; then
    open -a "Chromium" "$URL"
# Try Brave
elif [ -d "/Applications/Brave Browser.app" ]; then
    open -a "Brave Browser" "$URL"
# Fallback to system default
else
    open "$URL"
fi

# Wait for server process
wait $SERVER_PID
'''
    
    try:
        with open(command_path, 'w') as f:
            f.write(command_content)
        os.chmod(command_path, 0o755)
        print(f"✓ Created launcher: {command_path}")
        print("  (You can drag this to your Dock for easy access)")
        return True
        
    except Exception as e:
        print(f"✗ Failed to create macOS launcher: {e}")
        return False


def main():
    print("=" * 60)
    print("  GoGospelNow Universal Launcher Installer")
    print("=" * 60)
    print()
    
    project_root = get_project_root()
    desktop = get_desktop_path()
    system = platform.system()
    
    print(f"📁 Project directory: {project_root}")
    print(f"🖥️  Desktop directory: {desktop}")
    print(f"💻 Operating System: {system}")
    print()
    
    # Verify project structure
    if system == "Windows":
        required_file = project_root / "launch.bat"
    else:
        required_file = project_root / "start_translator.sh"
    
    if not required_file.exists():
        print(f"⚠️  Warning: {required_file.name} not found. The launcher may not work correctly.")
    
    if not (project_root / "main.py").exists():
        print("✗ Error: main.py not found. Are you running this from the project directory?")
        sys.exit(1)
    
    if not desktop.exists():
        print(f"⚠️  Desktop folder not found at {desktop}")
        try:
            desktop.mkdir(parents=True, exist_ok=True)
            print(f"  Created: {desktop}")
        except Exception as e:
            print(f"✗ Could not create desktop folder: {e}")
            sys.exit(1)
    
    print("Creating launcher...")
    print()
    
    success = False
    if system == "Windows":
        success = create_windows_shortcut(project_root, desktop)
    elif system == "Darwin":
        success = create_macos_command(project_root, desktop)
    else:  # Linux and others
        success = create_linux_desktop_file(project_root, desktop)
    
    print()
    if success:
        print("=" * 60)
        print("  ✅ Installation Complete!")
        print("=" * 60)
        print()
        print("You can now launch GoGospelNow Translator by:")
        if system == "Windows":
            print("  • Double-clicking 'GoGospelNow Translator' on your Desktop")
        elif system == "Darwin":
            print("  • Double-clicking 'GoGospelNow Translator.command' on your Desktop")
            print("  • Drag it to your Dock for quick access")
        else:
            print("  • Double-clicking 'gogospelnow.desktop' on your Desktop")
            print("  • Finding 'GoGospelNow Translator' in your applications menu")
        print()
        print("The app will start and automatically open in your default browser.")
        print("Use the 'Shutdown App' button in the app to close it cleanly.")
    else:
        print("=" * 60)
        print("  ❌ Installation Failed")
        print("=" * 60)
        print()
        print("Please try running the application manually:")
        if system == "Windows":
            print("  1. Open a command prompt in this directory")
            print("  2. Run: launch.bat")
        else:
            print("  1. Open a terminal in this directory")
            print("  2. Run: ./start_translator.sh")
        sys.exit(1)


if __name__ == "__main__":
    main()
