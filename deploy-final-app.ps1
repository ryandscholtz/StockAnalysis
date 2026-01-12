# Final deployment - remove dynamic routes completely
$BucketName = "stock-analysis-app-production"
$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "Final App Deployment..." -ForegroundColor Cyan

Set-Location frontend

# Clean up
Remove-Item -Recurse -Force "out" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".next" -ErrorAction SilentlyContinue

# Create environment file
"NEXT_PUBLIC_API_URL=$apiUrl" | Out-File -FilePath ".env.production" -Encoding UTF8

# Backup and remove dynamic routes
Write-Host "Backing up dynamic routes..." -ForegroundColor Yellow
if (Test-Path "app/analysis/[ticker]") {
    Move-Item "app/analysis/[ticker]" "analysis-ticker-backup" -Force
}
if (Test-Path "app/watchlist/[ticker]") {
    Move-Item "app/watchlist/[ticker]" "watchlist-ticker-backup" -Force
}

# Update Next.js config
$nextConfig = @'
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true
  }
}

module.exports = nextConfig
'@

$nextConfig | Out-File -FilePath "next.config.js" -Encoding UTF8

# Build
Write-Host "Building app..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -eq 0) {
    Write-Host "Build successful!" -ForegroundColor Green
    
    # Create S3 bucket if needed
    aws s3api head-bucket --bucket $BucketName --region $region --profile $profile 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Creating S3 bucket..." -ForegroundColor Yellow
        aws s3api create-bucket --bucket $BucketName --region $region --profile $profile --create-bucket-configuration LocationConstraint=$region
        aws s3 website s3://$BucketName --index-document index.html --error-document 404.html --profile $profile
        aws s3api put-public-access-block --bucket $BucketName --public-access-block-configuration "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false" --profile $profile
        
        $policy = '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::stock-analysis-app-production/*"}]}'
        $policy | Out-File -FilePath "policy.json" -Encoding UTF8
        aws s3api put-bucket-policy --bucket $BucketName --policy file://policy.json --profile $profile
        Remove-Item "policy.json"
    }
    
    # Deploy
    Write-Host "Deploying to S3..." -ForegroundColor Yellow
    aws s3 sync out/ s3://$BucketName --delete --region $region --profile $profile
    
    $websiteUrl = "http://$BucketName.s3-website-$region.amazonaws.com"
    Write-Host ""
    Write-Host "SUCCESS! App deployed!" -ForegroundColor Green
    Write-Host "Website: $websiteUrl" -ForegroundColor Cyan
    Write-Host "Watchlist: $websiteUrl/watchlist/" -ForegroundColor Cyan
    
} else {
    Write-Host "Build failed" -ForegroundColor Red
}

# Restore dynamic routes
Write-Host "Restoring dynamic routes..." -ForegroundColor Yellow
if (Test-Path "analysis-ticker-backup") {
    Move-Item "analysis-ticker-backup" "app/analysis/[ticker]" -Force
}
if (Test-Path "watchlist-ticker-backup") {
    Move-Item "watchlist-ticker-backup" "app/watchlist/[ticker]" -Force
}

Set-Location ..