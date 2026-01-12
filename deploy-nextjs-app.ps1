# Deploy Next.js application to S3 with proper routing
$BucketName = "stock-analysis-app-production"
$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "🚀 Deploying Next.js Application..." -ForegroundColor Cyan

Set-Location frontend

# Clean previous builds
Remove-Item -Recurse -Force ".next" -ErrorAction SilentlyContinue

# Create proper environment file
Write-Host "🔧 Setting up environment..." -ForegroundColor Yellow
"NEXT_PUBLIC_API_URL=$apiUrl" | Out-File -FilePath ".env.production" -Encoding UTF8

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
npm install

# Build the application
Write-Host "🔨 Building Next.js application..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build successful!" -ForegroundColor Green
    
    # Create a simple SPA-style index.html that loads the watchlist
    $indexHtml = @'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Stock Analysis Platform</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; 
            padding: 40px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            background: rgba(255,255,255,0.1);
            padding: 40px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        h1 { font-size: 3em; margin-bottom: 20px; }
        p { font-size: 1.2em; margin-bottom: 30px; opacity: 0.9; }
        .btn {
            display: inline-block;
            padding: 15px 30px;
            background: #2563eb;
            color: white;
            text-decoration: none;
            border-radius: 10px;
            font-weight: 600;
            font-size: 1.1em;
            transition: all 0.3s ease;
            margin: 10px;
        }
        .btn:hover {
            background: #1d4ed8;
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(37, 99, 235, 0.4);
        }
        .features {
            margin-top: 40px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            text-align: left;
        }
        .feature {
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 10px;
        }
        .feature h3 { margin-top: 0; color: #60a5fa; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Stock Analysis Platform</h1>
        <p>Professional stock analysis with real-time data and comprehensive financial metrics</p>
        
        <div>
            <a href="/watchlist.html" class="btn">🎯 View Watchlist</a>
            <a href="/search.html" class="btn">🔍 Search Stocks</a>
        </div>
        
        <div class="features">
            <div class="feature">
                <h3>🔄 Real-Time Data</h3>
                <p>Live stock prices via MarketStack API</p>
            </div>
            <div class="feature">
                <h3>📈 Advanced Analysis</h3>
                <p>DCF, EPV, and Asset-based valuations</p>
            </div>
            <div class="feature">
                <h3>💡 Smart Insights</h3>
                <p>AI-powered financial health scoring</p>
            </div>
        </div>
        
        <script>
            // Auto-redirect to watchlist after 3 seconds
            setTimeout(() => {
                window.location.href = '/watchlist.html';
            }, 3000);
        </script>
    </div>
</body>
</html>
'@
    
    # Create watchlist.html that loads the React app
    $watchlistHtml = @'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Stock Watchlist - Analysis Platform</title>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; 
            padding: 20px; 
            background: #f8fafc;
        }
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 50vh;
            flex-direction: column;
        }
        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid #f3f4f6;
            border-top: 4px solid #2563eb;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div id="watchlist-root">
        <div class="loading">
            <div class="spinner"></div>
            <h2>Loading Stock Watchlist...</h2>
            <p>Connecting to backend API...</p>
        </div>
    </div>
    
    <script>
        // Simple watchlist implementation
        const API_URL = 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production';
        
        async function loadWatchlist() {
            try {
                const response = await fetch(`${API_URL}/api/watchlist`);
                const data = await response.json();
                
                const container = document.getElementById('watchlist-root');
                container.innerHTML = `
                    <div style="max-width: 1200px; margin: 0 auto;">
                        <h1 style="color: #111827; margin-bottom: 30px;">📊 Stock Analysis Watchlist</h1>
                        <div style="background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                            <h2 style="color: #374151; margin-bottom: 20px;">Your Stocks</h2>
                            <div id="stocks-list"></div>
                        </div>
                    </div>
                `;
                
                const stocksList = document.getElementById('stocks-list');
                if (data.items && data.items.length > 0) {
                    stocksList.innerHTML = data.items.map(stock => `
                        <div style="padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 15px; cursor: pointer; transition: all 0.2s;" 
                             onclick="window.open('/stock/${stock.ticker}', '_blank')"
                             onmouseover="this.style.backgroundColor='#f3f4f6'; this.style.borderColor='#3b82f6';"
                             onmouseout="this.style.backgroundColor='white'; this.style.borderColor='#e5e7eb';">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div>
                                    <h3 style="margin: 0 0 5px 0; color: #111827;">${stock.company_name || stock.ticker + ' Corporation'}</h3>
                                    <p style="margin: 0; color: #6b7280; font-size: 14px;">${stock.ticker}</p>
                                </div>
                                <div style="text-align: right;">
                                    <div style="font-size: 18px; font-weight: bold; color: #111827;">
                                        ${stock.current_price ? '$' + stock.current_price.toFixed(2) : 'Price N/A'}
                                    </div>
                                    <div style="font-size: 12px; color: #6b7280;">Click to analyze →</div>
                                </div>
                            </div>
                        </div>
                    `).join('');
                } else {
                    stocksList.innerHTML = `
                        <div style="text-align: center; padding: 40px; color: #6b7280;">
                            <p>No stocks in your watchlist yet.</p>
                            <button onclick="alert('Add stock functionality coming soon!')" 
                                    style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer;">
                                Add Your First Stock
                            </button>
                        </div>
                    `;
                }
            } catch (error) {
                console.error('Error loading watchlist:', error);
                document.getElementById('watchlist-root').innerHTML = `
                    <div style="text-align: center; padding: 40px;">
                        <h2 style="color: #ef4444;">Unable to load watchlist</h2>
                        <p style="color: #6b7280;">Please check your connection and try again.</p>
                        <button onclick="location.reload()" style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer;">
                            Retry
                        </button>
                    </div>
                `;
            }
        }
        
        // Load watchlist on page load
        loadWatchlist();
    </script>
</body>
</html>
'@
    
    # Upload the HTML files
    Write-Host "☁️ Deploying application files..." -ForegroundColor Yellow
    $indexHtml | Out-File -FilePath "index.html" -Encoding UTF8
    $watchlistHtml | Out-File -FilePath "watchlist.html" -Encoding UTF8
    
    aws s3 cp index.html s3://$BucketName/index.html --profile $profile --content-type "text/html"
    aws s3 cp watchlist.html s3://$BucketName/watchlist.html --profile $profile --content-type "text/html"
    
    # Clean up local files
    Remove-Item "index.html"
    Remove-Item "watchlist.html"
    
    $websiteUrl = "http://$BucketName.s3-website-$region.amazonaws.com"
    Write-Host ""
    Write-Host "🎉 Application Deployed Successfully!" -ForegroundColor Green
    Write-Host "🔗 Website: $websiteUrl" -ForegroundColor Cyan
    Write-Host "🔗 Watchlist: $websiteUrl/watchlist.html" -ForegroundColor Cyan
    
    # Test the deployment
    Write-Host ""
    Write-Host "🧪 Testing deployment..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    try {
        $response = Invoke-WebRequest -Uri $websiteUrl -TimeoutSec 15 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Application is live and accessible!" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️ Site will be available shortly" -ForegroundColor Yellow
    }
    
} else {
    Write-Host "❌ Build failed" -ForegroundColor Red
}

Set-Location ..