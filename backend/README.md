# Stock Analysis Backend API

FastAPI backend for the Stock Analysis Tool using value investing principles.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file (optional):
```bash
cp .env.example .env
# Edit .env and add your API keys if desired:
# - FRED_API_KEY (optional - for risk-free rate)
# - ALPHA_VANTAGE_API_KEY (optional - for additional financial data)
#   Get free key at: https://www.alphavantage.co/support/#api-key
# - FMP_API_KEY (optional - for Financial Modeling Prep API)
#   Get free key at: https://financialmodelingprep.com/developer/docs/
#   Free tier: 250 requests/day
```

4. Run the server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

- `GET /api/analyze/{ticker}` - Full stock analysis
- `GET /api/quote/{ticker}` - Quick quote
- `GET /api/health` - Health check
- `POST /api/compare` - Compare multiple stocks

## Documentation

API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

