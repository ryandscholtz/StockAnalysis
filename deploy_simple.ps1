#!/usr/bin/env pwsh

Write-Host "🚀 Simple Production Deployment Script" -ForegroundColor Green

# Check AWS CLI
try {
    $awsIdentity = aws sts get-caller-identity --output json | ConvertFrom-Json
    Write-Host "✅ AWS CLI configured for: $($awsIdentity.Arn)" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS CLI not configured. Run 'aws configure' first." -ForegroundColor Red
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

# Build CDK
Write-Host "🔨 Building CDK..." -ForegroundColor White
npm run build

# Deploy
Write-Host "`n🚀 Deploying to production..." -ForegroundColor Green
npx cdk deploy --all --context environment=production --require-approval never --outputs-file outputs.json

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Deployment successful!" -ForegroundColor Green
    
    # Show outputs
    if (Test-Path "outputs.json") {
        Write-Host "`n📋 Deployment outputs:" -ForegroundColor Cyan
        Get-Content outputs.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
    }
    
    Write-Host "`n🎉 Production deployment complete!" -ForegroundColor Green
} else {
    Write-Host "`n❌ Deployment failed!" -ForegroundColor Red
}

Set-Location ..