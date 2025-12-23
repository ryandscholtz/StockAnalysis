# Stock Analysis Tool - Charlie Munger Methodology

A web-based stock analysis tool that analyzes stocks using Charlie Munger's investment philosophy, focusing on calculating intrinsic value (fair value per share) and comparing it to current market price (cost per share) to determine margin of safety.

## Architecture

- **Frontend**: Next.js 14+ (React, TypeScript)
- **Backend**: Python FastAPI
- **Data Sources**: Yahoo Finance (yfinance), Alpha Vantage, FRED API

## Features

1. **Intrinsic Value Assessment** - Calculate true business worth through multiple valuation methods:
   - Discounted Cash Flow (DCF)
   - Earnings Power Value (EPV)
   - Asset-Based Valuation

2. **Margin of Safety** - Compare market price to intrinsic value (target: 30-50% discount)

3. **Business Quality** - Assess competitive moats, financial health, and management quality

4. **Comprehensive Analysis** - Financial health scores, business quality metrics, and investment recommendations

## Getting Started

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the server:
```bash
uvicorn app.main:app --reload
```

Backend will be available at `http://localhost:8000`

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

- Backend API docs: `http://localhost:8000/docs` (Swagger UI)
- Backend API docs: `http://localhost:8000/redoc` (ReDoc)

## License

Private tool for personal use.
