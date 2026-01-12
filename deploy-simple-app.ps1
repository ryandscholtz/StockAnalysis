# Deploy simple application to S3
$BucketName = "stock-analysis-app-production"
$region = "eu-west-1"
$profile = "Cerebrum"
$apiUrl = "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production"

Write-Host "🚀 Deploying Application..." -ForegroundColor Cyan

# Create a simple watchlist HTML page
$watchlistHtml = @"
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>Stock Watchlist - Analysis Platform</title>
    <style>
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0; 
            padding: 20px; 
            background: #f8fafc;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { color: #111827; margin-bottom: 30px; }
        .card { 
            background: white; 
            padding: 30px; 
            border-radius: 12px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .stock-item {
            padding: 20px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            margin-bottom: 15px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .stock-item:hover {
            background-color: #f3f4f6;
            border-color: #3b82f6;
        }
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 200px;
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
    <div class="container">
        <h1 class="header">📊 Stock Analysis Watchlist</h1>
        <div class="card">
            <h2 style="color: #374151; margin-bottom: 20px;">Your Stocks</h2>
            <div id="watchlist-content">
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Loading watchlist...</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        const API_URL = '$apiUrl';
        
        async function loadWatchlist() {
            try {
                const response = await fetch(API_URL + '/api/watchlist');
                const data = await response.json();
                
                const content = document.getElementById('watchlist-content');
                
                if (data.items && data.items.length > 0) {
                    content.innerHTML = data.items.map(stock => {
                        const companyName = stock.company_name || (stock.ticker + ' Corporation');
                        const price = stock.current_price ? ('$' + stock.current_price.toFixed(2)) : 'Price N/A';
                        
                        return '<div class="stock-item" onclick="analyzeStock(\'' + stock.ticker + '\')">' +
                               '<div style="display: flex; justify-content: space-between; align-items: center;">' +
                               '<div>' +
                               '<h3 style="margin: 0 0 5px 0; color: #111827;">' + companyName + '</h3>' +
                               '<p style="margin: 0; color: #6b7280; font-size: 14px;">' + stock.ticker + '</p>' +
                               '</div>' +
                               '<div style="text-align: right;">' +
                               '<div style="font-size: 18px; font-weight: bold; color: #111827;">' + price + '</div>' +
                               '<div style="font-size: 12px; color: #6b7280;">Click to analyze →</div>' +
                               '</div>' +
                               '</div>' +
                               '</div>';
                    }).join('');
                } else {
                    content.innerHTML = '<div style="text-align: center; padding: 40px; color: #6b7280;">' +
                                      '<p>No stocks in your watchlist yet.</p>' +
                                      '<button onclick="addStock()" style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer;">' +
                                      'Add Your First Stock' +
                                      '</button>' +
                                      '</div>';
                }
            } catch (error) {
                console.error('Error loading watchlist:', error);
                document.getElementById('watchlist-content').innerHTML = 
                    '<div style="text-align: center; padding: 40px;">' +
                    '<h3 style="color: #ef4444;">Unable to load watchlist</h3>' +
                    '<p style="color: #6b7280;">Please check your connection and try again.</p>' +
                    '<button onclick="location.reload()" style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer;">Retry</button>' +
                    '</div>';
            }
        }
        
        function analyzeStock(ticker) {
            alert('Analysis for ' + ticker + ' - Feature coming soon!');
        }
        
        function addStock() {
            const ticker = prompt('Enter stock ticker (e.g., AAPL):');
            if (ticker) {
                alert('Adding ' + ticker + ' - Feature coming soon!');
            }
        }
        
        // Load watchlist on page load
        loadWatchlist();
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
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Stock Analysis Platform</h1>
        <p>Professional stock analysis with real-time data and comprehensive financial metrics</p>
        <a href="/watchlist.html" class="btn">🎯 View Watchlist</a>
        <script>
            setTimeout(() => { window.location.href = '/watchlist.html'; }, 3000);
        </script>
    </div>
</body>
</html>
"@

# Write files and upload
Write-Host "📄 Creating HTML files..." -ForegroundColor Yellow
$indexHtml | Out-File -FilePath "index.html" -Encoding UTF8
$watchlistHtml | Out-File -FilePath "watchlist.html" -Encoding UTF8

Write-Host "☁️ Uploading to S3..." -ForegroundColor Yellow
aws s3 cp index.html s3://$BucketName/index.html --profile $profile --content-type "text/html"
aws s3 cp watchlist.html s3://$BucketName/watchlist.html --profile $profile --content-type "text/html"

# Clean up
Remove-Item "index.html"
Remove-Item "watchlist.html"

$websiteUrl = "http://$BucketName.s3-website-$region.amazonaws.com"
Write-Host ""
Write-Host "🎉 Application Deployed!" -ForegroundColor Green
Write-Host "🔗 Website: $websiteUrl" -ForegroundColor Cyan
Write-Host "🔗 Watchlist: $websiteUrl/watchlist.html" -ForegroundColor Cyan