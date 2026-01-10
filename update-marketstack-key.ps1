# Script to update MarketStack API key in AWS Secrets Manager
# Replace YOUR-REAL-API-KEY with your actual MarketStack API key

$apiKey = Read-Host "Enter your MarketStack API key"

if ($apiKey -and $apiKey -ne "") {
    Write-Host "🔑 Updating MarketStack API key in AWS Secrets Manager..." -ForegroundColor Yellow
    
    $secretValue = @{
        external_api_keys = @{
            marketstack = $apiKey
        }
        jwt_secret = "cI6<H`giT~[N6Ej:]dw+Tr$|nKV?R(qQ"
        encryption_key = ""
    } | ConvertTo-Json -Compress
    
    aws secretsmanager update-secret --secret-id "stock-analysis-secrets-production" --secret-string $secretValue
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ API key updated successfully!" -ForegroundColor Green
        Write-Host "🔄 Testing the API with real data..." -ForegroundColor Yellow
        
        # Wait a moment for the update to propagate
        Start-Sleep -Seconds 3
        
        # Test the API
        Write-Host "📊 Testing live prices endpoint..." -ForegroundColor White
        curl "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/watchlist/live-prices"
        
        Write-Host "`n🎉 Setup complete! Your frontend should now show real stock prices when you refresh." -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to update API key" -ForegroundColor Red
    }
} else {
    Write-Host "❌ No API key provided" -ForegroundColor Red
}