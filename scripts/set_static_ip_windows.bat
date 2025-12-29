@echo off
:: Launches the PowerShell script to set a static IP
:: Automatically requests Administrator privileges if needed

cd /d "%~dp0"

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process cmd -ArgumentList '/c', '\"%~f0\"' -Verb RunAs"
    exit
)

:: We have Admin rights, run the script
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "set_static_ip_windows.ps1"
pause
