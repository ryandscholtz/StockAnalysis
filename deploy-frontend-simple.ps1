# Simple PowerShell script for deploying Next.js frontend to AWS S3

param(
    [Parameter(Mandatory=$false)]
    [string]$BucketName = "stock-analysis-frontend-production",
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying Stock Analysis Frontend to AWS S3..." -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# Check if AWS CLI is configured
try {
    $callerIdentity = aws sts get-caller-identity --profile $profile --output json | ConvertFrom-Json
    Write-Host "✅ AWS CLI configured for account: $($callerIdentity.Account)" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS CLI not configured. Run 'aws configure --profile Cerebrum' first." -ForegroundColor Red
    exit 1
}

$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "📋 Deployment Configuration:" -ForegroundColor Yellow
Write-Host "  S3 Bucket: $BucketName" -ForegroundColor White
Write-Host "  Region: $region" -ForegroundColor White
Write-Host "  Profile: $profile" -ForegroundColor White
Write-Host "  API URL: $apiUrl" -ForegroundColor White

if ($DryRun) {
    Write-Host "🔍 DRY RUN MODE - No changes will be made" -ForegroundColor Yellow
}

# Navigate to frontend directory
if (-not (Test-Path "frontend")) {
    Write-Host "❌ Frontend directory not found. Run this script from the project root." -ForegroundColor Red
    exit 1
}

Set-Location frontend

# Install dependencies
Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Yellow
if (-not $DryRun) {
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
        exit 1
    }
}

# Create environment file
Write-Host "⚙️ Configuring environment variables..." -ForegroundColor Yellow
$envContent = "NEXT_PUBLIC_API_URL=$apiUrl"
if (-not $DryRun) {
    $envContent | Out-File -FilePath ".env.production" -Encoding UTF8
    Write-Host "✅ Created .env.production" -ForegroundColor Green
}

# Build the application
Write-Host "🔨 Building Next.js application..." -ForegroundColor Yellow
if (-not $DryRun) {
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Build completed successfully" -ForegroundColor Green
}

# Create S3 bucket if it doesn't exist
Write-Host "📦 Checking S3 bucket..." -ForegroundColor Yellow
if (-not $DryRun) {
    try {
        aws s3api head-bucket --bucket $BucketName --region $region --profile $profile 2>$null
        Write-Host "✅ S3 bucket exists" -ForegroundColor Green
    } catch {
        Write-Host "🆕 Creating S3 bucket: $BucketName" -ForegroundColor Yellow
        aws s3api create-bucket --bucket $BucketName --region $region --profile $profile --create-bucket-configuration LocationConstraint=$region
        
        # Configure bucket for static website hosting
        Write-Host "🌐 Configuring static website hosting..." -ForegroundColor Yellow
        $websiteConfig = '{
    "IndexDocument": {
        "Suffix": "index.html"
    },
    "ErrorDocument": {
        "Key": "404.html"
    }
}'
        $websiteConfig | Out-File -FilePath "website-config.json" -Encoding UTF8
        aws s3api put-bucket-website --bucket $BucketName --website-configuration file://website-config.json --profile $profile
        Remove-Item "website-config.json"
        
        # Configure bucket policy for public read access
        Write-Host "🔓 Configuring bucket policy..." -ForegroundColor Yellow
        $bucketPolicy = '{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::' + $BucketName + '/*"
        }
    ]
}'
        $bucketPolicy | Out-File -FilePath "bucket-policy.json" -Encoding UTF8
        aws s3api put-bucket-policy --bucket $BucketName --policy file://bucket-policy.json --profile $profile
        Remove-Item "bucket-policy.json"
        
        Write-Host "✅ Created and configured S3 bucket" -ForegroundColor Green
    }
}

# Deploy to S3
Write-Host "☁️ Deploying to S3..." -ForegroundColor Yellow
if (-not $DryRun) {
    # Sync files to S3
    aws s3 sync out/ s3://$BucketName --delete --region $region --profile $profile
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ S3 sync failed" -ForegroundColor Red
        exit 1
    }
    
    # Set proper content types for better performance
    Write-Host "🔧 Setting content types..." -ForegroundColor Yellow
    aws s3 cp s3://$BucketName s3://$BucketName --recursive --metadata-directive REPLACE --content-type "text/html" --exclude "*" --include "*.html" --region $region --profile $profile
    aws s3 cp s3://$BucketName s3://$BucketName --recursive --metadata-directive REPLACE --content-type "text/css" --exclude "*" --include "*.css" --region $region --profile $profile
    aws s3 cp s3://$BucketName s3://$BucketName --recursive --metadata-directive REPLACE --content-type "application/javascript" --exclude "*" --include "*.js" --region $region --profile $profile
    
    Write-Host "✅ Files deployed to S3" -ForegroundColor Green
}

# Return to project root
Set-Location ..

if (-not $DryRun) {
    $websiteUrl = "http://$BucketName.s3-website-$region.amazonaws.com"
    
    Write-Host ""
    Write-Host "🎉 Frontend deployment successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Deployment Summary:" -ForegroundColor Cyan
    Write-Host "======================" -ForegroundColor Cyan
    Write-Host "S3 Bucket: $BucketName" -ForegroundColor White
    Write-Host "Region: $region" -ForegroundColor White
    Write-Host "Website URL: $websiteUrl" -ForegroundColor White
    Write-Host "API URL: $apiUrl" -ForegroundColor White
    
    Write-Host ""
    Write-Host "🔗 Access your application at:" -ForegroundColor Yellow
    Write-Host "  $websiteUrl" -ForegroundColor Cyan
    
    Write-Host ""
    Write-Host "🧪 Testing the deployment..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri $websiteUrl -Method HEAD -TimeoutSec 10
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Website is accessible!" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️ Website might take a few minutes to be available" -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Test the application functionality" -ForegroundColor White
    Write-Host "2. Verify API connectivity" -ForegroundColor White
    Write-Host "3. Set up CloudFront for better performance (optional)" -ForegroundColor White
    Write-Host "4. Configure custom domain (optional)" -ForegroundColor White
    
} else {
    Write-Host "✅ Dry run complete. Use -DryRun:$false to deploy." -ForegroundColor Green
}