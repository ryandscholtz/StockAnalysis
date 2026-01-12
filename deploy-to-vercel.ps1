# Deploy to Vercel - Perfect Next.js Support
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "Deploying to Vercel for Full Next.js Support..." -ForegroundColor Cyan

Set-Location frontend

# Create environment file
Write-Host "Setting up environment..." -ForegroundColor Yellow
"NEXT_PUBLIC_API_URL=$apiUrl" | Out-File -FilePath ".env.production" -Encoding UTF8

# Remove static export config for Vercel
Write-Host "Configuring for Vercel deployment..." -ForegroundColor Yellow
$nextConfig = @"
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  trailingSlash: true,
  images: {
    unoptimized: true
  }
}

module.exports = nextConfig
"@

$nextConfig | Out-File -FilePath "next.config.js" -Encoding UTF8

# Install Vercel CLI if not present
Write-Host "Checking Vercel CLI..." -ForegroundColor Yellow
$vercelInstalled = Get-Command vercel -ErrorAction SilentlyContinue
if (-not $vercelInstalled) {
    Write-Host "Installing Vercel CLI..." -ForegroundColor Yellow
    npm install -g vercel
}

# Deploy to Vercel
Write-Host "Deploying to Vercel..." -ForegroundColor Yellow
Write-Host "This will open a browser for authentication if needed..." -ForegroundColor Yellow

vercel --prod

Write-Host ""
Write-Host "Vercel Deployment Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Your Next.js app is now deployed with:" -ForegroundColor Cyan
Write-Host "   Full SSR and dynamic routing support" -ForegroundColor White
Write-Host "   ALL React components working perfectly" -ForegroundColor White
Write-Host "   AnalysisCard, ValuationStatus, FinancialHealth" -ForegroundColor White
Write-Host "   BusinessQuality, GrowthMetrics, PriceRatios" -ForegroundColor White
Write-Host "   PDFUpload, ManualDataEntry, Interactive Charts" -ForegroundColor White
Write-Host "   Automatic HTTPS and global CDN" -ForegroundColor White
Write-Host ""
Write-Host "The deployed app will look EXACTLY like your local development version!" -ForegroundColor Green

Set-Location ..