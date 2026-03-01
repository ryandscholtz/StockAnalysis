# Deploy Lambda with dependencies in a Layer (proper approach)
Write-Host "=== Deploying Lambda with Layers ===" -ForegroundColor Green

$functionName = "stock-analysis-api-production"
$layerName = "stock-analysis-dependencies"
$profile = "Cerebrum"
$region = "eu-west-1"
$s3Bucket = "stock-analysis-lambda-deployments"

# Step 1: Create dependencies layer
Write-Host ""
Write-Host "Step 1: Creating dependencies layer..." -ForegroundColor Cyan

# Create layer structure (dependencies must be in python/ subdirectory)
$layerDir = "lambda_layer"
$pythonDir = "$layerDir/python"

if (Test-Path $layerDir) {
    Remove-Item $layerDir -Recurse -Force
}
New-Item -ItemType Directory -Path $pythonDir -Force | Out-Null

Write-Host "Copying dependencies to layer structure..." -ForegroundColor Gray
# Copy all dependencies except our app code
Get-ChildItem lambda_build -Exclude "app","lambda_handler.py",".env" | ForEach-Object {
    Copy-Item $_.FullName "$pythonDir/" -Recurse -Force
    Write-Host "  Copied: $($_.Name)" -ForegroundColor Gray
}

Write-Host "Creating layer zip..." -ForegroundColor Gray
$layerZip = "lambda_layer.zip"
if (Test-Path $layerZip) {
    Remove-Item $layerZip -Force
}

# Create layer zip using Python
$pythonScript = @"
import zipfile
import os
from pathlib import Path

layer_dir = Path('$layerDir')
zip_file = Path('$layerZip')

print(f'Creating {zip_file}...')
with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(layer_dir):
        for file in files:
            file_path = Path(root) / file
            arcname = file_path.relative_to(layer_dir)
            zf.write(file_path, arcname)
            
size_mb = zip_file.stat().st_size / (1024 * 1024)
print(f'Layer created: {size_mb:.2f} MB')
"@

$pythonScript | python

$layerSize = (Get-Item $layerZip).Length / 1MB
Write-Host "Layer size: $([math]::Round($layerSize, 2)) MB" -ForegroundColor Cyan

# Upload layer to S3
Write-Host "Uploading layer to S3..." -ForegroundColor Cyan
aws s3 cp $layerZip "s3://$s3Bucket/$layerZip" --profile $profile --region $region

# Publish layer
Write-Host "Publishing Lambda layer..." -ForegroundColor Cyan
$layerOutput = aws lambda publish-layer-version `
    --layer-name $layerName `
    --description "Stock Analysis dependencies" `
    --content "S3Bucket=$s3Bucket,S3Key=$layerZip" `
    --compatible-runtimes python3.11 `
    --profile $profile `
    --region $region | ConvertFrom-Json

$layerArn = $layerOutput.LayerVersionArn
Write-Host "Layer published: $layerArn" -ForegroundColor Green

# Step 2: Create application code package (without dependencies)
Write-Host ""
Write-Host "Step 2: Creating application code package..." -ForegroundColor Cyan

$appDir = "lambda_app"
if (Test-Path $appDir) {
    Remove-Item $appDir -Recurse -Force
}
New-Item -ItemType Directory -Path $appDir -Force | Out-Null

# Copy only application code
Copy-Item "lambda_handler.py" "$appDir/" -Force
Copy-Item "app" "$appDir/" -Recurse -Force
if (Test-Path ".env") {
    Copy-Item ".env" "$appDir/" -Force
}

Write-Host "Creating application zip..." -ForegroundColor Gray
$appZip = "lambda_app.zip"
if (Test-Path $appZip) {
    Remove-Item $appZip -Force
}

# Create app zip using Python
$pythonScript = @"
import zipfile
import os
from pathlib import Path

app_dir = Path('$appDir')
zip_file = Path('$appZip')

print(f'Creating {zip_file}...')
with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(app_dir):
        for file in files:
            file_path = Path(root) / file
            arcname = file_path.relative_to(app_dir)
            zf.write(file_path, arcname)
            
size_mb = zip_file.stat().st_size / (1024 * 1024)
print(f'Application package created: {size_mb:.2f} MB')
"@

$pythonScript | python

$appSize = (Get-Item $appZip).Length / 1MB
Write-Host "Application size: $([math]::Round($appSize, 2)) MB" -ForegroundColor Cyan

# Upload app to S3
Write-Host "Uploading application to S3..." -ForegroundColor Cyan
aws s3 cp $appZip "s3://$s3Bucket/$appZip" --profile $profile --region $region

# Step 3: Update Lambda function
Write-Host ""
Write-Host "Step 3: Updating Lambda function..." -ForegroundColor Cyan

# Update function code
Write-Host "Updating function code..." -ForegroundColor Gray
aws lambda update-function-code `
    --function-name $functionName `
    --s3-bucket $s3Bucket `
    --s3-key $appZip `
    --profile $profile `
    --region $region | Out-Null

Write-Host "Waiting for function update..." -ForegroundColor Gray
Start-Sleep -Seconds 10

# Update function configuration to use layer
Write-Host "Attaching layer to function..." -ForegroundColor Gray
aws lambda update-function-configuration `
    --function-name $functionName `
    --layers $layerArn `
    --environment "Variables={MARKETSTACK_API_KEY=b435b1cd06228185916b7b7afd790dc6,ENVIRONMENT=production}" `
    --profile $profile `
    --region $region | Out-Null

Write-Host "Waiting for configuration update..." -ForegroundColor Gray
Start-Sleep -Seconds 10

# Step 4: Test the deployment
Write-Host ""
Write-Host "Step 4: Testing deployment..." -ForegroundColor Cyan

$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health"
Write-Host "Testing: $apiUrl" -ForegroundColor Gray

try {
    $response = Invoke-RestMethod -Uri $apiUrl -Method Get -TimeoutSec 30
    Write-Host ""
    Write-Host "[SUCCESS] Health check PASSED!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json) -ForegroundColor Cyan
} catch {
    Write-Host ""
    Write-Host "[FAILED] Health check FAILED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Checking Lambda logs..." -ForegroundColor Yellow
    
    # Get recent logs
    aws logs tail "/aws/lambda/$functionName" --since 5m --profile $profile --region $region
}

Write-Host ""
Write-Host "=== Deployment Complete ===" -ForegroundColor Green
Write-Host "Lambda function: $functionName" -ForegroundColor Cyan
Write-Host "Layer: $layerArn" -ForegroundColor Cyan
$apiBaseUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/"
Write-Host "API URL: $apiBaseUrl" -ForegroundColor Cyan
