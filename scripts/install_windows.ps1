# GoGospel installer (Windows PowerShell)
# - Creates a venv
# - Installs dependencies from requirements.txt
# - Shows how to run the app

$ErrorActionPreference = "Stop"

# Resolve project root (this script is in scripts/)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $ProjectDir

# Prefer py if available, fallback to python
$python = "py"
if (-not (Get-Command $python -ErrorAction SilentlyContinue)) {
  $python = "python"
}
if (-not (Get-Command $python -ErrorAction SilentlyContinue)) {
  Write-Error "Python not found. Please install Python 3.9+ and try again."
}

$venvDir = "venv"
$reqFile = "requirements.txt"

# Create venv if missing
if (-not (Test-Path $venvDir)) {
  Write-Host "Creating virtual environment at $venvDir ..."
  & $python -m venv $venvDir
}

# Activate venv
$activate = Join-Path $venvDir "Scripts\Activate.ps1"
. $activate

# Upgrade pip & wheel
python -m pip install -U pip wheel

# Install dependencies
if (Test-Path $reqFile) {
  Write-Host "Installing dependencies from $reqFile ..."
  pip install -r $reqFile
} else {
  Write-Warning "$reqFile not found. Skipping dependency install."
}

Write-Host ""
Write-Host "Installation complete. To run the app:" 
Write-Host "1) `"$activate`""
Write-Host "2) python main.py"
Write-Host ""
