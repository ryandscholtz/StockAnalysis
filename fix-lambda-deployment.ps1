#!/usr/bin/env pwsh

Write-Host "Fixing Lambda Deployment - Bell Equipment Company Name Issue" -ForegroundColor Green

# Set AWS profile to Cerebrum
$env:AWS_PROFILE = "Cerebrum"
Write-Host "Using AWS Profile: Cerebrum" -ForegroundColor Cyan

Write-Host "Creating Lambda deployment package..." -ForegroundColor Yellow

# Remove old deployment files
if (Test-Path "lambda-fix.zip") {
    Remove-Item "lambda-fix.zip" -Force
}

# Create deployment package with just the Lambda function
Write-Host "Packaging simple_marketstack_lambda.py..." -ForegroundColor White
Compress-Archive -Path "simple_marketstack_lambda.py" -DestinationPath "lambda-fix.zip" -Force

# Update Lambda function
Write-Host "Updating Lambda function..." -ForegroundColor Green

$FunctionName = "stock-analysis-api-production"
$ZipFile = "lambda-fix.zip"

try {
    Write-Host "Uploading fixed code to Lambda..." -ForegroundColor Yellow
    aws lambda update-function-code --function-name $FunctionName --zip-file "fileb://$ZipFile" --profile Cerebrum --region eu-west-1 --output table
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Lambda function updated successfully!" -ForegroundColor Green
        
        # Wait for function to be ready
        Write-Host "Waiting for function to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        # Test the health endpoint
        Write-Host "Testing health endpoint..." -ForegroundColor Yellow
        
        try {
            $healthResponse = Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health" -Method GET -TimeoutSec 30
            Write-Host "Health check successful!" -ForegroundColor Green
            Write-Host "Response: $($healthResponse | ConvertTo-Json -Compress)" -ForegroundColor Cyan
        } catch {
            Write-Host "Health check failed: $($_.Exception.Message)" -ForegroundColor Red
        }
        
        # Test BEL.XJSE analysis
        Write-Host "Testing BEL.XJSE analysis..." -ForegroundColor Yellow
        
        try {
            $analysisResponse = Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/analyze/BEL.XJSE" -Method GET -TimeoutSec 30
            Write-Host "BEL.XJSE analysis successful!" -ForegroundColor Green
            Write-Host "Company Name: $($analysisResponse.companyName)" -ForegroundColor Cyan
            Write-Host "Current Price: $($analysisResponse.currentPrice)" -ForegroundColor Cyan
        } catch {
            Write-Host "BEL.XJSE analysis failed: $($_.Exception.Message)" -ForegroundColor Red
        }
        
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
Remove-Item "lambda-fix.zip" -Force -ErrorAction SilentlyContinue

Write-Host "Lambda deployment fix complete!" -ForegroundColor Green
Write-Host "The Lambda should now be able to import simple_marketstack_lambda correctly." -ForegroundColor Cyan