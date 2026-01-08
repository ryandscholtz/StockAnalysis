# PowerShell script for production deployment of Stock Analysis infrastructure

param(
    [Parameter(Mandatory=$false)]
    [string]$Environment = "production",
    
    [Parameter(Mandatory=$false)]
    [string]$DomainName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AlertEmail = "",
    
    [Parameter(Mandatory=$false)]
    [string]$SlackWebhookUrl = "",
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipSecrets = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying Stock Analysis Infrastructure to $Environment..." -ForegroundColor Cyan
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

# Check if CDK is installed
if (-not (Get-Command cdk -ErrorAction SilentlyContinue)) {
    Write-Host "❌ CDK CLI not found. Install with: npm install -g aws-cdk" -ForegroundColor Red
    exit 1
}

# Set environment variables
$env:ENVIRONMENT = $Environment
$env:CDK_DEFAULT_ACCOUNT = $callerIdentity.Account
$env:CDK_DEFAULT_REGION = "eu-west-1"

if ($DomainName) {
    $env:DOMAIN_NAME = $DomainName
    Write-Host "🌐 Using domain name: $DomainName" -ForegroundColor Yellow
}

if ($AlertEmail) {
    $env:ALERT_EMAIL = $AlertEmail
    Write-Host "📧 Alert email configured: $AlertEmail" -ForegroundColor Yellow
}

if ($SlackWebhookUrl) {
    $env:SLACK_WEBHOOK_URL = $SlackWebhookUrl
    Write-Host "💬 Slack webhook configured" -ForegroundColor Yellow
}

Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
npm install

# Bootstrap CDK if needed
Write-Host "🔧 Checking CDK bootstrap..." -ForegroundColor Yellow
try {
    $null = aws cloudformation describe-stacks --stack-name CDKToolkit --region $env:CDK_DEFAULT_REGION 2>$null
    Write-Host "✅ CDK already bootstrapped" -ForegroundColor Green
} catch {
    Write-Host "📚 Bootstrapping CDK for $Environment environment..." -ForegroundColor Yellow
    cdk bootstrap --context environment=$Environment
}

# Create production secrets if not skipped
if (-not $SkipSecrets) {
    Write-Host "🔐 Setting up production secrets..." -ForegroundColor Yellow
    
    $secretName = "stock-analysis-secrets-$Environment"
    
    # Check if secret already exists
    try {
        $existingSecret = aws secretsmanager describe-secret --secret-id $secretName --region $env:CDK_DEFAULT_REGION 2>$null
        Write-Host "✅ Secret $secretName already exists" -ForegroundColor Green
    } catch {
        Write-Host "🔐 Creating new secret: $secretName" -ForegroundColor Yellow
        
        # Generate secure JWT secret
        $jwtSecret = [System.Web.Security.Membership]::GeneratePassword(64, 16)
        $encryptionKey = [System.Web.Security.Membership]::GeneratePassword(32, 8)
        
        $secretValue = @{
            jwt_secret = $jwtSecret
            encryption_key = $encryptionKey
            external_api_keys = @{
                alpha_vantage = $env:ALPHA_VANTAGE_API_KEY
                marketstack = $env:MARKETSTACK_API_KEY
                fred = $env:FRED_API_KEY
                fmp = $env:FMP_API_KEY
            }
        } | ConvertTo-Json -Depth 3
        
        aws secretsmanager create-secret `
            --name $secretName `
            --description "Production secrets for Stock Analysis API" `
            --secret-string $secretValue `
            --region $env:CDK_DEFAULT_REGION
            
        Write-Host "✅ Created secret: $secretName" -ForegroundColor Green
    }
}

# Synthesize the stack first
Write-Host "🔍 Synthesizing CDK stack..." -ForegroundColor Yellow
cdk synth --context environment=$Environment

if ($DryRun) {
    Write-Host "🔍 Dry run - showing deployment diff..." -ForegroundColor Yellow
    cdk diff --context environment=$Environment
    Write-Host "✅ Dry run complete. Use -DryRun:$false to deploy." -ForegroundColor Green
    exit 0
}

# Deploy the infrastructure
Write-Host "🚀 Deploying infrastructure stack..." -ForegroundColor Yellow
$deployResult = cdk deploy --context environment=$Environment --require-approval never --outputs-file "outputs-$Environment.json"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Infrastructure deployment complete!" -ForegroundColor Green
    
    # Display outputs
    if (Test-Path "outputs-$Environment.json") {
        $outputs = Get-Content "outputs-$Environment.json" | ConvertFrom-Json
        Write-Host ""
        Write-Host "📋 Deployment Outputs:" -ForegroundColor Cyan
        Write-Host "======================" -ForegroundColor Cyan
        
        $outputs.PSObject.Properties | ForEach-Object {
            $stackName = $_.Name
            $_.Value.PSObject.Properties | ForEach-Object {
                Write-Host "$($_.Name): $($_.Value)" -ForegroundColor White
            }
        }
    }
    
    Write-Host ""
    Write-Host "🎉 Production deployment successful!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Update backend environment variables with the deployed resources" -ForegroundColor White
    Write-Host "2. Package and deploy the Lambda function code" -ForegroundColor White
    Write-Host "3. Configure monitoring and alerting" -ForegroundColor White
    Write-Host "4. Run smoke tests against the deployed API" -ForegroundColor White
    
} else {
    Write-Host "❌ Deployment failed!" -ForegroundColor Red
    exit 1
}