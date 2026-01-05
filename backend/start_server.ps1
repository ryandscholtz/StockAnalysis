# Start the FastAPI backend server locally with AWS Bedrock AI
Write-Host "Starting Stock Analysis Backend Server (Local + AWS Bedrock)..." -ForegroundColor Green

# Check if virtual environment exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    .\venv\Scripts\Activate.ps1
} else {
    Write-Host "Warning: Virtual environment not found. Make sure dependencies are installed." -ForegroundColor Yellow
}

# Start the server locally with AWS Bedrock
Write-Host "Starting server on http://127.0.0.1:8000 (Local Backend + AWS Bedrock AI)" -ForegroundColor Cyan
Write-Host "Features available:" -ForegroundColor Yellow
Write-Host "  - Stock analysis using Yahoo Finance data" -ForegroundColor Green
Write-Host "  - Manual data entry" -ForegroundColor Green
Write-Host "  - PDF extraction using AWS Bedrock AI" -ForegroundColor Green
Write-Host "  - Comparison tools" -ForegroundColor Green
Write-Host "Features disabled:" -ForegroundColor Yellow
Write-Host "  - EC2 auto-management (running locally)" -ForegroundColor Red
Write-Host "  - Ollama/Local LLM (using AWS Bedrock instead)" -ForegroundColor Red

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

