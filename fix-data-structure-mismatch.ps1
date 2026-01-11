#!/usr/bin/env pwsh

Write-Host "Fixing Data Structure Mismatch - Ticker (Ticker) Issue" -ForegroundColor Green

# Set AWS profile to Cerebrum
$env:AWS_PROFILE = "Cerebrum"
Write-Host "Using AWS Profile: Cerebrum" -ForegroundColor Cyan

Write-Host "Creating Lambda deployment package..." -ForegroundColor Yellow

# Remove old deployment files
if (Test-Path "lambda-structure-fix.zip") {
    Remove-Item "lambda-structure-fix.zip" -Force
}

# Create deployment package with the updated Lambda function
Write-Host "Packaging updated simple_marketstack_lambda.py..." -ForegroundColor White
Compress-Archive -Path "simple_marketstack_lambda.py" -DestinationPath "lambda-structure-fix.zip" -Force

# Update Lambda function
Write-Host "Updating Lambda function..." -ForegroundColor Green

$FunctionName = "stock-analysis-api-production"
$ZipFile = "lambda-structure-fix.zip"

try {
    Write-Host "Uploading fixed code to Lambda..." -ForegroundColor Yellow
    aws lambda update-function-code --function-name $FunctionName --zip-file "fileb://$ZipFile" --profile Cerebrum --region eu-west-1 --output table
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Lambda function updated successfully!" -ForegroundColor Green
        
        # Wait for function to be ready
        Write-Host "Waiting for function to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        # Test the individual watchlist item endpoint
        Write-Host "Testing individual watchlist item endpoint..." -ForegroundColor Yellow
        
        try {
            $itemResponse = Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/watchlist/BEL.XJSE" -Method GET -TimeoutSec 30
            Write-Host "Individual item endpoint working!" -ForegroundColor Green
            
            # Check the data structure
            if ($itemResponse.watchlist_item) {
                Write-Host "Data structure is correct!" -ForegroundColor Green
                Write-Host "Company Name: $($itemResponse.watchlist_item.company_name)" -ForegroundColor Cyan
                Write-Host "Ticker: $($itemResponse.watchlist_item.ticker)" -ForegroundColor Cyan
                Write-Host "Has watchlist_item wrapper: YES" -ForegroundColor Green
            } else {
                Write-Host "Data structure issue - no watchlist_item wrapper" -ForegroundColor Red
                Write-Host "Response structure: $($itemResponse | ConvertTo-Json -Compress)" -ForegroundColor Yellow
            }
            
            # Test MSFT as well
            Write-Host "Testing MSFT for comparison..." -ForegroundColor Yellow
            $msftResponse = Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/watchlist/MSFT" -Method GET -TimeoutSec 30
            
            if ($msftResponse.watchlist_item) {
                Write-Host "MSFT structure is also correct!" -ForegroundColor Green
                Write-Host "MSFT Company Name: $($msftResponse.watchlist_item.company_name)" -ForegroundColor Cyan
            }
            
        } catch {
            Write-Host "Test failed: $($_.Exception.Message)" -ForegroundColor Red
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
Remove-Item "lambda-structure-fix.zip" -Force -ErrorAction SilentlyContinue

Write-Host "Data structure mismatch fixed!" -ForegroundColor Green
Write-Host "The frontend should now show Company Name (Ticker) instead of Ticker (Ticker)." -ForegroundColor Cyan