# Quick Reference Guide

## 🚀 Current System Status

**Backend**: `4.0.0-marketstack-260111-1347` (Enhanced Lambda with Financial Ratios)
**Frontend**: Next.js with Financial Summary Cards
**API Base**: `https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production`

## 📊 Available Financial Metrics

### Displayed on Stock Pages
- **P/E Ratio**: Price-to-Earnings (valuation)
- **P/B Ratio**: Price-to-Book (asset value)
- **ROE**: Return on Equity (profitability)
- **Debt-to-Equity**: Financial leverage
- **Market Cap**: Total company value
- **Current Ratio**: Liquidity strength

### Color Coding
- 🟢 **Green**: Good/Healthy values
- 🔵 **Blue**: Moderate/Acceptable values  
- 🟡 **Yellow**: Concerning/High values

## 🎯 Supported Stocks

| Ticker | Company | P/E | P/B | ROE | Market Cap |
|--------|---------|-----|-----|-----|------------|
| AAPL | Apple Inc. | 23.4 | 46.2 | 196.9% | $2.34T |
| GOOGL | Alphabet Inc. | 48.6 | 12.6 | 26.0% | $3.58T |
| MSFT | Microsoft Corp. | 35.5 | 15.2 | 42.7% | $3.13T |
| TSLA | Tesla Inc. | 39.1 | 9.3 | 23.9% | $586B |

## 🔗 Key API Endpoints

### Core Data
```bash
# Health check
GET /health

# Version info  
GET /api/version

# Watchlist with ratios
GET /api/watchlist

# Individual stock data
GET /api/watchlist/{ticker}

# Financial data with ratios
GET /api/manual-data/{ticker}

# Full analysis
GET /api/analyze/{ticker}
```

### Example Responses
```bash
# Quick test
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health

# Get GOOGL financial data
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/manual-data/GOOGL
```

## 🛠️ Quick Deployment

### Backend Update
```powershell
# 1. Package
Compress-Archive -Path simple-marketstack-lambda.py -DestinationPath simple-marketstack-lambda.zip -Force

# 2. Deploy
aws lambda update-function-code --function-name stock-analysis-api-production --zip-file fileb://simple-marketstack-lambda.zip --profile Cerebrum --region eu-west-1

# 3. Test
Invoke-RestMethod -Uri "https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health" -Method GET
```

### Frontend Development
```bash
cd frontend
npm run dev
# Access: http://localhost:3000
```

## 🔍 Troubleshooting

### Common Checks
```bash
# Backend version
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/version

# Test specific stock
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/manual-data/AAPL

# Check financial ratios structure
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/manual-data/GOOGL | jq .financial_data.key_metrics.latest
```

### Frontend Issues
- **Financial card not showing**: Check browser console, verify API response
- **Ratios showing N/A**: Check if `key_metrics.latest` exists in API response
- **Colors not working**: Verify values are numeric, not null

## 📁 Key Files

### Backend
- `simple-marketstack-lambda.py` - Main Lambda function
- `test-enhanced-financial-ratios.js` - Test script

### Frontend  
- `frontend/app/watchlist/[ticker]/page.tsx` - Stock detail page with financial summary
- `frontend/components/PriceRatios.tsx` - Analysis ratios component
- `frontend/components/FinancialDataDisplay.tsx` - Financial data sections

### Documentation
- `FINANCIAL_RATIOS_SYSTEM.md` - Complete system documentation
- `DEPLOYMENT_GUIDE.md` - Deployment procedures
- `README.md` - Project overview

## 🎨 UI Components

### Financial Summary Card
**Location**: Top of stock pages
**Shows**: 6 key metrics in responsive grid
**Features**: Color-coded values, conditional rendering

### Analysis Components (after "Run Analysis")
- **PriceRatios**: P/E, P/B, P/S ratios
- **GrowthMetrics**: ROE, profit margins  
- **FinancialHealth**: Debt and liquidity ratios
- **ValuationStatus**: Fair value vs current price

## 🔮 Future Enhancements

### Ready for Implementation
- **Real MarketStack API**: Replace sample data with live prices
- **More Stocks**: Expand beyond current 4 tickers
- **Historical Trends**: Show ratio changes over time
- **Industry Comparisons**: Compare to sector averages

### Development Priorities
1. MarketStack API integration
2. Additional stock coverage
3. Historical data visualization
4. Mobile responsiveness improvements
5. Performance optimizations

---

*Quick Reference - Updated: January 11, 2026*