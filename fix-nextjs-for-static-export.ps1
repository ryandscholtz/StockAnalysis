# Fix Next.js configuration for static export with dynamic routes

Write-Host "🔧 Fixing Next.js for static export with dynamic routes..." -ForegroundColor Green

# Step 1: Update Next.js config for static export
Write-Host "📝 Updating next.config.js..." -ForegroundColor Yellow

$nextConfig = @'
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  trailingSlash: true,
  output: 'export',
  images: {
    unoptimized: true
  }
}

module.exports = nextConfig
'@

Set-Content -Path "frontend/next.config.js" -Value $nextConfig

# Step 2: Create a layout file for the dynamic route to handle generateStaticParams
Write-Host "📝 Creating layout for dynamic route..." -ForegroundColor Yellow

$layoutContent = @'
// Layout for dynamic ticker route
export async function generateStaticParams() {
  // Return empty array to allow client-side routing for all tickers
  return []
}

export default function TickerLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <>{children}</>
}
'@

# Ensure directory exists
$tickerDir = "frontend/app/watchlist/[ticker]"
if (!(Test-Path $tickerDir)) {
    New-Item -ItemType Directory -Path $tickerDir -Force
}

Set-Content -Path "$tickerDir/layout.tsx" -Value $layoutContent

Write-Host "✅ Next.js configuration updated for static export!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Changes made:" -ForegroundColor Yellow
Write-Host "   ✓ Updated next.config.js for static export" -ForegroundColor Green
Write-Host "   ✓ Created layout.tsx with generateStaticParams" -ForegroundColor Green
Write-Host ""
Write-Host "🚀 Ready to build and deploy!" -ForegroundColor Green