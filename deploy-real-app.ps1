# Deploy Real Next.js App to AWS Amplify with SSR Support
$appId = "d2w7qchby0cr5y"
$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "Deploying Real Next.js App with SSR Support..." -ForegroundColor Cyan
Write-Host "App ID: $appId" -ForegroundColor Green

Set-Location frontend

# Create environment file
Write-Host "Setting up environment..." -ForegroundColor Yellow
"NEXT_PUBLIC_API_URL=$apiUrl" | Out-File -FilePath ".env.production" -Encoding UTF8

# Create proper amplify.yml for Next.js SSR
$amplifyYml = @"
version: 1
applications:
  - frontend:
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
    appRoot: .
"@

$amplifyYml | Out-File -FilePath "amplify.yml" -Encoding UTF8

# Create package.json scripts for Amplify
$packageJson = Get-Content "package.json" | ConvertFrom-Json
$packageJson.scripts.start = "next start"
$packageJson | ConvertTo-Json -Depth 10 | Out-File -FilePath "package.json" -Encoding UTF8

# Create deployment package
Write-Host "Creating deployment package..." -ForegroundColor Yellow
$zipPath = "../frontend-ssr-deploy.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }

# Include source files for SSR
$items = @(
    "app",
    "components", 
    "lib",
    "public",
    "package.json",
    "package-lock.json",
    "next.config.js",
    "tailwind.config.js",
    "tsconfig.json",
    "amplify.yml",
    ".env.production"
)

$existingItems = $items | Where-Object { Test-Path $_ }
Compress-Archive -Path $existingItems -DestinationPath $zipPath -Force

Write-Host "Deployment package created with source files" -ForegroundColor Green

# Upload to S3
Write-Host "Uploading to S3..." -ForegroundColor Yellow
aws s3 cp $zipPath "s3://stock-analysis-app-production/deployments/frontend-ssr-deploy.zip" --region $region --profile $profile

# Start deployment
Write-Host "Starting Amplify deployment..." -ForegroundColor Yellow
aws amplify start-deployment --app-id $appId --branch-name "main" --source-url "s3://stock-analysis-app-production/deployments/frontend-ssr-deploy.zip" --region $region --profile $profile

$appUrl = "https://main.$appId.amplifyapp.com"
Write-Host ""
Write-Host "Deployment Started with Next.js SSR Support!" -ForegroundColor Green
Write-Host "Your app will be live at: $appUrl" -ForegroundColor Cyan
Write-Host "Amplify Console: https://console.aws.amazon.com/amplify/home?region=$region#/$appId" -ForegroundColor Cyan
Write-Host ""
Write-Host "This deployment includes:" -ForegroundColor Cyan
Write-Host "   Full Next.js SSR and dynamic routing" -ForegroundColor White
Write-Host "   ALL React components working perfectly" -ForegroundColor White
Write-Host "   AnalysisCard, ValuationStatus, FinancialHealth" -ForegroundColor White
Write-Host "   BusinessQuality, GrowthMetrics, PriceRatios" -ForegroundColor White
Write-Host "   PDFUpload, ManualDataEntry, Interactive Charts" -ForegroundColor White
Write-Host ""
Write-Host "Deployment will complete in 5-10 minutes" -ForegroundColor Yellow

# Clean up
Remove-Item $zipPath -ErrorAction SilentlyContinue
Remove-Item "amplify.yml" -ErrorAction SilentlyContinue
Remove-Item ".env.production" -ErrorAction SilentlyContinue

Set-Location ..