# Deploy Frontend with Cognito Configuration
# This script builds and deploys the Next.js frontend with proper Cognito environment variables

Write-Host "🚀 Deploying Frontend with Cognito Configuration..." -ForegroundColor Green

# Set AWS profile
$env:AWS_PROFILE = "Cerebrum"

# Navigate to frontend directory
Set-Location frontend

Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
npm install

Write-Host "🔧 Building Next.js application for static export..." -ForegroundColor Yellow
# Build with production environment variables
npm run build

# Check if build was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "📁 Checking build output..." -ForegroundColor Yellow
if (Test-Path "out") {
    Write-Host "✅ Static export generated successfully" -ForegroundColor Green
    Get-ChildItem out | Select-Object Name, Length | Format-Table
} else {
    Write-Host "❌ Static export not found!" -ForegroundColor Red
    exit 1
}

# Navigate back to root
Set-Location ..

Write-Host "☁️ Deploying to S3..." -ForegroundColor Yellow

# Sync to S3 bucket
aws s3 sync frontend/out s3://stock-analysis-frontend-2026 --delete --profile Cerebrum

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ S3 sync failed!" -ForegroundColor Red
    exit 1
}

Write-Host "🔄 Invalidating CloudFront cache..." -ForegroundColor Yellow

# Get CloudFront distribution ID
$distributionId = "E3U5Z846WCYDVA"

# Create invalidation
aws cloudfront create-invalidation --distribution-id $distributionId --paths "/*" --profile Cerebrum

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ CloudFront invalidation failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Frontend deployed successfully with Cognito configuration!" -ForegroundColor Green
Write-Host "🌐 Frontend URL: https://d3dzzi09nwx2bk.cloudfront.net" -ForegroundColor Cyan
Write-Host "🔐 Cognito User Pool ID: eu-west-1_os9KVPAhb" -ForegroundColor Cyan
Write-Host "📧 Forgot password functionality should now work!" -ForegroundColor Green

Write-Host "`n🧪 Testing forgot password functionality..." -ForegroundColor Yellow
Write-Host "1. Go to: https://d3dzzi09nwx2bk.cloudfront.net/auth/forgot-password" -ForegroundColor White
Write-Host "2. Enter a valid email address" -ForegroundColor White
Write-Host "3. Check your email for the reset code" -ForegroundColor White
Write-Host "4. Use the reset code at: https://d3dzzi09nwx2bk.cloudfront.net/auth/reset-password" -ForegroundColor White