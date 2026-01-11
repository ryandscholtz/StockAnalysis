Write-Host "🚀 Deploying PDF Upload Fix..." -ForegroundColor Green

# Create deployment package
Write-Host "📦 Creating deployment package..." -ForegroundColor Yellow

# Create temp directory
$tempDir = "temp_deploy_pdf_fix"
if (Test-Path $tempDir) {
    Remove-Item -Recurse -Force $tempDir
}
New-Item -ItemType Directory -Path $tempDir | Out-Null

# Copy Lambda handler and AI processor
Copy-Item "backend/simple_lambda_handler_fixed.py" "$tempDir/lambda_function.py"
Copy-Item "backend/ai_pdf_processor.py" "$tempDir/"

# Create zip file
$zipFile = "lambda_pdf_fix.zip"
if (Test-Path $zipFile) {
    Remove-Item $zipFile
}

# Create zip using PowerShell
Compress-Archive -Path "$tempDir/*" -DestinationPath $zipFile

Write-Host "📤 Uploading to AWS Lambda..." -ForegroundColor Yellow

# Update Lambda function
aws lambda update-function-code --function-name stock-analysis-production --zip-file "fileb://$zipFile"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ PDF Upload Fix deployed successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Deployment failed!" -ForegroundColor Red
    exit 1
}

# Cleanup
Remove-Item -Recurse -Force $tempDir
Remove-Item $zipFile

Write-Host "🧹 Cleanup completed" -ForegroundColor Blue
Write-Host "🎉 PDF Upload functionality should now work with AI extraction!" -ForegroundColor Green