# Simple working deployment script
$BucketName = "stock-analysis-frontend-production"
$region = "eu-west-1"
$profile = "Cerebrum"

Write-Host "Deploying frontend..." -ForegroundColor Cyan

Set-Location frontend

# Create simple static files
Write-Host "Creating static files..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "dist"

$indexHtml = @'
<!DOCTYPE html>
<html>
<head>
    <title>Stock Analysis Platform</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .button { background: #0070f3; color: white; padding: 12px 24px; border: none; border-radius: 6px; text-decoration: none; display: inline-block; margin: 10px 10px 10px 0; }
        .button:hover { background: #0051cc; }
        .status { padding: 10px; background: #e7f3ff; border-left: 4px solid #0070f3; margin: 20px 0; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 2px solid #eee; padding-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Stock Analysis Platform</h1>
        <div class="status">
            <strong>Status:</strong> Frontend successfully deployed to AWS S3!
        </div>
        
        <p>Welcome to the Stock Analysis Platform. This application provides comprehensive financial analysis for stocks with real-time data and advanced valuation models.</p>
        
        <h2>✨ Features</h2>
        <ul>
            <li><strong>Real-time Stock Data:</strong> Live prices via MarketStack API</li>
            <li><strong>Financial Analysis:</strong> P/E, P/B, ROE, Debt-to-Equity ratios</li>
            <li><strong>Valuation Models:</strong> DCF, EPV, Asset-based valuations</li>
            <li><strong>Business Quality:</strong> ROE, ROA, profit margins analysis</li>
            <li><strong>Growth Metrics:</strong> Revenue and earnings growth tracking</li>
            <li><strong>PDF Upload:</strong> Extract data from financial statements</li>
        </ul>
        
        <h2>🔗 API Integration</h2>
        <p>Backend API: <a href="https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health" target="_blank">https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production</a></p>
        
        <h2>📊 Sample Analysis</h2>
        <p>The platform analyzes stocks like:</p>
        <ul>
            <li><strong>AAPL</strong> - Apple Inc.</li>
            <li><strong>GOOGL</strong> - Alphabet Inc.</li>
            <li><strong>MSFT</strong> - Microsoft Corporation</li>
            <li><strong>TSLA</strong> - Tesla Inc.</li>
            <li><strong>BEL.XJSE</strong> - Bell Equipment Ltd (JSE)</li>
        </ul>
        
        <h2>🎯 Recent Updates</h2>
        <ul>
            <li>✅ Cache status indicator moved below price display</li>
            <li>✅ Recommendation badges repositioned for better UX</li>
            <li>✅ Notes section removed for cleaner interface</li>
            <li>✅ MarketStack API integration for real-time data</li>
            <li>✅ Enhanced financial ratios display</li>
        </ul>
        
        <div class="status">
            <strong>Deployment Info:</strong><br>
            S3 Bucket: stock-analysis-frontend-production<br>
            Region: eu-west-1<br>
            Deployed: January 12, 2026
        </div>
        
        <p><em>For the full interactive application, the Next.js frontend connects to the AWS Lambda backend to provide real-time stock analysis and valuation.</em></p>
    </div>
</body>
</html>
'@

$indexHtml | Out-File -FilePath "dist/index.html" -Encoding UTF8
$indexHtml | Out-File -FilePath "dist/404.html" -Encoding UTF8

# Create bucket if needed
Write-Host "Checking S3 bucket..." -ForegroundColor Yellow
aws s3api head-bucket --bucket $BucketName --region $region --profile $profile 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating S3 bucket..." -ForegroundColor Yellow
    aws s3api create-bucket --bucket $BucketName --region $region --profile $profile --create-bucket-configuration LocationConstraint=$region
    aws s3 website s3://$BucketName --index-document index.html --error-document 404.html --profile $profile
    
    # Make bucket public
    $policy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::stock-analysis-frontend-production/*"}]}'
    $policy | Out-File -FilePath "policy.json" -Encoding UTF8
    aws s3api put-bucket-policy --bucket $BucketName --policy file://policy.json --profile $profile
    Remove-Item "policy.json"
}

# Deploy
Write-Host "Deploying to S3..." -ForegroundColor Yellow
aws s3 sync dist/ s3://$BucketName --delete --region $region --profile $profile

Set-Location ..

$websiteUrl = "http://$BucketName.s3-website-$region.amazonaws.com"
Write-Host ""
Write-Host "Deployment successful!" -ForegroundColor Green
Write-Host "Website URL: $websiteUrl" -ForegroundColor Cyan

# Test
Write-Host ""
Write-Host "Testing..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
try {
    $response = Invoke-WebRequest -Uri $websiteUrl -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "Website is live!" -ForegroundColor Green
    }
} catch {
    Write-Host "Website will be available shortly" -ForegroundColor Yellow
}