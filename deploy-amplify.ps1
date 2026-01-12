# Deploy Next.js app to AWS Amplify
$region = "eu-west-1"
$profile = "Cerebrum"
$appName = "stock-analysis-frontend"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "🚀 Deploying to AWS Amplify..." -ForegroundColor Cyan

# Check if Amplify CLI is installed
try {
    amplify --version | Out-Null
    Write-Host "✅ Amplify CLI found" -ForegroundColor Green
} catch {
    Write-Host "❌ Amplify CLI not found. Installing..." -ForegroundColor Red
    npm install -g @aws-amplify/cli
}

Set-Location frontend

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
        - echo "NEXT_PUBLIC_API_URL=$apiUrl" >> .env.production
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

# Create a simple deployment script that uses AWS CLI to create Amplify app
Write-Host "📦 Creating Amplify application..." -ForegroundColor Yellow

# Create the Amplify app
try {
    $createResult = aws amplify create-app --name $appName --region $region --profile $profile --platform WEB | ConvertFrom-Json
    $appId = $createResult.app.appId
    Write-Host "✅ Created Amplify app: $appId" -ForegroundColor Green
} catch {
    Write-Host "⚠️ App might already exist, trying to get existing app..." -ForegroundColor Yellow
    $listResult = aws amplify list-apps --region $region --profile $profile | ConvertFrom-Json
    $existingApp = $listResult.apps | Where-Object { $_.name -eq $appName }
    if ($existingApp) {
        $appId = $existingApp.appId
        Write-Host "✅ Found existing app: $appId" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to create or find app" -ForegroundColor Red
        exit 1
    }
}

# Set environment variables
Write-Host "🔧 Setting environment variables..." -ForegroundColor Yellow
aws amplify put-app --app-id $appId --environment-variables "NEXT_PUBLIC_API_URL=$apiUrl" --region $region --profile $profile

# Create a ZIP file of the frontend code
Write-Host "📦 Creating deployment package..." -ForegroundColor Yellow
$zipPath = "../frontend-deploy.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath }

# Create zip excluding node_modules and .next
$excludePatterns = @("node_modules", ".next", ".git", "*.log")
Compress-Archive -Path "." -DestinationPath $zipPath -Force

# Create a branch and deploy
Write-Host "🌿 Creating branch and deploying..." -ForegroundColor Yellow
try {
    $branchResult = aws amplify create-branch --app-id $appId --branch-name "main" --region $region --profile $profile | ConvertFrom-Json
    Write-Host "✅ Created branch: main" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Branch might already exist" -ForegroundColor Yellow
}

# Start deployment
Write-Host "🚀 Starting deployment..." -ForegroundColor Yellow
$deployResult = aws amplify start-deployment --app-id $appId --branch-name "main" --source-url "file://$((Get-Item $zipPath).FullName)" --region $region --profile $profile | ConvertFrom-Json

$jobId = $deployResult.jobSummary.jobId
Write-Host "✅ Deployment started with job ID: $jobId" -ForegroundColor Green

# Wait for deployment to complete
Write-Host "⏳ Waiting for deployment to complete..." -ForegroundColor Yellow
do {
    Start-Sleep -Seconds 10
    $jobStatus = aws amplify get-job --app-id $appId --branch-name "main" --job-id $jobId --region $region --profile $profile | ConvertFrom-Json
    $status = $jobStatus.job.summary.status
    Write-Host "Status: $status" -ForegroundColor Cyan
} while ($status -eq "RUNNING" -or $status -eq "PENDING")

if ($status -eq "SUCCEED") {
    $appUrl = "https://main.$appId.amplifyapp.com"
    Write-Host ""
    Write-Host "🎉 Deployment Successful!" -ForegroundColor Green
    Write-Host "🔗 Your app is live at: $appUrl" -ForegroundColor Cyan
    Write-Host "🔗 Amplify Console: https://console.aws.amazon.com/amplify/home?region=$region#/$appId" -ForegroundColor Cyan
    
    # Test the deployment
    Write-Host ""
    Write-Host "🧪 Testing deployment..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    try {
        $response = Invoke-WebRequest -Uri $appUrl -TimeoutSec 30 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ App is live and responding!" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️ App is deploying, may take a few more minutes" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Deployment failed with status: $status" -ForegroundColor Red
    # Get deployment logs
    Write-Host "📋 Deployment logs:" -ForegroundColor Yellow
    aws amplify get-job --app-id $appId --branch-name "main" --job-id $jobId --region $region --profile $profile
}

# Clean up
Remove-Item $zipPath -ErrorAction SilentlyContinue
Remove-Item "amplify.yml" -ErrorAction SilentlyContinue

Set-Location ..