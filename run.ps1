# LazySort – Windows PowerShell Run Script
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "       Starting LazySort – AI File Organizer..." -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

# Check if .venv exists
if (Test-Path ".\.venv\Scripts\streamlit.exe") {
    Write-Host "Starting Streamlit with local virtual environment..." -ForegroundColor Green
    & ".\.venv\Scripts\streamlit.exe" run app.py
} else {
    Write-Host "Virtual environment not detected. Running using system python..." -ForegroundColor Yellow
    streamlit run app.py
}
