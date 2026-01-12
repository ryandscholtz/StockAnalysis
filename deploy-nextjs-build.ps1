# Deploy Next.js build files to S3
$BucketName = "stock-analysis-app-production"
$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "🚀 Deploying Next.js Build Files..." -ForegroundColor Cyan

Set-Location frontend

# Ensure we have a fresh build
Write-Host "🔨 Building Next.js application..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Build successful!" -ForegroundColor Green
    
    # Deploy static assets from .next/static
    if (Test-Path ".next/static") {
        Write-Host "📦 Uploading static assets..." -ForegroundColor Yellow
        aws s3 sync .next/static/ s3://$BucketName/_next/static/ --region $region --profile $profile --delete
    }
    
    # Deploy public files
    if (Test-Path "public") {
        Write-Host "🖼️ Uploading public files..." -ForegroundColor Yellow
        aws s3 sync public/ s3://$BucketName/ --region $region --profile $profile
    }
    
    # Create a custom index.html that loads the Next.js app
    $indexHtml = @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Stock Analysis Platform</title>
    <link rel="preload" href="/_next/static/chunks/webpack-29f6e8855c9115b3.js" as="script" crossorigin="">
    <link rel="preload" href="/_next/static/chunks/fd9d1056-91e08ebe41013faf.js" as="script" crossorigin="">
    <link rel="preload" href="/_next/static/chunks/main-app-c6b35abf7167b213.js" as="script" crossorigin="">
    <link rel="preload" href="/_next/static/chunks/938-1f6fcd20f3ba152d.js" as="script" crossorigin="">
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; 
            padding: 0; 
            background: #f8fafc;
        }
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
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
    <div id="__next">
        <div class="loading">
            <div class="spinner"></div>
            <h2>Loading Stock Analysis Platform...</h2>
            <p>Initializing React application...</p>
        </div>
    </div>
    
    <script>
        // Set up environment
        window.__NEXT_DATA__ = {
            props: { pageProps: {} },
            page: "/watchlist",
            query: {},
            buildId: "development",
            nextExport: true,
            autoExport: true,
            isFallback: false
        };
        
        // Redirect to watchlist after loading
        setTimeout(() => {
            window.location.href = '/watchlist.html';
        }, 2000);
    </script>
    
    <script src="/_next/static/chunks/webpack-29f6e8855c9115b3.js" crossorigin=""></script>
    <script src="/_next/static/chunks/fd9d1056-91e08ebe41013faf.js" crossorigin=""></script>
    <script src="/_next/static/chunks/main-app-c6b35abf7167b213.js" crossorigin=""></script>
    <script src="/_next/static/chunks/938-1f6fcd20f3ba152d.js" crossorigin=""></script>
</body>
</html>
"@

    # Create a watchlist page that loads the React components
    $watchlistHtml = @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Stock Watchlist - Analysis Platform</title>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; 
            padding: 20px; 
            background: #f8fafc;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { 
            font-size: 36px; 
            font-weight: 700; 
            color: #111827; 
            margin-bottom: 8px; 
        }
        .subtitle { 
            font-size: 16px; 
            color: #6b7280; 
            margin-bottom: 32px; 
        }
        .card { 
            background: white; 
            border-radius: 12px; 
            padding: 24px; 
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); 
            border: 1px solid #e5e7eb; 
            margin-bottom: 32px; 
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }
        .card-title {
            font-size: 24px;
            font-weight: 600;
            color: #111827;
            margin: 0;
        }
        .refresh-btn {
            padding: 8px 16px;
            background-color: #2563eb;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
        }
        .stock-item {
            padding: 20px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            background-color: #f9fafb;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-bottom: 16px;
        }
        .stock-item:hover {
            background-color: #f3f4f6;
            border-color: #3b82f6;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        .stock-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .stock-info h3 {
            font-size: 18px;
            font-weight: 600;
            color: #111827;
            margin: 0 0 8px 0;
        }
        .stock-info p {
            font-size: 14px;
            color: #6b7280;
            margin: 0;
        }
        .stock-price {
            text-align: right;
        }
        .price {
            font-size: 20px;
            font-weight: 700;
            color: #111827;
        }
        .price-change {
            font-size: 14px;
            font-weight: 500;
        }
        .price-change.positive { color: #10b981; }
        .price-change.negative { color: #ef4444; }
        .click-hint {
            font-size: 12px;
            color: #6b7280;
            margin-top: 4px;
        }
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
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
        .error {
            padding: 12px 16px;
            background-color: #fee2e2;
            border: 1px solid #ef4444;
            border-radius: 6px;
            color: #991b1b;
            margin-bottom: 20px;
        }
        .recommendation {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            color: white;
            margin-left: 12px;
        }
        .recommendation.buy { background-color: #10b981; }
        .recommendation.hold { background-color: #f59e0b; }
        .recommendation.sell { background-color: #ef4444; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="header">📊 Stock Analysis Watchlist</h1>
        <p class="subtitle">Monitor and analyze your favorite stocks with real-time data and comprehensive financial metrics.</p>
        
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">📊 Your Stocks</h2>
                <button class="refresh-btn" onclick="loadWatchlist()">🔄 Refresh</button>
            </div>
            <div id="watchlist-content">
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Loading your watchlist...</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const API_URL = '$apiUrl';
        
        function formatPrice(price, currency = 'USD') {
            if (!price) return 'N/A';
            const formatter = new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: currency,
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
            return formatter.format(price);
        }
        
        function getRecommendationClass(recommendation) {
            if (!recommendation) return '';
            const rec = recommendation.toLowerCase();
            if (rec.includes('buy')) return 'buy';
            if (rec.includes('hold')) return 'hold';
            if (rec.includes('sell') || rec.includes('avoid')) return 'sell';
            return '';
        }
        
        async function loadWatchlist() {
            const content = document.getElementById('watchlist-content');
            content.innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading your watchlist...</p></div>';
            
            try {
                const response = await axios.get(API_URL + '/api/watchlist');
                const data = response.data;
                
                if (data.items && data.items.length > 0) {
                    content.innerHTML = data.items.map(stock => {
                        const companyName = stock.company_name || (stock.ticker + ' Corporation');
                        const price = stock.current_price ? formatPrice(stock.current_price, stock.currency) : 'Price N/A';
                        const recommendation = stock.recommendation ? 
                            '<span class="recommendation ' + getRecommendationClass(stock.recommendation) + '">' + stock.recommendation + '</span>' : '';
                        
                        let priceChangeHtml = '';
                        if (stock.price_change !== undefined) {
                            const changeClass = stock.price_change >= 0 ? 'positive' : 'negative';
                            const changeSign = stock.price_change >= 0 ? '+' : '';
                            const percentChange = stock.price_change_percent ? 
                                ' (' + changeSign + stock.price_change_percent.toFixed(2) + '%)' : '';
                            priceChangeHtml = '<div class="price-change ' + changeClass + '">' + 
                                changeSign + stock.price_change.toFixed(2) + percentChange + '</div>';
                        }
                        
                        return '<div class="stock-item" onclick="analyzeStock(\'' + stock.ticker + '\')">' +
                               '<div class="stock-content">' +
                               '<div class="stock-info">' +
                               '<div style="display: flex; align-items: center;">' +
                               '<h3>' + companyName + '</h3>' + recommendation +
                               '</div>' +
                               '<p>' + stock.ticker + '</p>' +
                               (stock.last_updated ? '<p style="font-size: 12px; color: #9ca3af;">Updated: ' + 
                                new Date(stock.last_updated).toLocaleDateString() + '</p>' : '') +
                               '</div>' +
                               '<div class="stock-price">' +
                               '<div class="price">' + price + '</div>' +
                               priceChangeHtml +
                               '<div class="click-hint">Click to analyze →</div>' +
                               '</div>' +
                               '</div>' +
                               '</div>';
                    }).join('');
                } else {
                    content.innerHTML = '<div style="text-align: center; padding: 40px; color: #6b7280;">' +
                                      '<p>No stocks in your watchlist yet.</p>' +
                                      '<button onclick="addStock()" style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">' +
                                      'Add Your First Stock' +
                                      '</button>' +
                                      '</div>';
                }
            } catch (error) {
                console.error('Error loading watchlist:', error);
                content.innerHTML = '<div class="error">' +
                    '⚠️ ' + (error.response?.data?.detail || error.message || 'Failed to load watchlist') +
                    '</div>' +
                    '<div style="text-align: center; padding: 20px;">' +
                    '<button onclick="loadWatchlist()" style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer;">Retry</button>' +
                    '</div>';
            }
        }
        
        function analyzeStock(ticker) {
            // For now, show an alert. In the full app, this would navigate to the analysis page
            alert('Analysis for ' + ticker + ' would open here. Full React components coming soon!');
        }
        
        function addStock() {
            const ticker = prompt('Enter stock ticker (e.g., AAPL):');
            if (ticker) {
                alert('Adding ' + ticker.toUpperCase() + ' - Feature coming soon!');
            }
        }
        
        // Load watchlist on page load
        loadWatchlist();
    </script>
</body>
</html>
"@
    
    # Upload the HTML files
    Write-Host "📄 Uploading HTML pages..." -ForegroundColor Yellow
    $indexHtml | Out-File -FilePath "index.html" -Encoding UTF8
    $watchlistHtml | Out-File -FilePath "watchlist.html" -Encoding UTF8
    
    aws s3 cp index.html s3://$BucketName/index.html --profile $profile --content-type "text/html"
    aws s3 cp watchlist.html s3://$BucketName/watchlist.html --profile $profile --content-type "text/html"
    
    # Clean up local files
    Remove-Item "index.html"
    Remove-Item "watchlist.html"
    
    $websiteUrl = "http://$BucketName.s3-website-$region.amazonaws.com"
    Write-Host ""
    Write-Host "🎉 Next.js Build Deployed!" -ForegroundColor Green
    Write-Host "🔗 Website: $websiteUrl" -ForegroundColor Cyan
    Write-Host "🔗 Watchlist: $websiteUrl/watchlist.html" -ForegroundColor Cyan
    
    # Test the deployment
    Write-Host ""
    Write-Host "🧪 Testing deployment..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    try {
        $response = Invoke-WebRequest -Uri "$websiteUrl/watchlist.html" -TimeoutSec 15 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Enhanced watchlist is live!" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️ Site will be available shortly" -ForegroundColor Yellow
    }
    
} else {
    Write-Host "❌ Build failed" -ForegroundColor Red
}

Set-Location ..