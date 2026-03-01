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

The API supports any stock ticker. Pass any valid ticker symbol to the endpoints:

```bash
GET /api/analyze/{ticker}       # e.g. /api/analyze/NVDA
GET /api/manual-data/{ticker}   # e.g. /api/manual-data/BHP
GET /api/watchlist/{ticker}     # e.g. /api/watchlist/AMZN
```

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
- [Financial Ratios System](../features/financial-ratios.md) - Complete system documentation
- [Lambda Deployment](../deployment/lambda-deployment.md) - Deployment procedures
- [Project README](../../README.md) - Project overview

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

---

*Quick Reference - Updated: February 2026*