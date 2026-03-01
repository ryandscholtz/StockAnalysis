# Redeploy frontend with correct Cognito configuration

Write-Host "Redeploying Frontend with Correct Configuration..." -ForegroundColor Green

$env:AWS_PROFILE = "Cerebrum"

Write-Host "`nCurrent Configuration (eu-west-1):" -ForegroundColor Cyan
Write-Host "User Pool ID: eu-west-1_os9KVPAhb" -ForegroundColor White
Write-Host "Client ID: 3mio6147kamjot07p7p27iqdg3" -ForegroundColor White
Write-Host "Region: eu-west-1" -ForegroundColor White

Write-Host "`nCleaning previous build..." -ForegroundColor Yellow
Set-Location frontend
Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force out -ErrorAction SilentlyContinue

Write-Host "Installing dependencies..." -ForegroundColor Yellow
npm install

Write-Host "Building with production environment..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}

Set-Location ..

Write-Host "Deploying to S3..." -ForegroundColor Yellow
aws s3 sync frontend/out s3://stock-analysis-frontend-2026 --delete --profile Cerebrum

Write-Host "Invalidating CloudFront cache..." -ForegroundColor Yellow
aws cloudfront create-invalidation --distribution-id E3U5Z846WCYDVA --paths "/*" --profile Cerebrum

Write-Host "`nDeployment Complete!" -ForegroundColor Green
Write-Host "Frontend URL: https://d3dzzi09nwx2bk.cloudfront.net" -ForegroundColor Cyan
Write-Host "`nConfiguration:" -ForegroundColor Cyan
Write-Host "  Region: eu-west-1" -ForegroundColor White
Write-Host "  User Pool: eu-west-1_os9KVPAhb" -ForegroundColor White
Write-Host "`nWait 2-3 minutes for CloudFront cache to clear, then test login" -ForegroundColor Yellow