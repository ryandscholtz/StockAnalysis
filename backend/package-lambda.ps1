# PowerShell script to package the backend for Lambda deployment
param(
    [Parameter(Mandatory=$false)]
    [string]$OutputDir = "dist",
    
    [Parameter(Mandatory=$false)]
    [switch]$Clean = $false
)

Write-Host "Packaging Stock Analysis API for Lambda deployment" -ForegroundColor Green

# Clean output directory if requested
if ($Clean -and (Test-Path $OutputDir)) {
    Write-Host "Cleaning output directory: $OutputDir" -ForegroundColor Yellow
    Remove-Item -Recurse -Force $OutputDir
}

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

# Check if virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
pip install mangum  # For Lambda ASGI adapter

# Copy application code
Write-Host "Copying application code..." -ForegroundColor Yellow
Copy-Item -Recurse -Path "app" -Destination "$OutputDir\app"
Copy-Item -Path "lambda_handler.py" -Destination "$OutputDir\main.py"

# Copy dependencies from virtual environment
Write-Host "Copying dependencies..." -ForegroundColor Yellow
$sitePackages = "venv\Lib\site-packages"
if (Test-Path $sitePackages) {
    # Copy all packages except some large/unnecessary ones
    $excludePatterns = @(
        "*__pycache__*",
        "*.pyc",
        "*.pyo",
        "*test*",
        "*Test*",
        "pip*",
        "setuptools*",
        "wheel*",
        "*.dist-info",
        "*.egg-info"
    )
    
    Get-ChildItem -Path $sitePackages | ForEach-Object {
        $shouldExclude = $false
        foreach ($pattern in $excludePatterns) {
            if ($_.Name -like $pattern) {
                $shouldExclude = $true
                break
            }
        }
        
        if (-not $shouldExclude) {
            $destPath = Join-Path $OutputDir $_.Name
            if ($_.PSIsContainer) {
                Copy-Item -Recurse -Path $_.FullName -Destination $destPath -Force
            } else {
                Copy-Item -Path $_.FullName -Destination $destPath -Force
            }
        }
    }
}

# Create a requirements file for the package
Write-Host "Creating package requirements..." -ForegroundColor Yellow
pip freeze | Out-File -FilePath "$OutputDir\requirements.txt" -Encoding utf8

# Calculate package size
$packageSize = (Get-ChildItem -Recurse $OutputDir | Measure-Object -Property Length -Sum).Sum
$packageSizeMB = [math]::Round($packageSize / 1MB, 2)

Write-Host "Package created successfully!" -ForegroundColor Green
Write-Host "Output directory: $OutputDir" -ForegroundColor Cyan
Write-Host "Package size: $packageSizeMB MB" -ForegroundColor Cyan

# Check if package is too large for Lambda
if ($packageSizeMB -gt 250) {
    Write-Warning "Package size ($packageSizeMB MB) exceeds Lambda limit (250 MB). Consider using Lambda Layers."
} elseif ($packageSizeMB -gt 50) {
    Write-Warning "Package size ($packageSizeMB MB) is large. Consider optimizing dependencies."
}

# Deactivate virtual environment
deactivate

Write-Host "Packaging complete!" -ForegroundColor Green
Write-Host "You can now deploy this package using CDK or upload to Lambda directly." -ForegroundColor Cyan