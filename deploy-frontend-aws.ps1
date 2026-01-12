# PowerShell script for deploying Next.js frontend to AWS S3 + CloudFront

param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "production",
    
    [Parameter(Mandatory=$false)]
    [string]$BucketName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$CloudFrontDistributionId = "",
    
    [Parameter(Mandatory=$false)]
    [string]$DomainName = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$CreateInfrastructure = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying Stock Analysis Frontend to AWS..." -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

# Validate environment
if ($Environment -notin @("staging", "production")) {
    Write-Host "❌ Invalid environment: $Environment. Must be 'staging' or 'production'" -ForegroundColor Red
    exit 1
}

# Check if AWS CLI is configured
try {
    $callerIdentity = aws sts get-caller-identity --output json | ConvertFrom-Json
    Write-Host "✅ AWS CLI configured for account: $($callerIdentity.Account)" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS CLI not configured. Run 'aws configure' first." -ForegroundColor Red
    exit 1
}

# Set default values if not provided
if (-not $BucketName) {
    $BucketName = "stock-analysis-frontend-$Environment-$($callerIdentity.Account)"
}

$region = "eu-west-1"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "📋 Deployment Configuration:" -ForegroundColor Yellow
Write-Host "  Environment: $Environment" -ForegroundColor White
Write-Host "  S3 Bucket: $BucketName" -ForegroundColor White
Write-Host "  Region: $region" -ForegroundColor White
Write-Host "  API URL: $apiUrl" -ForegroundColor White
if ($DomainName) {
    Write-Host "  Domain: $DomainName" -ForegroundColor White
}

if ($DryRun) {
    Write-Host "🔍 DRY RUN MODE - No changes will be made" -ForegroundColor Yellow
}

# Create infrastructure if requested
if ($CreateInfrastructure) {
    Write-Host "🏗️ Creating AWS infrastructure..." -ForegroundColor Yellow
    
    if (-not $DryRun) {
        # Create S3 bucket
        Write-Host "📦 Creating S3 bucket: $BucketName" -ForegroundColor Yellow
        try {
            aws s3api head-bucket --bucket $BucketName --region $region 2>$null
            Write-Host "✅ S3 bucket already exists" -ForegroundColor Green
        } catch {
            aws s3api create-bucket --bucket $BucketName --region $region --create-bucket-configuration LocationConstraint=$region
            Write-Host "✅ Created S3 bucket: $BucketName" -ForegroundColor Green
        }
        
        # Configure bucket for static website hosting
        Write-Host "🌐 Configuring static website hosting..." -ForegroundColor Yellow
        $websiteConfig = @{
            IndexDocument = @{ Suffix = "index.html" }
            ErrorDocument = @{ Key = "404.html" }
        } | ConvertTo-Json -Depth 3
        
        $websiteConfig | Out-File -FilePath "website-config.json" -Encoding UTF8
        aws s3api put-bucket-website --bucket $BucketName --website-configuration file://website-config.json
        Remove-Item "website-config.json"
        
        # Configure bucket policy for public read access
        Write-Host "🔓 Configuring bucket policy..." -ForegroundColor Yellow
        $bucketPolicy = @{
            Version = "2012-10-17"
            Statement = @(
                @{
                    Sid = "PublicReadGetObject"
                    Effect = "Allow"
                    Principal = "*"
                    Action = "s3:GetObject"
                    Resource = "arn:aws:s3:::$BucketName/*"
                }
            )
        } | ConvertTo-Json -Depth 4
        
        $bucketPolicy | Out-File -FilePath "bucket-policy.json" -Encoding UTF8
        aws s3api put-bucket-policy --bucket $BucketName --policy file://bucket-policy.json
        Remove-Item "bucket-policy.json"
        
        # Create CloudFront distribution
        Write-Host "☁️ Creating CloudFront distribution..." -ForegroundColor Yellow
        $distributionConfig = @{
            CallerReference = "stock-analysis-$Environment-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            Comment = "Stock Analysis Frontend - $Environment"
            DefaultRootObject = "index.html"
            Origins = @{
                Quantity = 1
                Items = @(
                    @{
                        Id = "S3-$BucketName"
                        DomainName = "$BucketName.s3-website-$region.amazonaws.com"
                        CustomOriginConfig = @{
                            HTTPPort = 80
                            HTTPSPort = 443
                            OriginProtocolPolicy = "http-only"
                        }
                    }
                )
            }
            DefaultCacheBehavior = @{
                TargetOriginId = "S3-$BucketName"
                ViewerProtocolPolicy = "redirect-to-https"
                TrustedSigners = @{
                    Enabled = $false
                    Quantity = 0
                }
                ForwardedValues = @{
                    QueryString = $false
                    Cookies = @{ Forward = "none" }
                }
                MinTTL = 0
                DefaultTTL = 86400
                MaxTTL = 31536000
            }
            Enabled = $true
            PriceClass = "PriceClass_100"
        } | ConvertTo-Json -Depth 10
        
        $distributionConfig | Out-File -FilePath "distribution-config.json" -Encoding UTF8
        $distribution = aws cloudfront create-distribution --distribution-config file://distribution-config.json | ConvertFrom-Json
        Remove-Item "distribution-config.json"
        
        $CloudFrontDistributionId = $distribution.Distribution.Id
        $cloudfrontDomain = $distribution.Distribution.DomainName
        
        Write-Host "✅ Created CloudFront distribution: $CloudFrontDistributionId" -ForegroundColor Green
        Write-Host "🌐 CloudFront domain: $cloudfrontDomain" -ForegroundColor Green
    }
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
    
    # Export static files
    Write-Host "📤 Exporting static files..." -ForegroundColor Yellow
    npx next export
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Export failed" -ForegroundColor Red
        exit 1
    }
}

# Deploy to S3
Write-Host "☁️ Deploying to S3..." -ForegroundColor Yellow
if (-not $DryRun) {
    # Sync files to S3
    aws s3 sync out/ s3://$BucketName --delete --region $region
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ S3 sync failed" -ForegroundColor Red
        exit 1
    }
    
    # Set proper content types
    Write-Host "🔧 Setting content types..." -ForegroundColor Yellow
    aws s3 cp s3://$BucketName s3://$BucketName --recursive --metadata-directive REPLACE --content-type "text/html" --exclude "*" --include "*.html" --region $region
    aws s3 cp s3://$BucketName s3://$BucketName --recursive --metadata-directive REPLACE --content-type "text/css" --exclude "*" --include "*.css" --region $region
    aws s3 cp s3://$BucketName s3://$BucketName --recursive --metadata-directive REPLACE --content-type "application/javascript" --exclude "*" --include "*.js" --region $region
    aws s3 cp s3://$BucketName s3://$BucketName --recursive --metadata-directive REPLACE --content-type "application/json" --exclude "*" --include "*.json" --region $region
}

# Invalidate CloudFront cache
if ($CloudFrontDistributionId) {
    Write-Host "🔄 Invalidating CloudFront cache..." -ForegroundColor Yellow
    if (-not $DryRun) {
        $invalidation = aws cloudfront create-invalidation --distribution-id $CloudFrontDistributionId --paths "/*" | ConvertFrom-Json
        Write-Host "✅ Created invalidation: $($invalidation.Invalidation.Id)" -ForegroundColor Green
    }
}

# Return to project root
Set-Location ..

if (-not $DryRun) {
    Write-Host ""
    Write-Host "🎉 Frontend deployment successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Deployment Summary:" -ForegroundColor Cyan
    Write-Host "======================" -ForegroundColor Cyan
    Write-Host "S3 Bucket: $BucketName" -ForegroundColor White
    Write-Host "S3 Website URL: http://$BucketName.s3-website-$region.amazonaws.com" -ForegroundColor White
    
    if ($CloudFrontDistributionId) {
        Write-Host "CloudFront Distribution: $CloudFrontDistributionId" -ForegroundColor White
        Write-Host "CloudFront URL: https://$cloudfrontDomain" -ForegroundColor White
    }
    
    if ($DomainName) {
        Write-Host "Custom Domain: https://$DomainName" -ForegroundColor White
    }
    
    Write-Host ""
    Write-Host "🔗 Access your application at:" -ForegroundColor Yellow
    if ($CloudFrontDistributionId) {
        Write-Host "  https://$cloudfrontDomain" -ForegroundColor Cyan
    } else {
        Write-Host "  http://$BucketName.s3-website-$region.amazonaws.com" -ForegroundColor Cyan
    }
    
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Test the deployed application" -ForegroundColor White
    Write-Host "2. Configure custom domain (if needed)" -ForegroundColor White
    Write-Host "3. Set up monitoring and alerts" -ForegroundColor White
    Write-Host "4. Configure CI/CD pipeline for automated deployments" -ForegroundColor White
    
} else {
    Write-Host "✅ Dry run complete. Use -DryRun:$false to deploy." -ForegroundColor Green
}