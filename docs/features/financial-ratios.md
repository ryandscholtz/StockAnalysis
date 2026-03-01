# Financial Ratios System Documentation

## Overview

The Stock Analysis Tool now features a comprehensive financial ratios system that displays key financial metrics prominently on stock pages. This system calculates and displays essential investment ratios without requiring complex API integrations.

## System Architecture

### Backend: Enhanced Lambda Function
- **File**: `simple-marketstack-lambda.py`
- **Version**: `4.0.0-marketstack-{YYMMDD-HHMM}` (GMT+2 timestamps)
- **Handler**: `simple-marketstack-lambda.lambda_handler`

### Frontend: Financial Summary Card
- **File**: `frontend/app/watchlist/[ticker]/page.tsx`
- **Component**: Financial Summary Card (displays at top of stock pages)
- **Data Source**: `/api/manual-data/{ticker}` endpoint

## Financial Metrics Displayed

### 1. Valuation Ratios
- **P/E Ratio** (Price-to-Earnings)
  - Formula: `Current Price / (Net Income / Shares Outstanding)`
  - Color Coding: Green < 20, Blue < 30, Yellow ≥ 30
  
- **P/B Ratio** (Price-to-Book)
  - Formula: `Current Price / (Shareholders Equity / Shares Outstanding)`
  - Color Coding: Green < 2, Blue < 4, Yellow ≥ 4

- **P/S Ratio** (Price-to-Sales)
  - Formula: `Current Price / (Revenue / Shares Outstanding)`
  - Used in analysis components

### 2. Financial Health Metrics
- **ROE** (Return on Equity)
  - Formula: `(Net Income / Shareholders Equity) * 100`
  - Color Coding: Green > 15%, Blue > 10%, Yellow ≤ 10%

- **Debt-to-Equity Ratio**
  - Formula: `Total Debt / Shareholders Equity`
  - Color Coding: Green < 0.5, Blue < 1.0, Yellow ≥ 1.0

- **Current Ratio**
  - Formula: `Current Assets / Current Liabilities`
  - Color Coding: Green > 2, Blue > 1, Yellow ≤ 1

### 3. Market Data
- **Market Cap**: `Current Price * Shares Outstanding`
- **Enterprise Value**: `Market Cap + Total Debt`
- **Shares Outstanding**: From financial statements

## Data Structure

### Backend Response Format (`/api/manual-data/{ticker}`)

```json
{
  "ticker": "GOOGL",
  "company_name": "Alphabet Inc.",
  "current_price": 2800.50,
  "financial_data": {
    "income_statement": {
      "revenue": 307394000000,
      "net_income": 73795000000
    },
    "balance_sheet": {
      "total_assets": 402392000000,
      "total_debt": 28810000000,
      "shareholders_equity": 283893000000
    },
    "cashflow": {
      "operating_cash_flow": 101395000000,
      "free_cash_flow": 69495000000
    },
    "key_metrics": {
      "latest": {
        "pe_ratio": 48.6,
        "pb_ratio": 12.6,
        "ps_ratio": 11.7,
        "debt_to_equity": 0.1,
        "current_ratio": 2.93,
        "roe": 0.26,
        "market_cap": 3584640000000,
        "shares_outstanding": 12800000000,
        "enterprise_value": 3613450000000
      }
    }
  },
  "has_data": true
}
```

### Analysis Response Format (`/api/analyze/{ticker}`)

```json
{
  "ticker": "GOOGL",
  "current_price": 2800.50,
  "fair_value": 126.84,
  "recommendation": "Buy",
  "priceRatios": {
    "priceToEarnings": 48.6,
    "priceToBook": 12.6,
    "priceToSales": 11.7
  },
  "growthMetrics": {
    "roe": 26.0,
    "gross_margin": 59.1,
    "operating_margin": 27.4,
    "net_margin": 24.0
  },
  "financial_health": {
    "score": 9,
    "debt_to_equity": 0.1,
    "current_ratio": 2.93,
    "roe": 26.0
  }
}
```

## Available Stock Data

### Current Sample Data
- **AAPL**: Apple Inc. - P/E 23.4, P/B 46.2, ROE 196.9%, Market Cap $2.34T
- **GOOGL**: Alphabet Inc. - P/E 48.6, P/B 12.6, ROE 26.0%, Market Cap $3.58T
- **MSFT**: Microsoft Corp. - P/E 35.5, P/B 15.2, ROE 42.7%, Market Cap $3.13T
- **TSLA**: Tesla Inc. - P/E 39.1, P/B 9.3, ROE 23.9%, Market Cap $586B

## API Endpoints

### Core Endpoints
- **`GET /api/watchlist`** - Returns watchlist with basic ratios in notes
- **`GET /api/watchlist/{ticker}`** - Individual stock with comprehensive ratios
- **`GET /api/watchlist/live-prices`** - Live prices with key ratios
- **`GET /api/manual-data/{ticker}`** - Financial data with calculated ratios
- **`GET /api/analyze/{ticker}`** - Full analysis with all metrics
- **`GET /api/version`** - Backend version with deployment timestamp

### Health Check
- **`GET /health`** - System status with version and features list

## Frontend Components

### 1. Financial Summary Card
**Location**: Top of individual stock pages
**Displays**: P/E, P/B, ROE, Debt-to-Equity, Market Cap, Current Ratio
**Features**: 
- Color-coded values for quick assessment
- Responsive grid layout
- Conditional rendering (only shows if data available)

### 2. Analysis Components (After "Run Analysis")
- **PriceRatios**: P/E, P/B, P/S, P/FCF, EV/EBITDA
- **GrowthMetrics**: ROE, profit margins
- **FinancialHealth**: Debt ratios, liquidity ratios
- **ValuationStatus**: Fair value vs current price

## Deployment

### Backend Deployment
```powershell
# Compress the Lambda function
Compress-Archive -Path simple-marketstack-lambda.py -DestinationPath simple-marketstack-lambda.zip -Force

# Deploy to AWS Lambda
aws lambda update-function-code --function-name stock-analysis-api-production --zip-file fileb://simple-marketstack-lambda.zip --profile Cerebrum --region eu-west-1

# Update handler (if needed)
aws lambda update-function-configuration --function-name stock-analysis-api-production --handler simple-marketstack-lambda.lambda_handler --profile Cerebrum --region eu-west-1
```

### Frontend Changes
The financial summary card is automatically included in the stock detail page. No separate deployment needed - changes are reflected when the Next.js app rebuilds.

## Testing

### Backend Testing
```bash
# Test health endpoint
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/health

# Test financial data
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/manual-data/GOOGL

# Test analysis
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/analyze/AAPL
```

### Frontend Testing
1. Navigate to any stock page (e.g., `/watchlist/GOOGL`)
2. Financial summary card should appear at the top
3. Click "Run Analysis" to see detailed analysis components

## Color Coding System

### P/E Ratio
- 🟢 **Green** (< 20): Undervalued or mature company
- 🔵 **Blue** (20-30): Fairly valued
- 🟡 **Yellow** (> 30): Potentially overvalued or high growth

### P/B Ratio
- 🟢 **Green** (< 2): Good value relative to book value
- 🔵 **Blue** (2-4): Moderate valuation
- 🟡 **Yellow** (> 4): Premium valuation

### ROE (Return on Equity)
- 🟢 **Green** (> 15%): Excellent profitability
- 🔵 **Blue** (10-15%): Good profitability
- 🟡 **Yellow** (< 10%): Concerning profitability

### Debt-to-Equity
- 🟢 **Green** (< 0.5): Conservative debt levels
- 🔵 **Blue** (0.5-1.0): Moderate debt levels
- 🟡 **Yellow** (> 1.0): High debt levels

### Current Ratio
- 🟢 **Green** (> 2): Strong liquidity
- 🔵 **Blue** (1-2): Adequate liquidity
- 🟡 **Yellow** (< 1): Liquidity concerns

## Future Enhancements

### Potential Improvements
1. **Real MarketStack Integration**: Replace sample data with live API calls
2. **More Tickers**: Expand beyond current 4 stocks
3. **Historical Data**: Show ratio trends over time
4. **Industry Comparisons**: Compare ratios to industry averages
5. **Custom Alerts**: Notify when ratios hit certain thresholds

### Adding New Stocks
To add a new stock to the system:

1. **Update `_get_stock_data_with_ratios()` in `simple-marketstack-lambda.py`**
2. **Add financial data and calculated ratios**
3. **Redeploy Lambda function**
4. **Test endpoints**

### Modifying Ratios
To add new financial ratios:

1. **Backend**: Add calculation in `_get_stock_data_with_ratios()`
2. **Frontend**: Add display in Financial Summary Card
3. **Update color coding logic**
4. **Update documentation**

## Troubleshooting

### Common Issues

**Financial Summary Card Not Showing**
- Check if `financialData?.financial_data?.key_metrics?.latest` exists
- Verify API endpoint returns correct structure
- Check browser console for errors

**Ratios Showing as "N/A"**
- Verify financial data contains required fields
- Check calculation logic in backend
- Ensure data types are numeric

**Color Coding Not Working**
- Check if values are within expected ranges
- Verify color coding logic in frontend component
- Ensure values are not null/undefined

### Debug Commands
```bash
# Check backend version
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/version

# Check specific stock data
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/manual-data/AAPL | jq .

# Test analysis endpoint
curl https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production/api/analyze/GOOGL | jq .priceRatios
```

## Version History

- **v4.0.0-marketstack**: Enhanced Lambda with comprehensive financial ratios
- **v3.0.0-enhanced**: Basic Lambda with analysis functionality  
- **v2.0.0-watchlist-fix**: Simple Lambda with watchlist endpoints
- **v1.x**: Original FastAPI implementation

---

*Last Updated: January 11, 2026*
*Backend Version: 4.0.0-marketstack-260111-1347*