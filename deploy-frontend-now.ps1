# Simple PowerShell script for deploying Next.js frontend to AWS S3

param(
    [Parameter(Mandatory=$false)]
    [string]$BucketName = "stock-analysis-frontend-production",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying Stock Analysis Frontend to AWS S3..." -ForegroundColor Cyan

$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "📋 Configuration:" -ForegroundColor Yellow
Write-Host "  S3 Bucket: $BucketName"
Write-Host "  Region: $region"
Write-Host "  Profile: $profile"
Write-Host "  API URL: $apiUrl"

if ($DryRun) {
    Write-Host "🔍 DRY RUN MODE - No changes will be made" -ForegroundColor Yellow
    exit 0
}

# Check if frontend directory exists
if (-not (Test-Path "frontend")) {
    Write-Host "❌ Frontend directory not found. Run this script from the project root." -ForegroundColor Red
    exit 1
}

Set-Location frontend

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
npm install
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Create environment file
Write-Host "⚙️ Creating environment file..." -ForegroundColor Yellow
"NEXT_PUBLIC_API_URL=$apiUrl" | Out-File -FilePath ".env.production" -Encoding UTF8

# Build the application
Write-Host "🔨 Building application..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed" -ForegroundColor Red
    exit 1
}

# Check if bucket exists, create if not
Write-Host "📦 Checking S3 bucket..." -ForegroundColor Yellow
$bucketExists = $false
try {
    aws s3api head-bucket --bucket $BucketName --region $region --profile $profile 2>$null
    $bucketExists = $true
    Write-Host "✅ S3 bucket exists" -ForegroundColor Green
} catch {
    Write-Host "🆕 Creating S3 bucket..." -ForegroundColor Yellow
    aws s3api create-bucket --bucket $BucketName --region $region --profile $profile --create-bucket-configuration LocationConstraint=$region
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Created S3 bucket" -ForegroundColor Green
        
        # Enable static website hosting
        Write-Host "🌐 Enabling static website hosting..." -ForegroundColor Yellow
        aws s3 website s3://$BucketName --index-document index.html --error-document 404.html --profile $profile
        
        # Make bucket public
        Write-Host "🔓 Making bucket public..." -ForegroundColor Yellow
        aws s3api put-bucket-policy --bucket $BucketName --policy "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"PublicReadGetObject\",\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"s3:GetObject\",\"Resource\":\"arn:aws:s3:::$BucketName/*\"}]}" --profile $profile
    } else {
        Write-Host "❌ Failed to create S3 bucket" -ForegroundColor Red
        exit 1
    }
}

# Deploy to S3
Write-Host "☁️ Deploying to S3..." -ForegroundColor Yellow
aws s3 sync out/ s3://$BucketName --delete --region $region --profile $profile

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Deployment successful!" -ForegroundColor Green
    
    $websiteUrl = "http://$BucketName.s3-website-$region.amazonaws.com"
    
    Write-Host ""
    Write-Host "🎉 Frontend deployed successfully!" -ForegroundColor Green
    Write-Host "🔗 Website URL: $websiteUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "🧪 Testing accessibility..." -ForegroundColor Yellow
    
    Start-Sleep -Seconds 3
    try {
        $response = Invoke-WebRequest -Uri $websiteUrl -Method HEAD -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Website is accessible!" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️ Website might take a few minutes to be available" -ForegroundColor Yellow
    }
    
} else {
    Write-Host "❌ Deployment failed" -ForegroundColor Red
    exit 1
}

# Return to project root
Set-Location ..

Write-Host ""
Write-Host "📋 Deployment Complete!" -ForegroundColor Cyan
Write-Host "Website: http://$BucketName.s3-website-$region.amazonaws.com" -ForegroundColor White
Write-Host "API: $apiUrl" -ForegroundColor White