# Start the FastAPI backend server
Write-Host "Starting Stock Analysis Backend Server..." -ForegroundColor Green

# Check if virtual environment exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    .\venv\Scripts\Activate.ps1
} else {
    Write-Host "Warning: Virtual environment not found. Make sure dependencies are installed." -ForegroundColor Yellow
}

# Start the server
Write-Host "Starting server on http://127.0.0.1:8000" -ForegroundColor Cyan
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

