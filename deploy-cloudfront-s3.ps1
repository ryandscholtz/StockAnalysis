# Deploy Next.js Frontend to S3 + CloudFront
# This approach gives full control over the AWS infrastructure

param(
    [string]$BucketName = "stock-analysis-frontend-$(Get-Random -Minimum 1000 -Maximum 9999)",
    [string]$Region = "eu-west-1",
    [string]$Profile = "Cerebrum"
)

Write-Host "🚀 Deploying Frontend to S3 + CloudFront..." -ForegroundColor Green
Write-Host "📋 Configuration:" -ForegroundColor Yellow
Write-Host "   Bucket: $BucketName" -ForegroundColor Cyan
Write-Host "   Region: $Region" -ForegroundColor Cyan
Write-Host "   Profile: $Profile" -ForegroundColor Cyan

# Step 1: Configure Next.js for static export
Write-Host "🔧 Configuring Next.js for static export..." -ForegroundColor Yellow

# Update next.config.js for static export
$nextConfig = @"
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  trailingSlash: true,
  output: 'export',
  images: {
    unoptimized: true
  },
  // Handle dynamic routes with fallback
  async generateStaticParams() {
    return []
  }
}

module.exports = nextConfig
"@

Set-Content -Path "frontend/next.config.js" -Value $nextConfig

# Step 2: Build the application
Write-Host "🔨 Building Next.js application..." -ForegroundColor Yellow
Set-Location frontend

# Install dependencies if needed
if (!(Test-Path "node_modules")) {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    npm ci
}

# Build for static export
npm run build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed. Checking for dynamic route issues..." -ForegroundColor Red
    
    # Create a fallback page for dynamic routes
    Write-Host "🔧 Creating fallback configuration..." -ForegroundColor Yellow
    
    # Create a simple fallback for dynamic routes
    $fallbackConfig = @"
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  trailingSlash: true,
  output: 'export',
  images: {
    unoptimized: true
  },
  // Skip dynamic routes during build
  exportPathMap: async function (defaultPathMap, { dev, dir, outDir, distDir, buildId }) {
    const pages = {}
    // Only include static pages
    Object.keys(defaultPathMap).forEach(key => {
      if (!key.includes('[') && !key.includes(']')) {
        pages[key] = defaultPathMap[key]
      }
    })
    return pages
  }
}

module.exports = nextConfig
"@
    
    Set-Content -Path "next.config.js" -Value $fallbackConfig
    Write-Host "⚠️  Dynamic routes will be handled by client-side routing" -ForegroundColor Yellow
    npm run build
}

Set-Location ..

if (!(Test-Path "frontend/out")) {
    Write-Host "❌ Build output not found. Build may have failed." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Build completed successfully!" -ForegroundColor Green

# Step 3: Create S3 bucket
Write-Host "🪣 Creating S3 bucket..." -ForegroundColor Yellow

try {
    aws s3 mb s3://$BucketName --region $Region --profile $Profile
    Write-Host "✅ S3 bucket created: $BucketName" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Bucket may already exist or creation failed" -ForegroundColor Yellow
}

# Step 4: Configure bucket for static website hosting
Write-Host "🌐 Configuring S3 for static website hosting..." -ForegroundColor Yellow

$websiteConfig = @"
{
    "IndexDocument": {
        "Suffix": "index.html"
    },
    "ErrorDocument": {
        "Key": "index.html"
    }
}
"@

Set-Content -Path "website-config.json" -Value $websiteConfig

aws s3api put-bucket-website --bucket $BucketName --website-configuration file://website-config.json --profile $Profile

# Step 5: Set bucket policy for public read access
Write-Host "🔓 Setting bucket policy for public access..." -ForegroundColor Yellow

$bucketPolicy = @"
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$BucketName/*"
        }
    ]
}
"@

Set-Content -Path "bucket-policy.json" -Value $bucketPolicy

aws s3api put-bucket-policy --bucket $BucketName --policy file://bucket-policy.json --profile $Profile

# Step 6: Upload files to S3
Write-Host "📤 Uploading files to S3..." -ForegroundColor Yellow

aws s3 sync frontend/out s3://$BucketName --delete --profile $Profile

Write-Host "✅ Files uploaded to S3!" -ForegroundColor Green

# Step 7: Create CloudFront distribution
Write-Host "☁️  Creating CloudFront distribution..." -ForegroundColor Yellow

$cloudfrontConfig = @"
{
    "CallerReference": "stock-analysis-$(Get-Date -Format 'yyyyMMdd-HHmmss')",
    "Comment": "Stock Analysis Frontend Distribution",
    "DefaultRootObject": "index.html",
    "Origins": {
        "Quantity": 1,
        "Items": [
            {
                "Id": "S3-$BucketName",
                "DomainName": "$BucketName.s3-website-$Region.amazonaws.com",
                "CustomOriginConfig": {
                    "HTTPPort": 80,
                    "HTTPSPort": 443,
                    "OriginProtocolPolicy": "http-only"
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
        "Quantity": 1,
        "Items": [
            {
                "ErrorCode": 404,
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

Write-Host "✅ CloudFront distribution created!" -ForegroundColor Green
Write-Host "📋 Distribution Details:" -ForegroundColor Yellow
Write-Host "   Distribution ID: $distributionId" -ForegroundColor Cyan
Write-Host "   Domain Name: $domainName" -ForegroundColor Cyan
Write-Host "   Status: Deploying (this may take 10-15 minutes)" -ForegroundColor Cyan

# Step 8: Clean up temporary files
Remove-Item "website-config.json" -ErrorAction SilentlyContinue
Remove-Item "bucket-policy.json" -ErrorAction SilentlyContinue
Remove-Item "cloudfront-config.json" -ErrorAction SilentlyContinue

# Step 9: Output final information
Write-Host ""
Write-Host "🎉 Deployment initiated successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Access Information:" -ForegroundColor Yellow
Write-Host "   S3 Website URL: http://$BucketName.s3-website-$Region.amazonaws.com" -ForegroundColor Cyan
Write-Host "   CloudFront URL: https://$domainName" -ForegroundColor Cyan
Write-Host ""
Write-Host "⏳ CloudFront deployment status:" -ForegroundColor Yellow
Write-Host "   The CloudFront distribution is being deployed globally." -ForegroundColor White
Write-Host "   This process typically takes 10-15 minutes." -ForegroundColor White
Write-Host "   You can check status in the AWS Console or run:" -ForegroundColor White
Write-Host "   aws cloudfront get-distribution --id $distributionId --profile $Profile" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔧 Next Steps:" -ForegroundColor Yellow
Write-Host "   1. Wait for CloudFront deployment to complete" -ForegroundColor White
Write-Host "   2. Test the CloudFront URL" -ForegroundColor White
Write-Host "   3. Configure custom domain (optional)" -ForegroundColor White
Write-Host "   4. Set up CI/CD for automatic deployments" -ForegroundColor White

# Save deployment info
$deploymentInfo = @{
    BucketName = $BucketName
    Region = $Region
    DistributionId = $distributionId
    CloudFrontDomain = $domainName
    S3WebsiteUrl = "http://$BucketName.s3-website-$Region.amazonaws.com"
    CloudFrontUrl = "https://$domainName"
    DeploymentTime = Get-Date
}

$deploymentInfo | ConvertTo-Json | Set-Content "deployment-info.json"
Write-Host "💾 Deployment info saved to deployment-info.json" -ForegroundColor Green