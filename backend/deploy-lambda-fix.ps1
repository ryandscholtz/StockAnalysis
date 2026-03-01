# Fix Lambda deployment with proper pydantic dependencies
# This script builds dependencies for Lambda's Python 3.11 runtime

Write-Host "=== Fixing Lambda Deployment ===" -ForegroundColor Green

$functionName = "stock-analysis-api-production"
$profile = "Cerebrum"
$region = "eu-west-1"

# Create temporary build directory
$buildDir = "lambda_build"
if (Test-Path $buildDir) {
    Write-Host "Cleaning existing build directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $buildDir
}
New-Item -ItemType Directory -Path $buildDir | Out-Null

Write-Host "Installing dependencies for Lambda runtime..." -ForegroundColor Cyan

# Install dependencies using pip with target directory
# This ensures we get the right platform-specific wheels for Linux
pip install -r requirements-lambda.txt -t $buildDir --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.11 --implementation cp

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error installing dependencies" -ForegroundColor Red
    exit 1
}

Write-Host "Copying application code..." -ForegroundColor Cyan

# Copy application code
Copy-Item -Recurse -Path "app" -Destination "$buildDir\app"
Copy-Item -Path "lambda_handler.py" -Destination "$buildDir\lambda_handler.py"

# Copy environment file if exists
if (Test-Path ".env.production") {
    Copy-Item -Path ".env.production" -Destination "$buildDir\.env"
}

Write-Host "Creating deployment package..." -ForegroundColor Cyan

# Create zip file
$zipFile = "lambda_deployment_fixed.zip"
if (Test-Path $zipFile) {
    Remove-Item $zipFile
}

# Change to build directory and create zip
Push-Location $buildDir
Compress-Archive -Path * -DestinationPath "..\$zipFile" -CompressionLevel Optimal
Pop-Location

# Get file size
$fileSize = (Get-Item $zipFile).Length / 1MB
Write-Host "Package size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan

if ($fileSize -gt 50) {
    Write-Host "Warning: Package is large. Deployment may take longer." -ForegroundColor Yellow
}

Write-Host "Deploying to Lambda..." -ForegroundColor Cyan

# Update Lambda function code
aws lambda update-function-code `
    --function-name $functionName `
    --zip-file "fileb://$zipFile" `
    --profile $profile `
    --region $region

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error deploying to Lambda" -ForegroundColor Red
    exit 1
}

Write-Host "Waiting for Lambda to update..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# Update environment variables to ensure they're set
Write-Host "Updating environment variables..." -ForegroundColor Cyan
aws lambda update-function-configuration `
    --function-name $functionName `
    --environment "Variables={MARKETSTACK_API_KEY=b435b1cd06228185916b7b7afd790dc6,ENVIRONMENT=production}" `
    --profile $profile `
    --region $region

Write-Host "Waiting for configuration update..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "=== Testing Lambda ===" -ForegroundColor Green

# Test the health endpoint
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health"
Write-Host "Testing: $apiUrl" -ForegroundColor Cyan

try {
    $response = Invoke-RestMethod -Uri $apiUrl -Method Get -TimeoutSec 30
    Write-Host "Health check passed!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json) -ForegroundColor Cyan
} catch {
    Write-Host "Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Checking Lambda logs..." -ForegroundColor Yellow
    
    # Get recent logs
    aws logs tail "/aws/lambda/$functionName" --since 5m --profile $profile --region $region
}

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host "Lambda function: $functionName" -ForegroundColor Cyan
Write-Host "API URL: https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/" -ForegroundColor Cyan

# Cleanup
Write-Host ""
Write-Host "Cleaning up build directory..." -ForegroundColor Yellow
Remove-Item -Recurse -Force $buildDir
