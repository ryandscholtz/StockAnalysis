# Fix missing pages by deploying static versions
$BucketName = "stock-analysis-app-production"
$region = "eu-west-1"
$profile = "Cerebrum"

Write-Host "Fixing missing pages..." -ForegroundColor Cyan

Set-Location frontend

# Check what static pages were built
Write-Host "Checking built pages..." -ForegroundColor Yellow
if (Test-Path ".next/server/app") {
    Get-ChildItem ".next/server/app" -Recurse -Name "*.html" | ForEach-Object {
        Write-Host "Found: $_" -ForegroundColor Green
    }
}

# Deploy missing static pages
Write-Host "Deploying static pages..." -ForegroundColor Yellow

# Copy auth pages if they exist
if (Test-Path ".next/server/app/auth/signin.html") {
    aws s3 cp .next/server/app/auth/signin.html s3://$BucketName/auth/signin.html --profile $profile
}
if (Test-Path ".next/server/app/auth/signup.html") {
    aws s3 cp .next/server/app/auth/signup.html s3://$BucketName/auth/signup.html --profile $profile
}

# Copy docs page if it exists
if (Test-Path ".next/server/app/docs.html") {
    aws s3 cp .next/server/app/docs.html s3://$BucketName/docs.html --profile $profile
}

# Create simple fallback pages for missing routes
$authSigninHtml = @'
<!DOCTYPE html>
<html>
<head>
    <title>Sign In - Stock Analysis</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
        .container { max-width: 400px; margin: 0 auto; padding: 40px; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .button { background: #0070f3; color: white; padding: 12px 24px; border: none; border-radius: 6px; text-decoration: none; display: inline-block; margin: 10px; cursor: pointer; }
        .input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Sign In</h1>
        <p>Authentication coming soon!</p>
        <form>
            <input type="email" placeholder="Email" class="input" />
            <input type="password" placeholder="Password" class="input" />
            <button type="button" class="button" onclick="alert('Authentication system coming soon!')">Sign In</button>
        </form>
        <p><a href="/watchlist.html" class="button" style="background: #666;">Back to Watchlist</a></p>
    </div>
</body>
</html>
'@

$authSignupHtml = @'
<!DOCTYPE html>
<html>
<head>
    <title>Sign Up - Stock Analysis</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; text-align: center; }
        .container { max-width: 400px; margin: 0 auto; padding: 40px; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .button { background: #0070f3; color: white; padding: 12px 24px; border: none; border-radius: 6px; text-decoration: none; display: inline-block; margin: 10px; cursor: pointer; }
        .input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Sign Up</h1>
        <p>Create your account to access advanced features!</p>
        <form>
            <input type="text" placeholder="Full Name" class="input" />
            <input type="email" placeholder="Email" class="input" />
            <input type="password" placeholder="Password" class="input" />
            <button type="button" class="button" onclick="alert('Registration system coming soon!')">Sign Up</button>
        </form>
        <p><a href="/watchlist.html" class="button" style="background: #666;">Back to Watchlist</a></p>
    </div>
</body>
</html>
'@

$docsHtml = @'
<!DOCTYPE html>
<html>
<head>
    <title>Documentation - Stock Analysis</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .button { background: #0070f3; color: white; padding: 12px 24px; border: none; border-radius: 6px; text-decoration: none; display: inline-block; margin: 10px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        .api-endpoint { background: #f5f5f5; padding: 10px; border-radius: 4px; margin: 10px 0; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 Stock Analysis Platform Documentation</h1>
        
        <h2>🚀 Getting Started</h2>
        <p>Welcome to the Stock Analysis Platform! This tool provides comprehensive financial analysis for stocks with real-time data and advanced valuation models.</p>
        
        <h2>🔗 API Endpoints</h2>
        <div class="api-endpoint">GET /health - Check API status</div>
        <div class="api-endpoint">GET /api/version - Get API version info</div>
        <div class="api-endpoint">GET /api/manual-data/{ticker} - Get stock data</div>
        <div class="api-endpoint">POST /api/analyze/{ticker} - Run stock analysis</div>
        
        <h2>📊 Features</h2>
        <ul>
            <li><strong>Real-time Data:</strong> Live stock prices via MarketStack API</li>
            <li><strong>Financial Ratios:</strong> P/E, P/B, ROE, Debt-to-Equity analysis</li>
            <li><strong>Valuation Models:</strong> DCF, EPV, Asset-based valuations</li>
            <li><strong>Business Quality:</strong> ROE, ROA, profit margin assessment</li>
            <li><strong>Growth Analysis:</strong> Revenue and earnings growth tracking</li>
        </ul>
        
        <h2>🎯 Supported Stocks</h2>
        <p>The platform supports analysis for major stocks including AAPL, GOOGL, MSFT, TSLA, and many more via the MarketStack API integration.</p>
        
        <p><a href="/watchlist.html" class="button">Back to Watchlist</a></p>
    </div>
</body>
</html>
'@

# Create and upload fallback pages
$authSigninHtml | Out-File -FilePath "signin.html" -Encoding UTF8
$authSignupHtml | Out-File -FilePath "signup.html" -Encoding UTF8
$docsHtml | Out-File -FilePath "docs.html" -Encoding UTF8

# Create auth directory structure
aws s3 cp signin.html s3://$BucketName/auth/signin/index.html --profile $profile
aws s3 cp signup.html s3://$BucketName/auth/signup/index.html --profile $profile
aws s3 cp docs.html s3://$BucketName/docs/index.html --profile $profile

# Also create direct access versions
aws s3 cp signin.html s3://$BucketName/auth/signin.html --profile $profile
aws s3 cp signup.html s3://$BucketName/auth/signup.html --profile $profile
aws s3 cp docs.html s3://$BucketName/docs.html --profile $profile

# Clean up temp files
Remove-Item signin.html, signup.html, docs.html

Set-Location ..

Write-Host ""
Write-Host "Fixed missing pages!" -ForegroundColor Green
Write-Host "Auth pages and docs are now available" -ForegroundColor Cyan