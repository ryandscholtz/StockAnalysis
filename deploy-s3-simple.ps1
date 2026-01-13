# Simple S3 + CloudFront deployment for Next.js build output
# This approach uses the .next build output directly

param(
    [string]$BucketName = "stock-analysis-frontend-$(Get-Random -Minimum 1000 -Maximum 9999)",
    [string]$Region = "eu-west-1",
    [string]$Profile = "Cerebrum"
)

Write-Host "🚀 Deploying Next.js build to S3 + CloudFront..." -ForegroundColor Green

# Step 1: Revert Next.js config to standard build (not static export)
Write-Host "🔧 Configuring Next.js for standard build..." -ForegroundColor Yellow

$nextConfig = @'
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  trailingSlash: true,
  images: {
    unoptimized: true
  },
  // Enable standalone output for better deployment
  output: 'standalone'
}

module.exports = nextConfig
'@

Set-Content -Path "frontend/next.config.js" -Value $nextConfig

# Step 2: Build the application
Write-Host "🔨 Building Next.js application..." -ForegroundColor Yellow
Set-Location frontend

npm ci
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    Set-Location ..
    exit 1
}

Set-Location ..

# Step 3: Create S3 bucket
Write-Host "🪣 Creating S3 bucket..." -ForegroundColor Yellow

try {
    aws s3 mb s3://$BucketName --region $Region --profile $Profile
    Write-Host "✅ S3 bucket created: $BucketName" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Bucket may already exist" -ForegroundColor Yellow
}

# Step 4: Upload the standalone build
Write-Host "📤 Uploading Next.js standalone build..." -ForegroundColor Yellow

# Upload the standalone server and static files
aws s3 sync frontend/.next/standalone s3://$BucketName --delete --profile $Profile
aws s3 sync frontend/.next/static s3://$BucketName/_next/static --delete --profile $Profile
aws s3 sync frontend/public s3://$BucketName --delete --profile $Profile

# Step 5: Set up Lambda@Edge for Next.js routing (simplified approach)
Write-Host "☁️  Setting up CloudFront distribution..." -ForegroundColor Yellow

$cloudfrontConfig = @"
{
    "CallerReference": "stock-analysis-$(Get-Date -Format 'yyyyMMdd-HHmmss')",
    "Comment": "Stock Analysis Frontend - Next.js Standalone",
    "DefaultRootObject": "index.html",
    "Origins": {
        "Quantity": 1,
        "Items": [
            {
                "Id": "S3-$BucketName",
                "DomainName": "$BucketName.s3.$Region.amazonaws.com",
                "S3OriginConfig": {
                    "OriginAccessIdentity": ""
                }
            }
        ]
    },
    "DefaultCacheBehavior": {
        "TargetOriginId": "S3-$BucketName",
        "ViewerProtocolPolicy": "redirect-to-https",
        "TrustedSigners": {
            "Enabled": false,
            "Quantity": 0
        },
        "ForwardedValues": {
            "QueryString": false,
            "Cookies": {
                "Forward": "none"
            }
        },
        "MinTTL": 0,
        "DefaultTTL": 86400,
        "MaxTTL": 31536000
    },
    "CustomErrorResponses": {
        "Quantity": 2,
        "Items": [
            {
                "ErrorCode": 404,
                "ResponsePagePath": "/index.html",
                "ResponseCode": "200",
                "ErrorCachingMinTTL": 300
            },
            {
                "ErrorCode": 403,
                "ResponsePagePath": "/index.html", 
                "ResponseCode": "200",
                "ErrorCachingMinTTL": 300
            }
        ]
    },
    "Enabled": true,
    "PriceClass": "PriceClass_100"
}
"@

Set-Content -Path "cloudfront-config.json" -Value $cloudfrontConfig

$distribution = aws cloudfront create-distribution --distribution-config file://cloudfront-config.json --profile $Profile | ConvertFrom-Json

$distributionId = $distribution.Distribution.Id
$domainName = $distribution.Distribution.DomainName

# Clean up
Remove-Item "cloudfront-config.json" -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "🎉 Deployment completed!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Access Information:" -ForegroundColor Yellow
Write-Host "   CloudFront URL: https://$domainName" -ForegroundColor Cyan
Write-Host "   Distribution ID: $distributionId" -ForegroundColor Cyan
Write-Host ""
Write-Host "⏳ Note: CloudFront deployment takes 10-15 minutes to complete globally." -ForegroundColor Yellow

# Save deployment info
$deploymentInfo = @{
    BucketName = $BucketName
    Region = $Region
    DistributionId = $distributionId
    CloudFrontDomain = $domainName
    CloudFrontUrl = "https://$domainName"
    DeploymentTime = Get-Date
    BuildType = "standalone"
}

$deploymentInfo | ConvertTo-Json | Set-Content "deployment-info.json"
Write-Host "💾 Deployment info saved to deployment-info.json" -ForegroundColor Green