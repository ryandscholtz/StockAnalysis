#!/usr/bin/env pwsh

Write-Host "🚀 Manual Production Deployment Script" -ForegroundColor Green

# Check prerequisites
Write-Host "`n📋 Checking prerequisites..." -ForegroundColor Yellow

# Check AWS CLI
try {
    $awsIdentity = aws sts get-caller-identity --output json | ConvertFrom-Json
    Write-Host "✅ AWS CLI configured for: $($awsIdentity.Arn)" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS CLI not configured. Run 'aws configure' first." -ForegroundColor Red
    exit 1
}

# Check Node.js
try {
    $nodeVersion = node --version
    Write-Host "✅ Node.js version: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "infrastructure")) {
    Write-Host "❌ Please run this script from the project root directory" -ForegroundColor Red
    exit 1
}

Write-Host "`n🏗️ Starting deployment..." -ForegroundColor Yellow

# Navigate to infrastructure
Set-Location infrastructure

# Install dependencies
Write-Host "📦 Installing CDK dependencies..." -ForegroundColor White
npm ci
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Build CDK
Write-Host "🔨 Building CDK..." -ForegroundColor White
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to build CDK" -ForegroundColor Red
    exit 1
}

# Bootstrap if needed
Write-Host "🥾 Bootstrapping CDK (if needed)..." -ForegroundColor White
npx cdk bootstrap --context environment=production
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ Bootstrap failed, but continuing..." -ForegroundColor Yellow
}

# Show diff
Write-Host "`n📊 Showing deployment diff..." -ForegroundColor White
npx cdk diff --context environment=production

# Confirm deployment
Write-Host "`n⚠️ Ready to deploy to PRODUCTION!" -ForegroundColor Yellow
$confirm = Read-Host "Type 'DEPLOY' to continue, or anything else to cancel"

if ($confirm -ne "DEPLOY") {
    Write-Host "❌ Deployment cancelled" -ForegroundColor Red
    Set-Location ..
    exit 1
}

# Deploy
Write-Host "`n🚀 Deploying to production..." -ForegroundColor Green
npx cdk deploy --all --context environment=production --require-approval never --outputs-file outputs.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Deployment successful!" -ForegroundColor Green
    
    # Show outputs
    if (Test-Path "outputs.json") {
        Write-Host "`n📋 Deployment outputs:" -ForegroundColor Cyan
        Get-Content outputs.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
        # Extract API endpoint for health check
        $outputs = Get-Content outputs.json | ConvertFrom-Json
        $apiEndpoint = $outputs.StockAnalysisStack.ApiEndpoint
        
        if ($apiEndpoint) {
            Write-Host "`n🏥 Running health check..." -ForegroundColor White
            try {
                $healthResponse = Invoke-WebRequest -Uri "$apiEndpoint/health" -TimeoutSec 30
                if ($healthResponse.StatusCode -eq 200) {
                    Write-Host "✅ Health check passed!" -ForegroundColor Green
                    Write-Host "🌐 API URL: $apiEndpoint" -ForegroundColor Cyan
                } else {
                    Write-Host "⚠️ Health check returned status: $($healthResponse.StatusCode)" -ForegroundColor Yellow
                }
            } catch {
                Write-Host "⚠️ Health check failed: $($_.Exception.Message)" -ForegroundColor Yellow
                Write-Host "This might be normal if the API is still starting up." -ForegroundColor Gray
            }
        }
    }
    
    Write-Host "`n🎉 Production deployment complete!" -ForegroundColor Green
    Write-Host "Monitor your application at: https://console.aws.amazon.com/cloudwatch/" -ForegroundColor Cyan
    
} else {
    Write-Host "`n❌ Deployment failed!" -ForegroundColor Red
    Write-Host "Check the error messages above for details." -ForegroundColor Gray
}

Set-Location ..