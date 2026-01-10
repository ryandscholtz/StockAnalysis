# PowerShell script to serve the test HTML file locally
Write-Host "Starting local web server for testing..." -ForegroundColor Green
Write-Host ""
Write-Host "Open your browser and navigate to:" -ForegroundColor Yellow
Write-Host "http://localhost:8000/test-frontend-with-proper-analysis.html" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Check if Python is available
try {
    $pythonVersion = python --version
    Write-Host "Using Python: $pythonVersion" -ForegroundColor Green
    python -m http.server 8000
} catch {
    Write-Host "Python not found. Trying Node.js..." -ForegroundColor Yellow
    try {
        npx serve . -p 8000
    } catch {
        Write-Host "Neither Python nor Node.js found. Please install one of them." -ForegroundColor Red
        Write-Host "Or use any web server to serve the HTML file." -ForegroundColor Yellow
    }
}

