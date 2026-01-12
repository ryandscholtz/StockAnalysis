# Deploy to AWS Amplify - Simple Version
$appId = "d2w7qchby0cr5y"
$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "🚀 Deploying to AWS Amplify..." -ForegroundColor Cyan
Write-Host "📱 App ID: $appId" -ForegroundColor Green

Set-Location frontend

# Create environment file
Write-Host "🔧 Setting up environment..." -ForegroundColor Yellow
"NEXT_PUBLIC_API_URL=$apiUrl" | Out-File -FilePath ".env.production" -Encoding UTF8

# Create amplify.yml for build configuration
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

# Create deployment package
Write-Host "📦 Creating deployment package..." -ForegroundColor Yellow
$zipPath = "../frontend-deploy.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }

# Create zip excluding unnecessary files
$excludeItems = @(".next", "node_modules", ".git", "*.log", ".env.local")
$items = Get-ChildItem -Path "." | Where-Object { $_.Name -notin $excludeItems }
Compress-Archive -Path $items -DestinationPath $zipPath -Force

Write-Host "✅ Deployment package created" -ForegroundColor Green

# Start deployment
Write-Host "🚀 Starting deployment..." -ForegroundColor Yellow
$fullZipPath = (Get-Item $zipPath).FullName

aws amplify start-deployment --app-id $appId --branch-name "main" --source-url "file://$fullZipPath" --region $region --profile $profile

$appUrl = "https://main.$appId.amplifyapp.com"
Write-Host ""
Write-Host "🎉 Deployment Started!" -ForegroundColor Green
Write-Host "🔗 Your app will be live at: $appUrl" -ForegroundColor Cyan
Write-Host "🔗 Amplify Console: https://console.aws.amazon.com/amplify/home?region=$region#/$appId" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 This deployment includes ALL your React components:" -ForegroundColor Cyan
Write-Host "   • AnalysisCard, ValuationStatus, FinancialHealth" -ForegroundColor White
Write-Host "   • BusinessQuality, GrowthMetrics, PriceRatios" -ForegroundColor White
Write-Host "   • PDFUpload, ManualDataEntry, Interactive Charts" -ForegroundColor White
Write-Host ""
Write-Host "⏱️ Deployment will complete in 3-5 minutes" -ForegroundColor Yellow
Write-Host "🔍 Monitor progress in the Amplify Console" -ForegroundColor Yellow

# Clean up
Remove-Item $zipPath -ErrorAction SilentlyContinue
Remove-Item "amplify.yml" -ErrorAction SilentlyContinue

Set-Location ..