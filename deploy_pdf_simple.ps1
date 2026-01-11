Write-Host "Deploying PDF Upload with Dependencies..." -ForegroundColor Green

# Create deployment package with dependencies
Write-Host "Creating deployment package with dependencies..." -ForegroundColor Yellow

# Create temp directory
$tempDir = "temp_deploy_pdf_deps"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Copy Lambda handler and AI processor
Copy-Item "backend/simple_lambda_handler_fixed.py" "$tempDir/lambda_function.py"
Copy-Item "backend/ai_pdf_processor.py" "$tempDir/"

# Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
Set-Location $tempDir

# Install dependencies to current directory
pip install PyMuPDF==1.23.26 Pillow==10.0.1 -t .

# Go back to root
Set-Location ..

# Create zip file
$zipFile = "lambda_pdf_with_deps.zip"
if (Test-Path $zipFile) {
    Remove-Item $zipFile
}

# Create zip using PowerShell
Write-Host "Creating deployment package..." -ForegroundColor Yellow
Compress-Archive -Path "$tempDir/*" -DestinationPath $zipFile

Write-Host "Uploading to AWS Lambda..." -ForegroundColor Yellow

# Update Lambda function
aws lambda update-function-code --function-name stock-analysis-api-production --zip-file "fileb://$zipFile"

if ($LASTEXITCODE -eq 0) {
    Write-Host "PDF Upload with dependencies deployed successfully!" -ForegroundColor Green
    
    # Update timeout to handle image processing
    Write-Host "Updating Lambda timeout for image processing..." -ForegroundColor Yellow
    aws lambda update-function-configuration --function-name stock-analysis-api-production --timeout 900
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Lambda timeout updated to 15 minutes" -ForegroundColor Green
    }
} else {
    Write-Host "Deployment failed!" -ForegroundColor Red
    exit 1
}

# Cleanup
Remove-Item -Recurse -Force $tempDir
Remove-Item $zipFile

Write-Host "Cleanup completed" -ForegroundColor Blue
Write-Host "PDF Upload with PDF-to-image fallback is now ready!" -ForegroundColor Green