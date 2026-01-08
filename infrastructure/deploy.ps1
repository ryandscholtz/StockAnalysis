# PowerShell deployment script for DynamoDB table

Write-Host "🚀 Deploying Stock Analysis DynamoDB Table..." -ForegroundColor Cyan

# Check if AWS CLI is configured
try {
    $null = aws sts get-caller-identity 2>&1
} catch {
    Write-Host "❌ AWS CLI not configured. Run 'aws configure' first." -ForegroundColor Red
    exit 1
}

# Check if CDK is installed
if (-not (Get-Command cdk -ErrorAction SilentlyContinue)) {
    Write-Host "❌ CDK CLI not found. Install with: npm install -g aws-cdk" -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
npm install

# Bootstrap CDK (if needed)
Write-Host "🔧 Checking CDK bootstrap..." -ForegroundColor Yellow
try {
    $null = aws cloudformation describe-stacks --stack-name CDKToolkit 2>&1
    Write-Host "✅ CDK already bootstrapped" -ForegroundColor Green
} catch {
    Write-Host "📚 Bootstrapping CDK (first time only)..." -ForegroundColor Yellow
    cdk bootstrap
}

# Get Cerebrum AWS account ID if not set
if (-not $env:CDK_DEFAULT_ACCOUNT) {
    Write-Host "⚠️  CDK_DEFAULT_ACCOUNT not set. Using default Cerebrum account (295202642810)..." -ForegroundColor Yellow
    $env:CDK_DEFAULT_ACCOUNT = '295202642810'
    Write-Host "Using Cerebrum account: $env:CDK_DEFAULT_ACCOUNT" -ForegroundColor Green
} else {
    Write-Host "Using Cerebrum account: $env:CDK_DEFAULT_ACCOUNT" -ForegroundColor Green
}

# Deploy
Write-Host "🚀 Deploying stack..." -ForegroundColor Yellow
cdk deploy --require-approval never

Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host 'Table Name: stock-analyses' -ForegroundColor Cyan
Write-Host 'To verify: aws dynamodb describe-table --table-name stock-analyses' -ForegroundColor Cyan

