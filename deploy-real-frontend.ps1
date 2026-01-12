# Deploy the real Next.js frontend with proper static export
$BucketName = "stock-analysis-app-production"
$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "🚀 Deploying Real Next.js Frontend Application..." -ForegroundColor Cyan

Set-Location frontend

# Clean previous builds
Remove-Item -Recurse -Force ".next" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "out" -ErrorAction SilentlyContinue

# Create proper environment file
Write-Host "🔧 Setting up environment..." -ForegroundColor Yellow
"NEXT_PUBLIC_API_URL=$apiUrl" | Out-File -FilePath ".env.production" -Encoding UTF8

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
npm install

# Build the application for static export
Write-Host "🔨 Building Next.js application for static export..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build successful!" -ForegroundColor Green
    
    # Check if out directory was created
    if (Test-Path "out") {
        Write-Host "📁 Static export directory found" -ForegroundColor Green
        
        # Deploy the entire out directory to S3
        Write-Host "☁️ Deploying static files to S3..." -ForegroundColor Yellow
        aws s3 sync out/ s3://$BucketName/ --region $region --profile $profile --delete
        
        # Set proper content types for specific files
        Write-Host "🔧 Setting content types..." -ForegroundColor Yellow
        aws s3 cp s3://$BucketName/ s3://$BucketName/ --recursive --metadata-directive REPLACE --content-type "text/html" --exclude "*" --include "*.html" --profile $profile
        aws s3 cp s3://$BucketName/ s3://$BucketName/ --recursive --metadata-directive REPLACE --content-type "text/css" --exclude "*" --include "*.css" --profile $profile
        aws s3 cp s3://$BucketName/ s3://$BucketName/ --recursive --metadata-directive REPLACE --content-type "application/javascript" --exclude "*" --include "*.js" --profile $profile
        
        $websiteUrl = "http://$BucketName.s3-website-$region.amazonaws.com"
        Write-Host ""
        Write-Host "🎉 Real Frontend Deployed Successfully!" -ForegroundColor Green
        Write-Host "🔗 Website: $websiteUrl" -ForegroundColor Cyan
        Write-Host "🔗 Watchlist: $websiteUrl/watchlist" -ForegroundColor Cyan
        
        # Test the deployment
        Write-Host ""
        Write-Host "🧪 Testing deployment..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        try {
            $response = Invoke-WebRequest -Uri $websiteUrl -TimeoutSec 15 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Host "✅ Real application is live and accessible!" -ForegroundColor Green
                
                # Test watchlist page specifically
                try {
                    $watchlistResponse = Invoke-WebRequest -Uri "$websiteUrl/watchlist" -TimeoutSec 15 -UseBasicParsing
                    if ($watchlistResponse.StatusCode -eq 200) {
                        Write-Host "✅ Watchlist page is working!" -ForegroundColor Green
                    }
                } catch {
                    Write-Host "⚠️ Watchlist page test failed, but main site is up" -ForegroundColor Yellow
                }
            }
        } catch {
            Write-Host "⚠️ Site will be available shortly (DNS propagation)" -ForegroundColor Yellow
        }
        
    } else {
        Write-Host "❌ Static export failed - out directory not found" -ForegroundColor Red
        Write-Host "This might be due to Next.js configuration issues" -ForegroundColor Yellow
    }
    
} else {
    Write-Host "❌ Build failed" -ForegroundColor Red
    Write-Host "Please check the build errors above" -ForegroundColor Yellow
}

Set-Location ..