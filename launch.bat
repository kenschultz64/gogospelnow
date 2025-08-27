@echo off

echo "Starting GoGospelNow Translator..."

REM Activate the virtual environment
call venv\Scripts\activate.bat

REM Launch the Python application in a separate window
start "GoGospelNow Translator" python main.py

echo "Waiting for the server to initialize..."
REM Wait for 5 seconds to give the server time to start
timeout /t 5 /nobreak > nul

echo "Launching application in Chrome..."
REM Launch Chrome to the application's URL
start chrome http://localhost:7860

echo "Launch sequence complete."
pause
