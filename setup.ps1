# LazySort – Windows PowerShell One-Click Setup Script
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "       LazySort – AI File Organizer Setup" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# 1. Verify Python
Write-Host "`n[1/4] Checking Python installation..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python was not found in your system PATH." -ForegroundColor Red
    Write-Host "Please download Python 3.10+ from https://www.python.org/downloads/ and check 'Add Python to PATH'." -ForegroundColor Yellow
    Exit 1
}
Write-Host "Found: $pythonVersion" -ForegroundColor Green

# 2. Setup Virtual Environment
Write-Host "`n[2/4] Setting up Python virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "Virtual environment created in .venv" -ForegroundColor Green
} else {
    Write-Host "Virtual environment already exists in .venv" -ForegroundColor Green
}

# 3. Activate and Install Requirements
Write-Host "`n[3/4] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\pip.exe" install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Some packages encountered an installation issue." -ForegroundColor Yellow
} else {
    Write-Host "Dependencies installed successfully!" -ForegroundColor Green
}

# 4. Generate Initial Sample Files
Write-Host "`n[4/4] Generating initial demo dataset..." -ForegroundColor Yellow
& ".\.venv\Scripts\python.exe" -c "from pathlib import Path; from core.demo_data import generate_sample_dataset; generate_sample_dataset(Path('sample_files'))"
Write-Host "Sample files ready in 'sample_files/' folder." -ForegroundColor Green

Write-Host "`n======================================================" -ForegroundColor Cyan
Write-Host "Setup Complete! You can now start the app by running:" -ForegroundColor Green
Write-Host "   .\run.ps1" -ForegroundColor Yellow
Write-Host "Or manually:" -ForegroundColor Green
Write-Host "   .\.venv\Scripts\streamlit.exe run app.py" -ForegroundColor Yellow
Write-Host "======================================================" -ForegroundColor Cyan
