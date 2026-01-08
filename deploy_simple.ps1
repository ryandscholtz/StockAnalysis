Write-Host "Manual Production Deployment Script" -ForegroundColor Green

# Check AWS CLI
try {
    $awsIdentity = aws sts get-caller-identity --profile Cerebrum | ConvertFrom-Json
    Write-Host "AWS CLI configured for account: $($awsIdentity.Account)" -ForegroundColor Green
    $env:AWS_PROFILE = "Cerebrum"
    $env:CDK_DEFAULT_REGION = "eu-west-1"
    Write-Host "Using region: eu-west-1" -ForegroundColor Green
} catch {
    Write-Host "AWS CLI not configured. Run 'aws configure' first." -ForegroundColor Red
    exit 1
}

# Check Node.js
try {
    node --version
    Write-Host "Node.js found" -ForegroundColor Green
} catch {
    Write-Host "Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "infrastructure")) {
    Write-Host "Please run this script from the project root directory" -ForegroundColor Red
    exit 1
}

Write-Host "Starting deployment..." -ForegroundColor Yellow

# Navigate to infrastructure
Set-Location infrastructure

# Install dependencies
Write-Host "Installing CDK dependencies..." -ForegroundColor White
npm ci

# Build CDK
Write-Host "Building CDK..." -ForegroundColor White
npm run build

# Bootstrap if needed
Write-Host "Bootstrapping CDK..." -ForegroundColor White
npx cdk bootstrap --context environment=production

# Show diff
Write-Host "Showing deployment diff..." -ForegroundColor White
npx cdk diff --context environment=production

# Confirm deployment
Write-Host "Ready to deploy to PRODUCTION!" -ForegroundColor Yellow
$confirm = Read-Host "Type 'DEPLOY' to continue, or anything else to cancel"

if ($confirm -ne "DEPLOY") {
    Write-Host "Deployment cancelled" -ForegroundColor Red
    Set-Location ..
    exit 1
}

# Deploy
Write-Host "Deploying to production..." -ForegroundColor Green
npx cdk deploy --all --context environment=production --require-approval never --outputs-file outputs.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "Deployment successful!" -ForegroundColor Green
} else {
    Write-Host "Deployment failed!" -ForegroundColor Red
}

Set-Location ..