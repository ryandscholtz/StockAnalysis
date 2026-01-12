# Test script for verifying frontend deployment

param(
    [Parameter(Mandatory=$false)]
    [string]$WebsiteUrl = "http://stock-analysis-frontend-production.s3-website-eu-west-1.amazonaws.com",
    
    [Parameter(Mandatory=$false)]
    [string]$ApiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"
)

$ErrorActionPreference = "Stop"

Write-Host "🧪 Testing Frontend Deployment..." -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

Write-Host "🌐 Website URL: $WebsiteUrl" -ForegroundColor Yellow
Write-Host "🔗 API URL: $ApiUrl" -ForegroundColor Yellow

# Test 1: Website accessibility
Write-Host ""
Write-Host "Test 1: Website Accessibility" -ForegroundColor Yellow
Write-Host "-----------------------------" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri $WebsiteUrl -TimeoutSec 15
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Website is accessible (Status: $($response.StatusCode))" -ForegroundColor Green
        
        # Check if it contains expected content
        if ($response.Content -match "Stock Analysis" -or $response.Content -match "watchlist") {
            Write-Host "✅ Website contains expected content" -ForegroundColor Green
        } else {
            Write-Host "⚠️ Website accessible but content might be incorrect" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "❌ Website not accessible: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: API connectivity
Write-Host ""
Write-Host "Test 2: API Connectivity" -ForegroundColor Yellow
Write-Host "------------------------" -ForegroundColor Yellow
try {
    $healthResponse = Invoke-RestMethod -Uri "$ApiUrl/health" -Method GET -TimeoutSec 10
    Write-Host "✅ API health check passed" -ForegroundColor Green
    
    # Test version endpoint
    try {
        $versionResponse = Invoke-RestMethod -Uri "$ApiUrl/api/version" -Method GET -TimeoutSec 10
        Write-Host "✅ API version: $($versionResponse.version)" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Version endpoint not accessible" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "❌ API not accessible: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: CORS configuration
Write-Host ""
Write-Host "Test 3: CORS Configuration" -ForegroundColor Yellow
Write-Host "--------------------------" -ForegroundColor Yellow
try {
    $corsHeaders = @{
        'Origin' = $WebsiteUrl
        'Access-Control-Request-Method' = 'GET'
    }
    $corsResponse = Invoke-WebRequest -Uri "$ApiUrl/api/version" -Method OPTIONS -Headers $corsHeaders -TimeoutSec 10
    
    $accessControlHeaders = $corsResponse.Headers['Access-Control-Allow-Origin']
    if ($accessControlHeaders -contains '*' -or $accessControlHeaders -contains $WebsiteUrl) {
        Write-Host "✅ CORS properly configured" -ForegroundColor Green
    } else {
        Write-Host "⚠️ CORS might need adjustment" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️ Could not test CORS configuration" -ForegroundColor Yellow
}

# Test 4: Sample API endpoint
Write-Host ""
Write-Host "Test 4: Sample API Endpoint" -ForegroundColor Yellow
Write-Host "---------------------------" -ForegroundColor Yellow
try {
    $sampleResponse = Invoke-RestMethod -Uri "$ApiUrl/api/manual-data/AAPL" -Method GET -TimeoutSec 15
    if ($sampleResponse) {
        Write-Host "✅ Sample API endpoint working" -ForegroundColor Green
        if ($sampleResponse.ticker -eq "AAPL") {
            Write-Host "✅ API returning expected data structure" -ForegroundColor Green
        }
    }
} catch {
    Write-Host "⚠️ Sample API endpoint test failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "📋 Test Summary" -ForegroundColor Cyan
Write-Host "===============" -ForegroundColor Cyan
Write-Host "Frontend URL: $WebsiteUrl" -ForegroundColor White
Write-Host "Backend API: $ApiUrl" -ForegroundColor White

Write-Host ""
Write-Host "🎯 Manual Testing Steps:" -ForegroundColor Yellow
Write-Host "1. Open $WebsiteUrl in your browser" -ForegroundColor White
Write-Host "2. Navigate to the watchlist page" -ForegroundColor White
Write-Host "3. Click on a stock (AAPL, GOOGL, MSFT, TSLA)" -ForegroundColor White
Write-Host "4. Verify the stock details page loads correctly" -ForegroundColor White
Write-Host "5. Test 'Run Analysis' functionality" -ForegroundColor White
Write-Host "6. Check that financial data displays properly" -ForegroundColor White

Write-Host ""
Write-Host "🔧 If issues occur:" -ForegroundColor Yellow
Write-Host "- Check browser console for JavaScript errors" -ForegroundColor White
Write-Host "- Verify API endpoints are accessible" -ForegroundColor White
Write-Host "- Check CORS configuration if API calls fail" -ForegroundColor White
Write-Host "- Ensure environment variables are set correctly" -ForegroundColor White