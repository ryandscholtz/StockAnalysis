# Deploy enhanced watchlist with better styling and functionality
$BucketName = "stock-analysis-app-production"
$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "🚀 Deploying Enhanced Watchlist..." -ForegroundColor Cyan

# Create enhanced watchlist HTML
$watchlistHtml = @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Stock Watchlist - Professional Analysis Platform</title>
    <script src="https://unpkg.com/axios/dist/axios.min.js"></script>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0; 
            padding: 20px; 
            background: #f8fafc;
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        
        /* Header Styles */
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
        
        /* Card Styles */
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
        
        /* Button Styles */
        .btn {
            padding: 8px 16px;
            background-color: #2563eb;
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .btn:hover {
            background-color: #1d4ed8;
            transform: translateY(-1px);
        }
        .btn-success {
            background-color: #10b981;
        }
        .btn-success:hover {
            background-color: #059669;
        }
        
        /* Stock Item Styles */
        .stock-grid {
            display: grid;
            gap: 16px;
        }
        .stock-item {
            padding: 20px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            background-color: #f9fafb;
            cursor: pointer;
            transition: all 0.2s ease;
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
        .stock-info {
            flex: 1;
        }
        .stock-info h3 {
            font-size: 18px;
            font-weight: 600;
            color: #111827;
            margin: 0 0 8px 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .stock-info p {
            font-size: 14px;
            color: #6b7280;
            margin: 0 0 4px 0;
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
            margin-top: 4px;
        }
        .price-change.positive { color: #10b981; }
        .price-change.negative { color: #ef4444; }
        .click-hint {
            font-size: 12px;
            color: #6b7280;
            margin-top: 4px;
        }
        
        /* Recommendation Badge */
        .recommendation {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            color: white;
        }
        .recommendation.strong-buy { background-color: #10b981; }
        .recommendation.buy { background-color: #3b82f6; }
        .recommendation.hold { background-color: #f59e0b; }
        .recommendation.avoid { background-color: #ef4444; }
        
        /* Loading and Error States */
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 40px;
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
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #6b7280;
        }
        
        /* Features Section */
        .features {
            padding: 24px;
            background-color: #eff6ff;
            border: 1px solid #3b82f6;
            border-radius: 12px;
        }
        .features h3 {
            font-size: 20px;
            font-weight: 600;
            color: #1e40af;
            margin-bottom: 16px;
        }
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 16px;
        }
        .feature {
            background: rgba(255,255,255,0.7);
            padding: 16px;
            border-radius: 8px;
        }
        .feature h4 {
            font-size: 16px;
            font-weight: 600;
            color: #1e40af;
            margin-bottom: 8px;
        }
        .feature p {
            font-size: 14px;
            color: #1e3a8a;
            margin: 0;
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .container { padding: 0 10px; }
            .header { font-size: 28px; }
            .stock-content { flex-direction: column; align-items: flex-start; gap: 12px; }
            .stock-price { text-align: left; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="header">📊 Stock Analysis Watchlist</h1>
        <p class="subtitle">Monitor and analyze your favorite stocks with real-time data and comprehensive financial metrics.</p>
        
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">📊 Your Stocks</h2>
                <div>
                    <button class="btn" onclick="loadWatchlist()">🔄 Refresh</button>
                    <button class="btn btn-success" onclick="addStock()" style="margin-left: 8px;">➕ Add Stock</button>
                </div>
            </div>
            <div id="watchlist-content">
                <div class="loading">
                    <div class="spinner"></div>
                    <p style="margin-top: 20px; color: #6b7280;">Loading your watchlist...</p>
                </div>
            </div>
        </div>
        
        <div class="features">
            <h3>🚀 Platform Features</h3>
            <div class="features-grid">
                <div class="feature">
                    <h4>Real-Time Data</h4>
                    <p>Live stock prices and market data via MarketStack API integration</p>
                </div>
                <div class="feature">
                    <h4>Advanced Analysis</h4>
                    <p>DCF, EPV, and Asset-based valuations with customizable business models</p>
                </div>
                <div class="feature">
                    <h4>Financial Health</h4>
                    <p>Comprehensive ratio analysis and business quality assessment</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const API_URL = '$apiUrl';
        
        function formatPrice(price, currency = 'USD') {
            if (!price) return 'N/A';
            try {
                const formatter = new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: currency,
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });
                return formatter.format(price);
            } catch (e) {
                return currency + ' ' + price.toFixed(2);
            }
        }
        
        function getRecommendationClass(recommendation) {
            if (!recommendation) return '';
            const rec = recommendation.toLowerCase();
            if (rec.includes('strong buy')) return 'strong-buy';
            if (rec.includes('buy')) return 'buy';
            if (rec.includes('hold')) return 'hold';
            if (rec.includes('sell') || rec.includes('avoid')) return 'avoid';
            return '';
        }
        
        async function loadWatchlist() {
            const content = document.getElementById('watchlist-content');
            content.innerHTML = '<div class="loading"><div class="spinner"></div><p style="margin-top: 20px; color: #6b7280;">Loading your watchlist...</p></div>';
            
            try {
                console.log('Fetching watchlist from:', API_URL + '/api/watchlist');
                const response = await axios.get(API_URL + '/api/watchlist');
                const data = response.data;
                console.log('Watchlist data:', data);
                
                if (data.items && data.items.length > 0) {
                    const stocksHtml = data.items.map(stock => {
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
                        
                        const lastUpdated = stock.last_updated ? 
                            '<p style="font-size: 12px; color: #9ca3af;">Updated: ' + 
                            new Date(stock.last_updated).toLocaleDateString() + '</p>' : '';
                        
                        return '<div class="stock-item" onclick="analyzeStock(\'' + stock.ticker + '\')">' +
                               '<div class="stock-content">' +
                               '<div class="stock-info">' +
                               '<h3>' + companyName + recommendation + '</h3>' +
                               '<p>' + stock.ticker + '</p>' +
                               lastUpdated +
                               '</div>' +
                               '<div class="stock-price">' +
                               '<div class="price">' + price + '</div>' +
                               priceChangeHtml +
                               '<div class="click-hint">Click to analyze →</div>' +
                               '</div>' +
                               '</div>' +
                               '</div>';
                    }).join('');
                    
                    content.innerHTML = '<div class="stock-grid">' + stocksHtml + '</div>';
                } else {
                    content.innerHTML = '<div class="empty-state">' +
                                      '<p>No stocks in your watchlist yet.</p>' +
                                      '<button class="btn btn-success" onclick="addStock()">' +
                                      'Add Your First Stock' +
                                      '</button>' +
                                      '</div>';
                }
            } catch (error) {
                console.error('Error loading watchlist:', error);
                const errorMessage = error.response?.data?.detail || error.message || 'Failed to load watchlist';
                content.innerHTML = '<div class="error">' +
                    '⚠️ ' + errorMessage +
                    '</div>' +
                    '<div style="text-align: center; padding: 20px;">' +
                    '<button class="btn" onclick="loadWatchlist()">Retry</button>' +
                    '</div>';
            }
        }
        
        function analyzeStock(ticker) {
            // Show a more sophisticated placeholder
            const modal = document.createElement('div');
            modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;';
            modal.innerHTML = '<div style="background: white; padding: 30px; border-radius: 12px; max-width: 400px; text-align: center;">' +
                '<h3 style="color: #111827; margin-bottom: 16px;">📈 ' + ticker + ' Analysis</h3>' +
                '<p style="color: #6b7280; margin-bottom: 20px;">Full stock analysis with DCF valuation, financial health scoring, and business quality assessment will be available soon.</p>' +
                '<button onclick="document.body.removeChild(this.parentElement.parentElement)" style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer;">Close</button>' +
                '</div>';
            document.body.appendChild(modal);
        }
        
        function addStock() {
            const ticker = prompt('Enter stock ticker (e.g., AAPL, GOOGL, MSFT):');
            if (ticker && ticker.trim()) {
                const cleanTicker = ticker.trim().toUpperCase();
                alert('Adding ' + cleanTicker + ' to watchlist - Feature coming soon!\\n\\nThis will integrate with the backend API to add stocks to your personal watchlist.');
            }
        }
        
        // Load watchlist on page load
        document.addEventListener('DOMContentLoaded', loadWatchlist);
    </script>
</body>
</html>
"@

# Create index.html
$indexHtml = @"
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
            max-width: 600px;
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
            margin-top: 30px;
            text-align: left;
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 10px;
        }
        .features h3 { color: #60a5fa; margin-bottom: 15px; }
        .features ul { list-style: none; padding: 0; }
        .features li { margin: 8px 0; opacity: 0.9; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Stock Analysis Platform</h1>
        <p>Professional stock analysis with real-time data, comprehensive financial metrics, and AI-powered insights</p>
        
        <a href="/watchlist.html" class="btn">🎯 View Watchlist</a>
        
        <div class="features">
            <h3>🚀 Key Features</h3>
            <ul>
                <li>📈 Real-time stock prices via MarketStack API</li>
                <li>💰 DCF, EPV, and Asset-based valuations</li>
                <li>🏥 Financial health scoring</li>
                <li>🎯 Business quality assessment</li>
                <li>📊 Interactive charts and analysis</li>
            </ul>
        </div>
        
        <script>
            setTimeout(() => { window.location.href = '/watchlist.html'; }, 4000);
        </script>
    </div>
</body>
</html>
"@

Write-Host "📄 Creating enhanced HTML files..." -ForegroundColor Yellow
$indexHtml | Out-File -FilePath "index.html" -Encoding UTF8
$watchlistHtml | Out-File -FilePath "watchlist.html" -Encoding UTF8

Write-Host "☁️ Uploading to S3..." -ForegroundColor Yellow
aws s3 cp index.html s3://$BucketName/index.html --profile $profile --content-type "text/html"
aws s3 cp watchlist.html s3://$BucketName/watchlist.html --profile $profile --content-type "text/html"

Remove-Item "index.html"
Remove-Item "watchlist.html"

$websiteUrl = "http://$BucketName.s3-website-$region.amazonaws.com"
Write-Host ""
Write-Host "🎉 Enhanced Watchlist Deployed!" -ForegroundColor Green
Write-Host "🔗 Website: $websiteUrl" -ForegroundColor Cyan
Write-Host "🔗 Watchlist: $websiteUrl/watchlist.html" -ForegroundColor Cyan