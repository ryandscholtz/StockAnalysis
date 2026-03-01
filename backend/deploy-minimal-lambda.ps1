# Deploy minimal Lambda package (without heavy PDF/data science libraries)
Write-Host "=== Creating Minimal Lambda Package ===" -ForegroundColor Green

$functionName = "stock-analysis-api-production"
$profile = "Cerebrum"
$region = "eu-west-1"
$s3Bucket = "stock-analysis-lambda-deployments"

# Clean up old builds
$buildDir = "lambda_minimal"
if (Test-Path $buildDir) {
    Remove-Item $buildDir -Recurse -Force
}
New-Item -ItemType Directory -Path $buildDir -Force | Out-Null

# Install minimal dependencies
Write-Host "Installing minimal dependencies..." -ForegroundColor Cyan
pip install `
    fastapi==0.104.1 `
    pydantic==2.5.0 `
    mangum==0.17.0 `
    boto3==1.34.0 `
    python-dotenv==1.0.0 `
    requests==2.32.5 `
    httpx==0.25.2 `
    beautifulsoup4==4.12.2 `
    python-multipart==0.0.6 `
    PyJWT==2.8.0 `
    passlib==1.7.4 `
    aws-xray-sdk==2.12.0 `
    sqlalchemy==2.0.23 `
    yfinance==0.2.28 `
    pandas==2.1.3 `
    numpy==1.26.2 `
    PyPDF2==3.0.1 `
    pdfplumber==0.10.3 `
    -t $buildDir `
    --platform manylinux2014_x86_64 `
    --only-binary=:all: `
    --python-version 3.11 `
    --implementation cp `
    --upgrade

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error installing dependencies" -ForegroundColor Red
    exit 1
}

# Copy application code
Write-Host "Copying application code..." -ForegroundColor Cyan
Copy-Item "lambda_handler.py" "$buildDir/" -Force
Copy-Item "app" "$buildDir/" -Recurse -Force
if (Test-Path ".env") {
    Copy-Item ".env" "$buildDir/" -Force
}

# Create zip
Write-Host "Creating deployment package..." -ForegroundColor Cyan
$zipFile = "lambda_minimal.zip"
if (Test-Path $zipFile) {
    Remove-Item $zipFile -Force
}

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

$fileSize = (Get-Item $zipFile).Length / 1MB
Write-Host "Package size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan

# Upload to S3
Write-Host "Uploading to S3..." -ForegroundColor Cyan
aws s3 cp $zipFile "s3://$s3Bucket/$zipFile" --profile $profile --region $region

# Update Lambda
Write-Host "Updating Lambda function..." -ForegroundColor Cyan
aws lambda update-function-code `
    --function-name $functionName `
    --s3-bucket $s3Bucket `
    --s3-key $zipFile `
    --profile $profile `
    --region $region | Out-Null

Write-Host "Waiting for update..." -ForegroundColor Gray
Start-Sleep -Seconds 15

# Update environment variables
Write-Host "Updating environment variables..." -ForegroundColor Cyan
aws lambda update-function-configuration `
    --function-name $functionName `
    --environment "Variables={MARKETSTACK_API_KEY=b435b1cd06228185916b7b7afd790dc6,ENVIRONMENT=production}" `
    --layers "" `
    --profile $profile `
    --region $region | Out-Null

Write-Host "Waiting for configuration update..." -ForegroundColor Gray
Start-Sleep -Seconds 10

# Test
Write-Host ""
Write-Host "Testing deployment..." -ForegroundColor Cyan
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health"

try {
    $response = Invoke-RestMethod -Uri $apiUrl -Method Get -TimeoutSec 30
    Write-Host ""
    Write-Host "[SUCCESS] Health check PASSED!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json) -ForegroundColor Cyan
} catch {
    Write-Host ""
    Write-Host "[FAILED] Health check failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Checking logs..." -ForegroundColor Yellow
    aws logs tail "/aws/lambda/$functionName" --since 2m --profile $profile --region $region
}

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
