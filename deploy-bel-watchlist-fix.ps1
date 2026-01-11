#!/usr/bin/env pwsh

Write-Host "Adding BEL.XJSE to Default Watchlist" -ForegroundColor Green

# Set AWS profile to Cerebrum
$env:AWS_PROFILE = "Cerebrum"
Write-Host "Using AWS Profile: Cerebrum" -ForegroundColor Cyan

Write-Host "Creating Lambda deployment package..." -ForegroundColor Yellow

# Remove old deployment files
if (Test-Path "lambda-bel-fix.zip") {
    Remove-Item "lambda-bel-fix.zip" -Force
}

# Create deployment package with the updated Lambda function
Write-Host "Packaging updated simple_marketstack_lambda.py..." -ForegroundColor White
Compress-Archive -Path "simple_marketstack_lambda.py" -DestinationPath "lambda-bel-fix.zip" -Force

# Update Lambda function
Write-Host "Updating Lambda function..." -ForegroundColor Green

$FunctionName = "stock-analysis-api-production"
$ZipFile = "lambda-bel-fix.zip"

try {
    Write-Host "Uploading updated code to Lambda..." -ForegroundColor Yellow
    aws lambda update-function-code --function-name $FunctionName --zip-file "fileb://$ZipFile" --profile Cerebrum --region eu-west-1 --output table
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Lambda function updated successfully!" -ForegroundColor Green
        
        # Wait for function to be ready
        Write-Host "Waiting for function to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        # Test the main watchlist endpoint
        Write-Host "Testing main watchlist endpoint..." -ForegroundColor Yellow
        
        try {
            $watchlistResponse = Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/watchlist" -Method GET -TimeoutSec 30
            Write-Host "Watchlist endpoint working!" -ForegroundColor Green
            Write-Host "Total items: $($watchlistResponse.items.Count)" -ForegroundColor Cyan
            
            # Check if BEL.XJSE is in the list
            $belItem = $watchlistResponse.items | Where-Object { $_.ticker -eq "BEL.XJSE" }
            if ($belItem) {
                Write-Host "BEL.XJSE found in main watchlist!" -ForegroundColor Green
                Write-Host "Company Name: $($belItem.company_name)" -ForegroundColor Cyan
                Write-Host "Current Price: $($belItem.current_price)" -ForegroundColor Cyan
            } else {
                Write-Host "BEL.XJSE not found in main watchlist" -ForegroundColor Red
                Write-Host "Available tickers: $($watchlistResponse.items.ticker -join ', ')" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "Watchlist test failed: $($_.Exception.Message)" -ForegroundColor Red
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
Remove-Item "lambda-bel-fix.zip" -Force -ErrorAction SilentlyContinue

Write-Host "BEL.XJSE added to default watchlist!" -ForegroundColor Green
Write-Host "The frontend should now show Bell Equipment in the main watchlist view." -ForegroundColor Cyan