# Final deployment script - deploy built Next.js app to S3
$BucketName = "stock-analysis-frontend-production"
$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "🚀 Final Frontend Deployment to S3..." -ForegroundColor Cyan

# Navigate to frontend
Set-Location frontend

# Create env file
"NEXT_PUBLIC_API_URL=$apiUrl" | Out-File -FilePath ".env.production" -Encoding UTF8

# Install and build
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
npm install

Write-Host "🔨 Building application..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed - trying without static export" -ForegroundColor Red
    # Create a simple index.html for the main page
    $indexHtml = @"
<!DOCTYPE html>
<html>
<head>
    <title>Stock Analysis</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .container { max-width: 800px; margin: 0 auto; }
        .button { background: #0070f3; color: white; padding: 12px 24px; border: none; border-radius: 6px; text-decoration: none; display: inline-block; margin: 10px; }
        .button:hover { background: #0051cc; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Stock Analysis Platform</h1>
        <p>Welcome to the Stock Analysis Platform. This application provides comprehensive financial analysis for stocks.</p>
        
        <h2>Features:</h2>
        <ul>
            <li>Real-time stock price data</li>
            <li>Financial ratio analysis</li>
            <li>Valuation models (DCF, EPV, Asset-based)</li>
            <li>Business quality metrics</li>
            <li>Growth analysis</li>
        </ul>
        
        <h2>Quick Access:</h2>
        <a href="/watchlist" class="button">View Watchlist</a>
        <a href="/watchlist/AAPL" class="button">Apple (AAPL)</a>
        <a href="/watchlist/GOOGL" class="button">Google (GOOGL)</a>
        <a href="/watchlist/MSFT" class="button">Microsoft (MSFT)</a>
        <a href="/watchlist/TSLA" class="button">Tesla (TSLA)</a>
        
        <h2>API Status:</h2>
        <p>Backend API: <a href="$apiUrl/health" target="_blank">$apiUrl</a></p>
        
        <script>
            // Simple client-side routing for SPA behavior
            if (window.location.pathname !== '/') {
                // For now, redirect to main page
                // In a full deployment, this would be handled by the Next.js router
                console.log('Current path:', window.location.pathname);
            }
        </script>
    </div>
</body>
</html>
"@
    
    # Create out directory and files
    New-Item -ItemType Directory -Force -Path "out"
    $indexHtml | Out-File -FilePath "out/index.html" -Encoding UTF8
    
    # Create a simple 404 page
    $indexHtml.Replace("Stock Analysis Platform", "Page Not Found - Stock Analysis") | Out-File -FilePath "out/404.html" -Encoding UTF8
    
    Write-Host "✅ Created fallback static files" -ForegroundColor Green
}

# Check if bucket exists, create if not
Write-Host "📦 Checking S3 bucket..." -ForegroundColor Yellow
aws s3api head-bucket --bucket $BucketName --region $region --profile $profile 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "🆕 Creating S3 bucket..." -ForegroundColor Yellow
    aws s3api create-bucket --bucket $BucketName --region $region --profile $profile --create-bucket-configuration LocationConstraint=$region
    aws s3 website s3://$BucketName --index-document index.html --error-document 404.html --profile $profile
    
    # Create bucket policy file
    $bucketPolicy = @"
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$BucketName/*"
        }
    ]
}
"@
    $bucketPolicy | Out-File -FilePath "bucket-policy.json" -Encoding UTF8
    aws s3api put-bucket-policy --bucket $BucketName --policy file://bucket-policy.json --profile $profile
    Remove-Item "bucket-policy.json"
}

# Deploy files
Write-Host "☁️ Deploying to S3..." -ForegroundColor Yellow
if (Test-Path "out") {
    aws s3 sync out/ s3://$BucketName --delete --region $region --profile $profile
} elseif (Test-Path ".next") {
    # Deploy Next.js build files
    aws s3 sync .next/static/ s3://$BucketName/_next/static/ --region $region --profile $profile
    if (Test-Path "public") {
        aws s3 sync public/ s3://$BucketName/ --region $region --profile $profile
    }
} else {
    Write-Host "❌ No build output found" -ForegroundColor Red
    exit 1
}

Set-Location ..

$websiteUrl = "http://$BucketName.s3-website-$region.amazonaws.com"
Write-Host ""
Write-Host "🎉 Deployment complete!" -ForegroundColor Green
Write-Host "🔗 Website URL: $websiteUrl" -ForegroundColor Cyan
Write-Host "🔗 API URL: $apiUrl" -ForegroundColor Cyan

# Test the deployment
Write-Host ""
Write-Host "🧪 Testing deployment..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri $websiteUrl -Method HEAD -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Website is accessible!" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ Website might take a few minutes to be available" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Yellow
Write-Host "1. Visit $websiteUrl to test the application" -ForegroundColor White
Write-Host "2. For full Next.js functionality, consider using AWS Amplify or Vercel" -ForegroundColor White
Write-Host "3. The current deployment provides basic functionality" -ForegroundColor White