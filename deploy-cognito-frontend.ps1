# Deploy Frontend with Cognito Configuration
Write-Host "Deploying Frontend with Cognito Configuration..." -ForegroundColor Green

# Set AWS profile
$env:AWS_PROFILE = "Cerebrum"

# Navigate to frontend directory
Set-Location frontend

Write-Host "Installing dependencies..." -ForegroundColor Yellow
npm install

Write-Host "Building Next.js application..." -ForegroundColor Yellow
npm run build

# Check if build was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

# Navigate back to root
Set-Location ..

Write-Host "Deploying to S3..." -ForegroundColor Yellow

# Sync to S3 bucket
aws s3 sync frontend/out s3://stock-analysis-frontend-2026 --delete --profile Cerebrum

Write-Host "Invalidating CloudFront cache..." -ForegroundColor Yellow

# Create invalidation
aws cloudfront create-invalidation --distribution-id E3U5Z846WCYDVA --paths "/*" --profile Cerebrum

Write-Host "Frontend deployed successfully!" -ForegroundColor Green
Write-Host "Frontend URL: https://d3dzzi09nwx2bk.cloudfront.net" -ForegroundColor Cyan