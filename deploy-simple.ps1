# Simple deployment script
$BucketName = "stock-analysis-frontend-production"
$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "Deploying frontend to S3..." -ForegroundColor Cyan

# Navigate to frontend
Set-Location frontend

# Create env file
$apiUrl | Out-File -FilePath ".env.production" -Encoding UTF8 -NoNewline
"NEXT_PUBLIC_API_URL=$apiUrl" | Out-File -FilePath ".env.production" -Encoding UTF8

# Install and build
Write-Host "Installing dependencies..." -ForegroundColor Yellow
npm install

Write-Host "Building application..." -ForegroundColor Yellow
npm run build

# Create bucket if needed
Write-Host "Checking S3 bucket..." -ForegroundColor Yellow
aws s3api head-bucket --bucket $BucketName --region $region --profile $profile 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating S3 bucket..." -ForegroundColor Yellow
    aws s3api create-bucket --bucket $BucketName --region $region --profile $profile --create-bucket-configuration LocationConstraint=$region
    aws s3 website s3://$BucketName --index-document index.html --profile $profile
    aws s3api put-bucket-policy --bucket $BucketName --profile $profile --policy '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":"*","Action":"s3:GetObject","Resource":"arn:aws:s3:::stock-analysis-frontend-production/*"}]}'
}

# Deploy
Write-Host "Deploying to S3..." -ForegroundColor Yellow
aws s3 sync .next/static/ s3://$BucketName/_next/static/ --region $region --profile $profile
aws s3 sync public/ s3://$BucketName/ --region $region --profile $profile

# For Next.js standalone build, we need to handle this differently
# Let's use a simpler approach with static export
Write-Host "Note: For full Next.js deployment, consider using AWS Amplify or Vercel" -ForegroundColor Yellow

Set-Location ..

$websiteUrl = "http://$BucketName.s3-website-$region.amazonaws.com"
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host "Website URL: $websiteUrl" -ForegroundColor Cyan