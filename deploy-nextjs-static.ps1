# Deploy Next.js Static Build to CloudFront + S3
# This script creates a proper static deployment from the Next.js build

Write-Host "🚀 Deploying Next.js Static Build to CloudFront + S3" -ForegroundColor Green

# Create deployment directory
$deployDir = "frontend/deploy"
if (Test-Path $deployDir) {
    Remove-Item -Recurse -Force $deployDir
}
New-Item -ItemType Directory -Path $deployDir -Force | Out-Null

Write-Host "📁 Creating static deployment structure..." -ForegroundColor Yellow

# Copy HTML files from server build
Copy-Item "frontend/.next/server/app/index.html" "$deployDir/index.html"
Copy-Item "frontend/.next/server/app/watchlist.html" "$deployDir/watchlist.html"
Copy-Item "frontend/.next/server/app/single-search.html" "$deployDir/single-search.html"
Copy-Item "frontend/.next/server/app/docs.html" "$deployDir/docs.html"
Copy-Item "frontend/.next/server/app/batch-analysis.html" "$deployDir/batch-analysis.html"
Copy-Item "frontend/.next/server/app/batch-search.html" "$deployDir/batch-search.html"
Copy-Item "frontend/.next/server/app/processing-data.html" "$deployDir/processing-data.html"

# Copy static assets
Copy-Item -Recurse "frontend/.next/static" "$deployDir/_next/static"

# Create 404.html for CloudFront error handling
Copy-Item "frontend/.next/server/app/_not-found.html" "$deployDir/404.html"

Write-Host "📦 Uploading to S3..." -ForegroundColor Yellow

# Upload to S3
aws s3 sync $deployDir s3://stock-analysis-frontend-2026/ --profile Cerebrum --delete

Write-Host "🔄 Creating CloudFront invalidation..." -ForegroundColor Yellow

# Create CloudFront invalidation
aws cloudfront create-invalidation --distribution-id E3U5Z846WCYDVA --paths "/*" --profile Cerebrum

Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host "🌐 URL: https://d3dzzi09nwx2bk.cloudfront.net" -ForegroundColor Cyan

# Clean up
Remove-Item -Recurse -Force $deployDir

Write-Host "🎉 Next.js application deployed successfully!" -ForegroundColor Green