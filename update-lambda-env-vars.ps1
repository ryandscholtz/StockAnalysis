#!/usr/bin/env pwsh

Write-Host "Updating Lambda Environment Variables for MarketStack API" -ForegroundColor Green

# Set AWS profile to Cerebrum
$env:AWS_PROFILE = "Cerebrum"
Write-Host "Using AWS Profile: Cerebrum" -ForegroundColor Cyan

$FunctionName = "stock-analysis-api-production"
$MarketStackApiKey = "b435b1cd06228185916b7b7afd790dc6"

Write-Host "Setting MarketStack API key environment variable..." -ForegroundColor Yellow

try {
    # Create a temporary JSON file for environment variables
    $envVarsJson = @{
        Variables = @{
            MARKETSTACK_API_KEY = $MarketStackApiKey
        }
    } | ConvertTo-Json -Depth 3

    $tempFile = "lambda-env-temp.json"
    $envVarsJson | Out-File -FilePath $tempFile -Encoding ASCII -NoNewline

    Write-Host "Environment variables JSON created in $tempFile" -ForegroundColor White
    Write-Host "Content: $envVarsJson" -ForegroundColor White

    # Update the Lambda function configuration using file
    aws lambda update-function-configuration `
        --function-name $FunctionName `
        --environment "file://$tempFile" `
        --profile Cerebrum `
        --region eu-west-1 `
        --output table

    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Lambda environment variables updated successfully!" -ForegroundColor Green
        
        # Clean up temp file
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
        
        # Wait for function to be ready
        Write-Host "Waiting for function to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        # Test the search endpoint to verify API integration
        Write-Host "Testing MarketStack API integration..." -ForegroundColor Yellow
        
        try {
            $testResponse = Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/search?q=AAPL" -Method GET -TimeoutSec 30
            
            Write-Host "Search test results:" -ForegroundColor Cyan
            Write-Host "Data source: $($testResponse.data_source)" -ForegroundColor White
            Write-Host "API integration: $($testResponse.api_integration)" -ForegroundColor White
            Write-Host "Results found: $($testResponse.total)" -ForegroundColor White
            
            if ($testResponse.data_source -eq "marketstack_api") {
                Write-Host "🎉 SUCCESS! MarketStack API is now active!" -ForegroundColor Green
                Write-Host "🌐 Search is using live API data with 170,000+ tickers" -ForegroundColor Green
            } else {
                Write-Host "⚠️  Still using local database. May need more time to propagate." -ForegroundColor Yellow
                Write-Host "💡 Try testing again in a few minutes." -ForegroundColor Yellow
            }
            
        } catch {
            Write-Host "Could not test search endpoint: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "💡 The environment variable was set, but testing failed. Try manual testing." -ForegroundColor Yellow
        }
        
    } else {
        Write-Host "❌ Failed to update Lambda environment variables!" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "Error updating Lambda configuration: $($_.Exception.Message)" -ForegroundColor Red
    # Clean up temp file
    Remove-Item "lambda-env-temp.json" -Force -ErrorAction SilentlyContinue
    exit 1
}

Write-Host "Environment variable update complete!" -ForegroundColor Green
Write-Host "MarketStack API key has been configured in Lambda function." -ForegroundColor Cyan
Write-Host "The search endpoint should now use live API data." -ForegroundColor Cyan