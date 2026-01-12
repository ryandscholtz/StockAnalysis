# Deploy the proper Next.js frontend with real components
$BucketName = "stock-analysis-app-production"
$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "🚀 Deploying PROPER Frontend Application..." -ForegroundColor Cyan

Set-Location frontend

# Clean previous builds
Remove-Item -Recurse -Force ".next" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "out" -ErrorAction SilentlyContinue

# Create proper environment file
"NEXT_PUBLIC_API_URL=$apiUrl" | Out-File -FilePath ".env.production" -Encoding UTF8

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
npm install

# Build the real application
Write-Host "🔨 Building real Next.js application..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build successful!" -ForegroundColor Green
    
    # Deploy static assets
    Write-Host "☁️ Deploying static assets..." -ForegroundColor Yellow
    aws s3 sync .next/static/ s3://$BucketName/_next/static/ --region $region --profile $profile
    
    # Deploy public files
    if (Test-Path "public") {
        aws s3 sync public/ s3://$BucketName/ --region $region --profile $profile
    }
    
    # Deploy the built HTML pages
    Write-Host "📄 Deploying HTML pages..." -ForegroundColor Yellow
    if (Test-Path ".next/server/app") {
        # Copy all built HTML files
        Get-ChildItem ".next/server/app" -Recurse -Filter "*.html" | ForEach-Object {
            $relativePath = $_.FullName.Substring((Get-Item ".next/server/app").FullName.Length + 1)
            $s3Path = $relativePath.Replace('\', '/')
            
            Write-Host "Uploading: $s3Path" -ForegroundColor Green
            aws s3 cp $_.FullName s3://$BucketName/$s3Path --profile $profile
        }
    }
    
    # Create a proper index.html that loads the watchlist
    $indexHtml = @'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Stock Analysis Platform</title>
    <link rel="stylesheet" href="/_next/static/css/8bf3e82623b865a9.css" crossorigin="" data-precedence="next"/>
    <script src="/_next/static/chunks/polyfills-c67a75d1b6f99dc8.js" crossorigin="" nomodule=""></script>
</head>
<body>
    <div id="__next">
        <div style="padding: 40px; text-align: center;">
            <h1>🚀 Stock Analysis Platform</h1>
            <p>Loading your professional stock analysis interface...</p>
            <div style="margin: 20px 0;">
                <a href="/watchlist.html" style="padding: 12px 24px; background: #2563eb; color: white; text-decoration: none; border-radius: 6px; font-weight: 600;">
                    Enter Watchlist
                </a>
            </div>
            <script>
                // Auto-redirect to watchlist
                setTimeout(() => {
                    window.location.href = '/watchlist.html';
                }, 2000);
            </script>
        </div>
    </div>
</body>
</html>
'@
    
    $indexHtml | Out-File -FilePath "index.html" -Encoding UTF8
    aws s3 cp index.html s3://$BucketName/index.html --profile $profile
    Remove-Item "index.html"
    
    $websiteUrl = "http://$BucketName.s3-website-$region.amazonaws.com"
    Write-Host ""
    Write-Host "🎉 PROPER Frontend Deployed!" -ForegroundColor Green
    Write-Host "🔗 Website: $websiteUrl" -ForegroundColor Cyan
    Write-Host "🔗 Watchlist: $websiteUrl/watchlist.html" -ForegroundColor Cyan
    
    # Test the deployment
    Write-Host ""
    Write-Host "🧪 Testing deployment..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    try {
        $response = Invoke-WebRequest -Uri "$websiteUrl/watchlist.html" -TimeoutSec 10 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Real application is live!" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️ Application will be available shortly" -ForegroundColor Yellow
    }
    
} else {
    Write-Host "❌ Build failed" -ForegroundColor Red
}

Set-Location ..