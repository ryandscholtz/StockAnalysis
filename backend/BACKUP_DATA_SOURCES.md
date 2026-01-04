# Backup Data Sources Configuration

This document explains how to configure backup data sources to avoid Yahoo Finance rate limits.

## Available Backup Sources

### 1. Alpha Vantage (Recommended - Primary Backup)
- **Free Tier**: 5 API calls per minute, 500 calls per day
- **Sign up**: https://www.alphavantage.co/support/#api-key
- **API Key**: Get from https://www.alphavantage.co/support/#api-key
- **Environment Variable**: `ALPHA_VANTAGE_API_KEY`
- **Documentation**: https://www.alphavantage.co/documentation/
- **Note**: Already used for financial statements (income statement, balance sheet, cash flow). With this API key, it will also be used as the primary backup source for price data.

### 2. Financial Modeling Prep
- **Free Tier**: 250 requests/day
- **Sign up**: https://financialmodelingprep.com/developer/docs/
- **API Key**: Get from https://financialmodelingprep.com/developer/docs/
- **Environment Variable**: `FMP_API_KEY`

### 3. MarketStack
- **Free Tier**: 1,000 requests/month
- **Sign up**: https://marketstack.com/
- **API Key**: Get from https://marketstack.com/dashboard
- **Environment Variable**: `MARKETSTACK_API_KEY`

### ~~IEX Cloud (Deprecated)~~
- **Status**: Retired on August 31, 2024
- IEX Cloud has been removed from backup sources. Please use Alpha Vantage or other alternatives.

## Configuration

Add these to your `.env` file:

```bash
# Alpha Vantage (recommended - primary backup source)
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_api_key_here

# Financial Modeling Prep (optional)
FMP_API_KEY=your_fmp_api_key_here

# MarketStack (optional)
MARKETSTACK_API_KEY=your_marketstack_api_key_here
```

## How It Works

1. **Primary Source**: Yahoo Finance (yfinance library)
2. **Fallback Chain**: When Yahoo Finance fails or is rate-limited:
   - Tries Alpha Vantage (primary backup)
   - Tries Financial Modeling Prep
   - Tries MarketStack
   - Returns None if all sources fail

## Rate Limit Handling

The system automatically:
- Detects Yahoo Finance rate limits (429 errors)
- Switches to backup sources seamlessly
- Logs which source was used for debugging
- Falls back gracefully if all sources are exhausted

## Getting API Keys

### Alpha Vantage (Recommended - Primary Backup)
1. Go to https://www.alphavantage.co/support/#api-key
2. Sign up for free account (or use existing account)
3. Get API key from the support page
4. Add to `.env` as `ALPHA_VANTAGE_API_KEY`
5. **Note**: Alpha Vantage is already used for financial statements (income statement, balance sheet, cash flow). With this API key, it will also be used as the primary backup source for price data.

**Rate Limits**: Free tier allows 5 API calls per minute and 500 calls per day. The system will automatically respect these limits.

### Financial Modeling Prep
1. Go to https://financialmodelingprep.com/developer/docs/
2. Sign up for free account
3. Get API key from dashboard
4. Add to `.env` as `FMP_API_KEY`

### MarketStack
1. Go to https://marketstack.com/
2. Sign up for free account
3. Get API key from dashboard
4. Add to `.env` as `MARKETSTACK_API_KEY`

## Testing

To test backup sources, you can temporarily disable Yahoo Finance or hit rate limits. The system will automatically use backup sources.

Check logs to see which source was used:
```
Got price from Alpha Vantage: 150.25
Got company info from Financial Modeling Prep
```

