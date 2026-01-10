Write-Host "Deploying to production..." -ForegroundColor Green

Set-Location infrastructure
npm ci
npm run build
npx cdk deploy --all --context environment=production --require-approval never

if ($LASTEXITCODE -eq 0) {
    Write-Host "Deployment successful!" -ForegroundColor Green
} else {
    Write-Host "Deployment failed!" -ForegroundColor Red
}

Set-Location ..