# Stock Analysis Tool

A web-based stock analysis tool that uses value investing principles to analyze stocks, focusing on calculating intrinsic value (fair value per share) and comparing it to current market price (cost per share) to determine margin of safety.

## 📊 Enhanced Financial Ratios System

The tool features a comprehensive financial ratios system that displays key metrics prominently on stock pages:

- **P/E, P/B, P/S Ratios** - Essential valuation metrics
- **ROE, Debt-to-Equity, Current Ratio** - Financial health indicators
- **Market Cap, Enterprise Value** - Market data
- **Color-coded indicators** for quick assessment
- **Real-time calculations** from financial statements

**📖 [View Complete Financial Ratios Documentation](docs/features/financial-ratios.md)**

## Architecture

- **Frontend**: Next.js 14+ (React, TypeScript)
- **Backend**: Enhanced AWS Lambda Function (Python)
- **Data Sources**: MarketStack API ready, Yahoo Finance fallback
- **Current Version**: Backend `4.0.0-marketstack`, Frontend with Financial Summary Cards

## Features

1. **Intrinsic Value Assessment** - Calculate true business worth through multiple valuation methods:
   - Discounted Cash Flow (DCF)
   - Earnings Power Value (EPV)
   - Asset-Based Valuation

2. **Margin of Safety** - Compare market price to intrinsic value (target: 30-50% discount)

3. **Business Quality** - Assess competitive moats, financial health, and management quality

4. **Comprehensive Analysis** - Financial health scores, business quality metrics, and investment recommendations

## Quick Start

### Current System (Enhanced Lambda)

The system now runs on an enhanced AWS Lambda function with comprehensive financial ratios:

**Backend**: Already deployed at `https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production`
- Version: `4.0.0-marketstack-{timestamp}`
- Features: Financial ratios, real price data, comprehensive analysis

**Frontend**: Run locally with:
```bash
cd frontend
npm install
npm run dev
```

### Key Endpoints
- `GET /api/watchlist` - Watchlist with financial ratios
- `GET /api/manual-data/{ticker}` - Comprehensive financial data
- `GET /api/analyze/{ticker}` - Full stock analysis
- `GET /health` - System status and version

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

4. Run the development server:
```bash
npm run dev
```

Frontend will be available at `http://localhost:3000`

## Usage

1. Open the frontend in your browser
2. Enter a stock ticker symbol (e.g., AAPL, MSFT, GOOGL)
3. View comprehensive analysis including:
   - Fair value vs current price
   - Margin of safety
   - Valuation breakdown
   - Financial health score
   - Business quality assessment
   - Investment recommendation

## API Endpoints

- `GET /api/analyze/{ticker}` - Full stock analysis
- `GET /api/quote/{ticker}` - Quick quote
- `GET /api/health` - Health check
- `POST /api/compare` - Compare multiple stocks

## Documentation

All documentation lives in the [docs/](docs/) directory:

- **[Documentation Index](docs/README.md)** - Full table of contents
- **[Development Guide](docs/development/guide.md)** - Setup, testing, and contributing
- **[Deployment Guide](docs/deployment/deployment.md)** - Environments, CI/CD, and rollback
- **[Lambda Deployment](docs/deployment/lambda-deployment.md)** - Hands-on Lambda deployment steps
- **[Analysis Weights Guide](docs/features/analysis-weights.md)** - Business type presets and weight configuration
- **[Financial Ratios System](docs/features/financial-ratios.md)** - Financial ratios documentation
- **Backend API docs**: `http://localhost:8000/docs` (Swagger UI)
- **Backend API docs**: `http://localhost:8000/redoc` (ReDoc)

## License

Private tool for personal use.
