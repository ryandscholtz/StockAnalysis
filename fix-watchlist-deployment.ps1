#!/usr/bin/env pwsh

Write-Host "Quick Fix: Redeploying Lambda with Watchlist Endpoint" -ForegroundColor Green

# Check AWS CLI
try {
    $awsIdentity = aws sts get-caller-identity --output json | ConvertFrom-Json
    Write-Host "AWS CLI configured for: $($awsIdentity.Arn)" -ForegroundColor Green
} catch {
    Write-Host "AWS CLI not configured. Run 'aws configure' first." -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "backend")) {
    Write-Host "Please run this script from the project root directory" -ForegroundColor Red
    exit 1
}

Write-Host "Creating Lambda deployment package..." -ForegroundColor Yellow

# Navigate to backend
Set-Location backend

# Check if requirements.txt exists
if (-not (Test-Path "requirements.txt")) {
    Write-Host "requirements.txt not found in backend directory" -ForegroundColor Red
    Set-Location ..
    exit 1
}

# Create deployment package
Write-Host "Creating zip file..." -ForegroundColor White

# Remove old dist files
if (Test-Path "dist.zip") {
    Remove-Item "dist.zip" -Force
}
if (Test-Path "dist") {
    Remove-Item "dist" -Recurse -Force
}

# Create dist directory
New-Item -ItemType Directory -Path "dist" -Force | Out-Null

# Copy application files
Write-Host "Copying application files..." -ForegroundColor White
Copy-Item -Path "app" -Destination "dist/app" -Recurse -Force
Copy-Item -Path "lambda_handler.py" -Destination "dist/" -Force
Copy-Item -Path "requirements.txt" -Destination "dist/" -Force

# Install dependencies in dist directory
Write-Host "Installing Python dependencies..." -ForegroundColor White
Set-Location dist
pip install -r requirements.txt -t . --quiet

# Create zip file
Write-Host "Creating deployment zip..." -ForegroundColor White
Compress-Archive -Path * -DestinationPath ../dist.zip -Force

Set-Location ..

# Update Lambda function
Write-Host "Updating Lambda function..." -ForegroundColor Green

$FunctionName = "stock-analysis-api-production"
$ZipFile = "dist.zip"

try {
    $result = aws lambda update-function-code --function-name $FunctionName --zip-file "fileb://$ZipFile" --output json | ConvertFrom-Json
    
    if ($result.FunctionName) {
        Write-Host "Lambda function updated successfully!" -ForegroundColor Green
        Write-Host "Function: $($result.FunctionName)" -ForegroundColor Cyan
        Write-Host "Version: $($result.Version)" -ForegroundColor Cyan
        
        # Wait for function to be ready
        Write-Host "Waiting for function to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        Write-Host "Watchlist endpoint fix deployment complete!" -ForegroundColor Green
        Write-Host "The /api/watchlist endpoint should now be available." -ForegroundColor Cyan
        
    } else {
        Write-Host "Lambda update failed!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Error updating Lambda function: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Cleanup
Write-Host "Cleaning up..." -ForegroundColor White
Remove-Item "dist" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "dist.zip" -Force -ErrorAction SilentlyContinue

Set-Location ..