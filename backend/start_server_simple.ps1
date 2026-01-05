#!/usr/bin/env pwsh
# Simple server startup script

Write-Host "🚀 Starting Stock Analysis Backend Server..." -ForegroundColor Green

# Activate virtual environment if it exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "📦 Activating virtual environment..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
}

# Start the server
Write-Host "🌐 Starting FastAPI server on http://127.0.0.1:8000" -ForegroundColor Cyan
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload