# Deploy Static Next.js Export to AWS Amplify
$appId = "d2w7qchby0cr5y"
$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "Building and Deploying Static Next.js Export to AWS Amplify..." -ForegroundColor Cyan
Write-Host "App ID: $appId" -ForegroundColor Green

Set-Location frontend

# Create environment file
Write-Host "Setting up environment..." -ForegroundColor Yellow
"NEXT_PUBLIC_API_URL=$apiUrl" | Out-File -FilePath ".env.production" -Encoding UTF8

# Build the static export
Write-Host "Installing dependencies..." -ForegroundColor Yellow
npm ci
if ($LASTEXITCODE -ne 0) {
    Write-Host "npm install failed" -ForegroundColor Red
    exit 1
}

Write-Host "Building static export..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed" -ForegroundColor Red
    exit 1
}

Write-Host "Build completed successfully" -ForegroundColor Green

# Create deployment package with static export
Write-Host "Creating deployment package..." -ForegroundColor Yellow
$zipPath = "../frontend-static-deploy.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }

# The static export is in the 'out' directory
if (Test-Path "out") {
    Set-Location out
    $items = Get-ChildItem -Path "." -Recurse
    Compress-Archive -Path $items -DestinationPath "../$zipPath" -Force
    Set-Location ..
    Write-Host "Static export packaged from 'out' directory" -ForegroundColor Green
} else {
    Write-Host "No 'out' directory found. Using .next directory..." -ForegroundColor Yellow
    Compress-Archive -Path ".next/*" -DestinationPath $zipPath -Force
}

# Upload to S3
Write-Host "Uploading to S3..." -ForegroundColor Yellow
aws s3 cp $zipPath "s3://stock-analysis-app-production/deployments/frontend-static-deploy.zip" --region $region --profile $profile

# Start deployment
Write-Host "Starting Amplify deployment..." -ForegroundColor Yellow
aws amplify start-deployment --app-id $appId --branch-name "main" --source-url "s3://stock-analysis-app-production/deployments/frontend-static-deploy.zip" --region $region --profile $profile

$appUrl = "https://main.$appId.amplifyapp.com"
Write-Host ""
Write-Host "Deployment Started with Static Next.js Export!" -ForegroundColor Green
Write-Host "Your app will be live at: $appUrl" -ForegroundColor Cyan
Write-Host "Amplify Console: https://console.aws.amazon.com/amplify/home?region=$region#/$appId" -ForegroundColor Cyan
Write-Host ""
Write-Host "This deployment includes ALL your React components:" -ForegroundColor Cyan
Write-Host "   AnalysisCard, ValuationStatus, FinancialHealth" -ForegroundColor White
Write-Host "   BusinessQuality, GrowthMetrics, PriceRatios" -ForegroundColor White
Write-Host "   PDFUpload, ManualDataEntry, Interactive Charts" -ForegroundColor White
Write-Host "   Static export with client-side routing" -ForegroundColor White
Write-Host ""
Write-Host "Deployment will complete in 3-5 minutes" -ForegroundColor Yellow

# Clean up
Remove-Item $zipPath -ErrorAction SilentlyContinue
Remove-Item ".env.production" -ErrorAction SilentlyContinue

Set-Location ..