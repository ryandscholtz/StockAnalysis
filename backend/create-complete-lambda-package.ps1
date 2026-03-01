# Create complete Lambda package with dependencies and application code
Write-Host "=== Creating Complete Lambda Package ===" -ForegroundColor Green

$buildDir = "lambda_build"
$zipFile = "lambda_deployment_complete.zip"

# Check if build directory exists
if (-not (Test-Path $buildDir)) {
    Write-Host "Error: Build directory $buildDir does not exist" -ForegroundColor Red
    Write-Host "Please run: pip install -r requirements-lambda.txt -t lambda_build --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.11 --implementation cp" -ForegroundColor Yellow
    exit 1
}

# Remove old zip if exists
if (Test-Path $zipFile) {
    Write-Host "Removing old zip file: $zipFile" -ForegroundColor Cyan
    Remove-Item $zipFile -Force
}

Write-Host "Copying application code to build directory..." -ForegroundColor Cyan

# Copy lambda_handler.py
Copy-Item "lambda_handler.py" "$buildDir/" -Force
Write-Host "  Copied: lambda_handler.py" -ForegroundColor Gray

# Copy app directory
if (Test-Path "app") {
    Copy-Item "app" "$buildDir/" -Recurse -Force
    Write-Host "  Copied: app/ directory" -ForegroundColor Gray
} else {
    Write-Host "  Warning: app/ directory not found" -ForegroundColor Yellow
}

# Copy .env if exists
if (Test-Path ".env") {
    Copy-Item ".env" "$buildDir/" -Force
    Write-Host "  Copied: .env" -ForegroundColor Gray
}

Write-Host "Creating zip file from $buildDir..." -ForegroundColor Cyan

# Create zip using Python (more reliable than PowerShell for large files)
$pythonScript = @"
import zipfile
import os
from pathlib import Path

build_dir = Path('$buildDir')
zip_file = Path('$zipFile')

print(f'Creating {zip_file}...')
with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(build_dir):
        for file in files:
            file_path = Path(root) / file
            arcname = file_path.relative_to(build_dir)
            zf.write(file_path, arcname)
            
size_mb = zip_file.stat().st_size / (1024 * 1024)
print(f'Package created: {size_mb:.2f} MB')
"@

$pythonScript | python

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error creating zip file" -ForegroundColor Red
    exit 1
}

# Get file size
$fileSize = (Get-Item $zipFile).Length / 1MB
Write-Host ""
Write-Host "Package created successfully!" -ForegroundColor Green
Write-Host "File: $zipFile" -ForegroundColor Cyan
Write-Host "Size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan

if ($fileSize -gt 250) {
    Write-Host "WARNING: Package exceeds Lambda limit (250 MB)" -ForegroundColor Red
    exit 1
} elseif ($fileSize -gt 50) {
    Write-Host "Note: Package is large. Will upload via S3." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Package Ready for Deployment ===" -ForegroundColor Green
