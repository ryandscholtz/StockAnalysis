# Deploy Next.js app to AWS Amplify
$region = "eu-west-1"
$profile = "Cerebrum"
$appName = "stock-analysis-frontend"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "🚀 Deploying to AWS Amplify..." -ForegroundColor Cyan

Set-Location frontend

# Create environment file
Write-Host "🔧 Setting up environment..." -ForegroundColor Yellow
"NEXT_PUBLIC_API_URL=$apiUrl" | Out-File -FilePath ".env.production" -Encoding UTF8

# Build the application
Write-Host "🔨 Building Next.js application..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build successful!" -ForegroundColor Green
    
    # Create Amplify app
    Write-Host "📦 Creating Amplify application..." -ForegroundColor Yellow
    
    try {
        $createCmd = "aws amplify create-app --name $appName --region $region --profile $profile --platform WEB"
        $createResult = Invoke-Expression $createCmd | ConvertFrom-Json
        $appId = $createResult.app.appId
        Write-Host "✅ Created Amplify app: $appId" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️ App might already exist, checking..." -ForegroundColor Yellow
        $listCmd = "aws amplify list-apps --region $region --profile $profile"
        $listResult = Invoke-Expression $listCmd | ConvertFrom-Json
        $existingApp = $listResult.apps | Where-Object { $_.name -eq $appName }
        if ($existingApp) {
            $appId = $existingApp.appId
            Write-Host "✅ Found existing app: $appId" -ForegroundColor Green
        }
        else {
            Write-Host "❌ Failed to create or find app" -ForegroundColor Red
            Set-Location ..
            exit 1
        }
    }
    
    # Create deployment package
    Write-Host "📦 Creating deployment package..." -ForegroundColor Yellow
    $zipPath = "../frontend-deploy.zip"
    if (Test-Path $zipPath) { Remove-Item $zipPath }
    
    # Create a temporary directory with only necessary files
    $tempDir = "../temp-deploy"
    if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force }
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    
    # Copy necessary files
    Copy-Item "package.json" $tempDir
    Copy-Item "package-lock.json" $tempDir -ErrorAction SilentlyContinue
    Copy-Item "next.config.js" $tempDir
    Copy-Item ".env.production" $tempDir
    Copy-Item "app" $tempDir -Recurse
    Copy-Item "components" $tempDir -Recurse
    Copy-Item "lib" $tempDir -Recurse
    Copy-Item "types" $tempDir -Recurse
    Copy-Item "public" $tempDir -Recurse -ErrorAction SilentlyContinue
    
    # Create amplify.yml in temp directory
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
    
    $amplifyYml | Out-File -FilePath "$tempDir/amplify.yml" -Encoding UTF8
    
    # Create zip from temp directory
    Compress-Archive -Path "$tempDir/*" -DestinationPath $zipPath -Force
    Remove-Item $tempDir -Recurse -Force
    
    Write-Host "✅ Deployment package created" -ForegroundColor Green
    
    # Get the full path for the zip file
    $fullZipPath = (Get-Item $zipPath).FullName
    
    Write-Host "🌿 Creating main branch..." -ForegroundColor Yellow
    $branchCmd = "aws amplify create-branch --app-id $appId --branch-name main --region $region --profile $profile"
    try {
        Invoke-Expression $branchCmd | Out-Null
        Write-Host "✅ Branch created" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️ Branch might already exist" -ForegroundColor Yellow
    }
    
    Write-Host "🚀 Starting deployment..." -ForegroundColor Yellow
    $deployCmd = "aws amplify start-deployment --app-id $appId --branch-name main --source-url `"file://$fullZipPath`" --region $region --profile $profile"
    
    try {
        $deployResult = Invoke-Expression $deployCmd | ConvertFrom-Json
        $jobId = $deployResult.jobSummary.jobId
        Write-Host "✅ Deployment started with job ID: $jobId" -ForegroundColor Green
        
        $appUrl = "https://main.$appId.amplifyapp.com"
        Write-Host ""
        Write-Host "🎉 Deployment Initiated!" -ForegroundColor Green
        Write-Host "🔗 Your app will be live at: $appUrl" -ForegroundColor Cyan
        Write-Host "🔗 Amplify Console: https://console.aws.amazon.com/amplify/home?region=$region#/$appId" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "⏳ Deployment is in progress. Check the Amplify Console for status." -ForegroundColor Yellow
        Write-Host "   The full React application with all components will be available once complete." -ForegroundColor Yellow
        
    }
    catch {
        Write-Host "❌ Deployment failed: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    # Clean up
    Remove-Item $zipPath -ErrorAction SilentlyContinue
    
} else {
    Write-Host "❌ Build failed" -ForegroundColor Red
}

Set-Location ..