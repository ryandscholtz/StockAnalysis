# Deploy Full Next.js App to AWS Amplify
$appId = "d2w7qchby0cr5y"
$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "🚀 Building and Deploying Full Next.js App to AWS Amplify..." -ForegroundColor Cyan
Write-Host "📱 App ID: $appId" -ForegroundColor Green

Set-Location frontend

# Create environment file
Write-Host "🔧 Setting up environment..." -ForegroundColor Yellow
"NEXT_PUBLIC_API_URL=$apiUrl" | Out-File -FilePath ".env.production" -Encoding UTF8

# Create amplify.yml for proper Next.js build
$amplifyYml = @"
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: .next
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
      - .next/cache/**/*
"@

$amplifyYml | Out-File -FilePath "amplify.yml" -Encoding UTF8

# Build the Next.js application locally first
Write-Host "🔨 Building Next.js application..." -ForegroundColor Yellow
npm ci
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ npm install failed" -ForegroundColor Red
    exit 1
}

npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Build completed successfully" -ForegroundColor Green

# Create deployment package with built files
Write-Host "📦 Creating deployment package..." -ForegroundColor Yellow
$zipPath = "../frontend-built-deploy.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }

# Include all necessary files for deployment
$items = @(
    "package.json",
    "package-lock.json", 
    ".next",
    "public",
    "amplify.yml",
    ".env.production"
)

$existingItems = $items | Where-Object { Test-Path $_ }
Compress-Archive -Path $existingItems -DestinationPath $zipPath -Force

Write-Host "✅ Deployment package created with built files" -ForegroundColor Green

# Upload to S3 first
Write-Host "📤 Uploading to S3..." -ForegroundColor Yellow
aws s3 cp $zipPath "s3://stock-analysis-app-production/deployments/frontend-built-deploy.zip" --region $region --profile $profile

# Start deployment with built package
Write-Host "🚀 Starting Amplify deployment..." -ForegroundColor Yellow
aws amplify start-deployment --app-id $appId --branch-name "main" --source-url "s3://stock-analysis-app-production/deployments/frontend-built-deploy.zip" --region $region --profile $profile

$appUrl = "https://main.$appId.amplifyapp.com"
Write-Host ""
Write-Host "🎉 Deployment Started with Built Next.js App!" -ForegroundColor Green
Write-Host "🔗 Your app will be live at: $appUrl" -ForegroundColor Cyan
Write-Host "🔗 Amplify Console: https://console.aws.amazon.com/amplify/home?region=$region#/$appId" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 This deployment includes ALL your React components:" -ForegroundColor Cyan
Write-Host "   • AnalysisCard, ValuationStatus, FinancialHealth" -ForegroundColor White
Write-Host "   • BusinessQuality, GrowthMetrics, PriceRatios" -ForegroundColor White
Write-Host "   • PDFUpload, ManualDataEntry, Interactive Charts" -ForegroundColor White
Write-Host "   • Full Next.js SSR and dynamic routing" -ForegroundColor White
Write-Host ""
Write-Host "⏱️ Deployment will complete in 3-5 minutes" -ForegroundColor Yellow
Write-Host "🔍 Monitor progress in the Amplify Console" -ForegroundColor Yellow

# Clean up
Remove-Item $zipPath -ErrorAction SilentlyContinue
Remove-Item "amplify.yml" -ErrorAction SilentlyContinue
Remove-Item ".env.production" -ErrorAction SilentlyContinue

Set-Location ..