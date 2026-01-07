@echo off
cd /d "C:\gogospelnow2"
call venv\Scripts\activate.bat

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
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://localhost:7860?__theme=dark"
    goto :done
)
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" "http://localhost:7860?__theme=dark"
    goto :done
)

REM Try Microsoft Edge (Chromium-based, works well)
where msedge >nul 2>&1
if %errorlevel% equ 0 (
    start msedge "http://localhost:7860?__theme=dark"
    goto :done
)
if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    start "" "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" "http://localhost:7860?__theme=dark"
    goto :done
)

REM Fallback to default browser (may be Firefox, but at least it opens something)
start "" "http://localhost:7860?__theme=dark"

:done
