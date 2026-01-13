# Deploy Next.js App to Vercel
# This is the recommended approach for Next.js applications

Write-Host "🚀 Deploying Stock Analysis App to Vercel..." -ForegroundColor Green

# Check if Vercel CLI is installed
try {
    $vercelVersion = vercel --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Vercel CLI not found. Installing..." -ForegroundColor Yellow
        npm install -g vercel
    } else {
        Write-Host "✅ Vercel CLI found: $vercelVersion" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Installing Vercel CLI..." -ForegroundColor Yellow
    npm install -g vercel
}

# Navigate to frontend directory
Set-Location frontend

Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
npm ci

Write-Host "🔨 Building application..." -ForegroundColor Yellow
npm run build

Write-Host "🚀 Deploying to Vercel..." -ForegroundColor Yellow
Write-Host "Note: You'll need to authenticate with Vercel on first use" -ForegroundColor Cyan

# Deploy to Vercel
vercel --prod

Write-Host "✅ Deployment completed!" -ForegroundColor Green
Write-Host "🌐 Your app should be available at the URL shown above" -ForegroundColor Cyan

Set-Location ..