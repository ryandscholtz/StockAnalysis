"""
Stock Data Lambda - Handles stock price data and market information
Dependencies: stdlib only (urllib), optional yfinance
"""
import json
import os
import boto3
import concurrent.futures
from datetime import datetime
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import URLError

# Optional imports with fallbacks
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


# Authoritative currency overrides by ticker suffix.
# APIs often return the exchange's base currency (ZAR) but JSE trades in cents (ZAC).
_TICKER_CURRENCY_OVERRIDE: dict[str, str] = {
    '.XJSE': 'ZAC',   # Johannesburg Stock Exchange — prices quoted in cents
}


def _resolve_currency(ticker: str, api_currency: str | None) -> str:
    """Return the correct currency for a ticker, overriding API values where known."""
    upper = ticker.upper()
    for suffix, currency in _TICKER_CURRENCY_OVERRIDE.items():
        if upper.endswith(suffix):
            return currency
    return api_currency or 'USD'


def _yahoo_symbol(ticker: str) -> str:
    """Convert MarketStack/XJSE style tickers to Yahoo Finance format"""
    # BEL.XJSE -> BEL.JO, PPE.XJSE -> PPE.JO
    if ticker.upper().endswith('.XJSE'):
        return ticker[:-5] + '.JO'
    return ticker


def get_ticker_data_yahoo(ticker: str) -> dict:
    """Get stock ticker data from Yahoo Finance (no API key required)"""
    from urllib.request import Request

    yahoo_symbol = _yahoo_symbol(ticker)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}?interval=1d&range=1d"

    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())

        result = data.get('chart', {}).get('result', [])
        if not result:
            return {'error': f'No data for {yahoo_symbol}'}

        meta = result[0].get('meta', {})
        price = meta.get('regularMarketPrice') or meta.get('previousClose') or 0
        currency = meta.get('currency', 'USD')
        name = meta.get('longName') or meta.get('shortName') or ticker

        return {
            'ticker': ticker,
            'name': name,
            'price': price,
            'currentPrice': price,
            'currency': _resolve_currency(ticker, currency),
            'exchange': meta.get('exchangeName', ''),
            'source': 'yahoo_finance'
        }
    except URLError as e:
        return {'error': str(e)}
    except Exception as e:
        return {'error': str(e)}


def get_ticker_data_marketstack(ticker: str) -> dict:
    """Get stock ticker data from MarketStack paid API (HTTPS)"""
    api_key = os.getenv('MARKETSTACK_API_KEY', '')
    if not api_key:
        return {'error': 'MARKETSTACK_API_KEY not configured'}

    # MarketStack uses exchange suffixes differently: BEL.XJSE stays as-is
    # For EOD latest data
    try:
        url = f"https://api.marketstack.com/v1/eod/latest?{urlencode({'access_key': api_key, 'symbols': ticker})}"
        data = _urllib_get(url)

        items = data.get('data', [])
        if not items:
            return {'error': f'No data for {ticker}'}

        item = items[0] if isinstance(items, list) else items
        price = item.get('close') or item.get('adj_close') or 0

        # Fetch ticker info for company name and currency
        name = ticker
        currency = 'USD'
        try:
            info_url = f"https://api.marketstack.com/v1/tickers/{ticker}?{urlencode({'access_key': api_key})}"
            info_data = _urllib_get(info_url)
            name = info_data.get('name') or ticker
            # currency_code lives under stock_exchange on the tickers endpoint
            exchange_info = info_data.get('stock_exchange') or {}
            currency = exchange_info.get('currency_code') or 'USD'
        except Exception:
            pass

        return {
            'ticker': ticker,
            'name': name,
            'price': price,
            'currentPrice': price,
            'currency': _resolve_currency(ticker, currency),
            'exchange': item.get('exchange', ''),
            'source': 'marketstack'
        }
    except Exception as e:
        return {'error': str(e)}


def get_ticker_data(ticker: str) -> dict:
    """Get stock ticker data.
    For tickers with known exchange overrides (e.g. JSE), Yahoo Finance is tried
    first because it returns accurate real-time prices. MarketStack EOD data for
    these exchanges is often stale or incorrect.
    For all other tickers, MarketStack (paid) is tried first, with Yahoo as fallback.
    """
    upper = ticker.upper()
    use_yahoo_first = any(upper.endswith(s) for s in _TICKER_CURRENCY_OVERRIDE)

    if use_yahoo_first:
        yf_data = get_ticker_data_yahoo(ticker)
        if 'error' not in yf_data:
            return {'statusCode': 200, 'body': json.dumps(yf_data)}

    # MarketStack (paid plan, HTTPS)
    ms_data = get_ticker_data_marketstack(ticker)
    if 'error' not in ms_data:
        return {
            'statusCode': 200,
            'body': json.dumps(ms_data)
        }

    # Fall back to Yahoo Finance
    if not use_yahoo_first:
        yf_data = get_ticker_data_yahoo(ticker)
        if 'error' not in yf_data:
            return {
                'statusCode': 200,
                'body': json.dumps(yf_data)
            }

    return {
        'statusCode': 503,
        'body': json.dumps({
            'error': 'Stock data unavailable',
            'marketstack_error': ms_data.get('error', ''),
            'yahoo_error': yf_data.get('error', '')
        })
    }


def _urllib_get(url: str) -> dict:
    """Simple urllib GET helper"""
    from urllib.request import Request
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {'error': str(e)}


def search_stocks(query: str) -> dict:
    """Search for stocks using Yahoo Finance quote search"""
    try:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={urlencode({'q': query})}&quotesCount=10&newsCount=0"
        data = _urllib_get(url)

        quotes = data.get('quotes', [])
        results = []
        for item in quotes:
            if item.get('quoteType') in ('EQUITY', 'ETF'):
                results.append({
                    'symbol': item.get('symbol', ''),
                    'name': item.get('longname') or item.get('shortname') or '',
                    'exchange': item.get('exchDisp') or item.get('exchange') or ''
                })

        if results:
            return {
                'statusCode': 200,
                'body': json.dumps({'results': results})
            }
    except Exception:
        pass

    # Fallback: try MarketStack for search
    api_key = os.getenv('MARKETSTACK_API_KEY', '')
    if not api_key:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Search unavailable'})
        }

    try:
        ms_url = f"http://api.marketstack.com/v1/tickers?{urlencode({'access_key': api_key, 'search': query, 'limit': 10})}"
        data = _urllib_get(ms_url)

        results = []
        for item in data.get('data', []):
            results.append({
                'symbol': item.get('symbol', ''),
                'name': item.get('name', ''),
                'exchange': item.get('stock_exchange', {}).get('acronym', '')
            })

        return {
            'statusCode': 200,
            'body': json.dumps({'results': results})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# ---------------------------------------------------------------------------
# Explore Stocks – market/exchange browser
# ---------------------------------------------------------------------------

MARKET_TICKERS = {
    "SP500": {
        "name": "S&P 500",
        "description": "Top S&P 500 companies by market cap",
        "region": "US",
        "tickers": [
            "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK-B", "LLY", "JPM",
            "V", "UNH", "XOM", "MA", "AVGO", "JNJ", "HD", "PG", "COST", "ABBV",
            "MRK", "CVX", "KO", "WMT", "PEP", "BAC", "CRM", "NFLX", "TMO", "ORCL",
            "AMD", "ABT", "ACN", "LIN", "MCD", "DHR", "CSCO", "TXN", "NEE", "PM",
            "ADBE", "WFC", "MS", "RTX", "INTU", "DIS", "BMY", "UPS", "AMGN", "LOW",
        ],
    },
    "NASDAQ100": {
        "name": "NASDAQ 100",
        "description": "Top NASDAQ 100 technology & growth companies",
        "region": "US",
        "tickers": [
            "AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "GOOGL", "GOOG", "AVGO", "COST",
            "NFLX", "TMUS", "AMD", "CSCO", "ADBE", "PEP", "TXN", "QCOM", "HON", "INTU",
            "AMAT", "AMGN", "ISRG", "MU", "BKNG", "LRCX", "REGN", "ADI", "VRTX", "PANW",
            "KLAC", "SNPS", "MRVL", "CDNS", "GILD", "SBUX", "ADP", "MDLZ", "PYPL", "CTAS",
            "ABNB", "ORLY", "FTNT", "MELI", "MNST", "CRWD", "PCAR", "KDP", "INTC", "ASML",
        ],
    },
    "DOW30": {
        "name": "Dow Jones 30",
        "description": "Dow Jones Industrial Average – 30 blue-chip stocks",
        "region": "US",
        "tickers": [
            "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW",
            "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM",
            "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT",
        ],
    },
    "NYSE": {
        "name": "NYSE",
        "description": "Popular New York Stock Exchange stocks",
        "region": "US",
        "tickers": [
            "JPM", "BAC", "V", "JNJ", "WMT", "PG", "XOM", "CVX", "KO", "PEP",
            "MCD", "DIS", "MS", "GS", "WFC", "C", "ABT", "LLY", "UNH", "PFE",
            "MRK", "ABBV", "TMO", "HD", "NKE", "TGT", "LOW", "CRM", "AXP", "MA",
            "CAT", "BA", "HON", "MMM", "UPS", "GE", "NEE", "DUK", "AMT", "PLD",
            "XOM", "COP", "EOG", "BRK-B", "RTX", "IBM", "T", "VZ", "FDX", "SLB",
        ],
    },
    "NASDAQ": {
        "name": "NASDAQ",
        "description": "Popular NASDAQ-listed stocks",
        "region": "US",
        "tickers": [
            "AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "GOOGL", "GOOG", "NFLX", "AMD",
            "INTC", "CSCO", "ADBE", "PYPL", "INTU", "QCOM", "TXN", "HON", "AMGN", "SBUX",
            "COST", "PEP", "TMUS", "AVGO", "ISRG", "MU", "LRCX", "REGN", "GILD", "VRTX",
            "PANW", "CRWD", "FTNT", "ABNB", "MELI", "BKNG", "ORLY", "MNST", "KDP", "MDLZ",
            "ADP", "CTAS", "CDNS", "SNPS", "PCAR", "KLAC", "AMAT", "MRVL", "ADI", "LYFT",
        ],
    },
    "FTSE100": {
        "name": "FTSE 100",
        "description": "London Stock Exchange – top 100 UK companies",
        "region": "UK",
        "tickers": [
            "AZN.L", "SHEL.L", "HSBA.L", "ULVR.L", "BP.L", "BATS.L", "GSK.L", "RIO.L",
            "DGE.L", "REL.L", "BA.L", "LSEG.L", "PRU.L", "IMB.L", "NG.L", "VOD.L",
            "BT-A.L", "LLOY.L", "BARC.L", "NWG.L", "STAN.L", "AAL.L", "ANTO.L", "ABF.L",
            "CNA.L", "SSE.L", "WPP.L", "HLN.L", "MNDI.L", "RKT.L",
        ],
    },
    "ASX200": {
        "name": "ASX 200",
        "description": "Australian Securities Exchange – top 200 Australian companies",
        "region": "AU",
        "tickers": [
            "BHP.AX", "CSL.AX", "CBA.AX", "NAB.AX", "WBC.AX", "ANZ.AX", "WES.AX",
            "MQG.AX", "RIO.AX", "TLS.AX", "WOW.AX", "FMG.AX", "AMC.AX",
            "ALL.AX", "REA.AX", "QBE.AX", "SUN.AX", "IAG.AX", "MPL.AX", "ORG.AX",
        ],
    },
    "TSX": {
        "name": "TSX",
        "description": "Toronto Stock Exchange – top Canadian companies",
        "region": "CA",
        "tickers": [
            "RY.TO", "TD.TO", "BNS.TO", "BMO.TO", "CM.TO", "ENB.TO", "CNR.TO",
            "TRP.TO", "SU.TO", "ABX.TO", "MFC.TO", "SLF.TO", "CP.TO", "BCE.TO",
            "T.TO", "CNQ.TO", "PPL.TO", "ATD.TO", "GWO.TO", "AEM.TO",
        ],
    },
    "DAX": {
        "name": "DAX 40",
        "description": "Frankfurt Stock Exchange – top 40 German companies",
        "region": "DE",
        "tickers": [
            "SAP.DE", "SIE.DE", "ALV.DE", "MBG.DE", "DTE.DE", "BAYN.DE", "BMW.DE",
            "VOW3.DE", "MUV2.DE", "DB1.DE", "RWE.DE", "BAS.DE", "MRK.DE", "HEI.DE",
            "ADS.DE", "IFX.DE", "LIN.DE", "EOAN.DE", "HEN3.DE", "DHER.DE",
        ],
    },
    "NIKKEI": {
        "name": "Nikkei 225",
        "description": "Tokyo Stock Exchange – top Japanese companies",
        "region": "JP",
        "tickers": [
            "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "8316.T", "6902.T",
            "9432.T", "9433.T", "4063.T", "6954.T", "7974.T", "8035.T", "4519.T",
            "6367.T", "5108.T", "4661.T", "9022.T", "8591.T", "6098.T",
        ],
    },
}

# In-process cache: {market_id: {"data": [...], "timestamp": datetime}}
_explore_cache = {}
_EXPLORE_CACHE_TTL = 900  # 15 minutes


def _fetch_single_stock_explore(ticker_symbol):
    """Fetch comprehensive stock info for explore page using yfinance."""
    if not YFINANCE_AVAILABLE:
        return None
    try:
        import yfinance as yf
        t = yf.Ticker(ticker_symbol)
        info = t.info
        if not info or len(info) < 5:
            return None

        price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose")
        )
        if not price:
            return None

        prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
        change = info.get("regularMarketChange")
        change_pct = info.get("regularMarketChangePercent")
        if change is None and price and prev_close:
            change = price - prev_close
        if change_pct is None and change is not None and prev_close and prev_close != 0:
            change_pct = (change / prev_close) * 100

        div_yield = info.get("dividendYield")
        if div_yield and div_yield < 1:
            div_yield = div_yield * 100  # convert 0.03 → 3.0

        return {
            "ticker": ticker_symbol,
            "companyName": info.get("shortName") or info.get("longName") or ticker_symbol,
            "exchange": info.get("exchange") or info.get("fullExchangeName", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "currency": info.get("currency", "USD"),
            "price": price,
            "priceChange": change,
            "priceChangePct": change_pct,
            "marketCap": info.get("marketCap"),
            "peRatio": info.get("trailingPE"),
            "forwardPE": info.get("forwardPE"),
            "pbRatio": info.get("priceToBook"),
            "psRatio": info.get("priceToSalesTrailing12Months"),
            "evToEbitda": info.get("enterpriseToEbitda"),
            "dividendYield": div_yield,
            "week52High": info.get("fiftyTwoWeekHigh"),
            "week52Low": info.get("fiftyTwoWeekLow"),
            "volume": info.get("volume") or info.get("regularMarketVolume"),
            "avgVolume": info.get("averageVolume"),
            "beta": info.get("beta"),
            "eps": info.get("trailingEps"),
            "roe": info.get("returnOnEquity"),
        }
    except Exception as exc:
        print(f"[DEBUG] explore fetch failed for {ticker_symbol}: {exc}")
        return None


def _fetch_stocks_batch(tickers, max_workers=8):
    """Fetch explore data for a list of tickers with bounded concurrency."""
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {executor.submit(_fetch_single_stock_explore, t): t for t in tickers}
        for future in concurrent.futures.as_completed(future_map):
            try:
                result = future.result(timeout=15)
                if result:
                    results.append(result)
            except Exception as exc:
                print(f"[DEBUG] explore batch error for {future_map[future]}: {exc}")
    return results


def get_explore_markets():
    """Return available markets for the explore page."""
    markets = [
        {
            "id": key,
            "name": val["name"],
            "description": val["description"],
            "region": val["region"],
            "ticker_count": len(val["tickers"]),
        }
        for key, val in MARKET_TICKERS.items()
    ]
    return {
        "statusCode": 200,
        "body": json.dumps({"markets": markets}),
    }


def get_explore_stocks(market, force_refresh=False):
    """Return stocks for a specific market with key financial metrics."""
    market_id = market.upper()
    if market_id not in MARKET_TICKERS:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": f"Market '{market}' not found"}),
        }

    if not YFINANCE_AVAILABLE:
        return {
            "statusCode": 503,
            "body": json.dumps({"error": "yfinance not available in this environment"}),
        }

    now = datetime.utcnow()
    cache_entry = _explore_cache.get(market_id)
    if not force_refresh and cache_entry:
        age = (now - cache_entry["timestamp"]).total_seconds()
        if age < _EXPLORE_CACHE_TTL:
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "market": market_id,
                    "market_name": MARKET_TICKERS[market_id]["name"],
                    "stocks": cache_entry["data"],
                    "cached": True,
                    "cache_age_seconds": int(age),
                }),
            }

    tickers = MARKET_TICKERS[market_id]["tickers"]
    stocks = _fetch_stocks_batch(tickers)
    stocks.sort(key=lambda x: x.get("marketCap") or 0, reverse=True)

    _explore_cache[market_id] = {"data": stocks, "timestamp": now}

    return {
        "statusCode": 200,
        "body": json.dumps({
            "market": market_id,
            "market_name": MARKET_TICKERS[market_id]["name"],
            "stocks": stocks,
            "cached": False,
            "cache_age_seconds": 0,
        }),
    }


def lambda_handler(event, context):
    """AWS Lambda handler for stock data operations"""
    
    # Add CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': '*',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    
    try:
        # Route to appropriate handler
        if '/api/ticker/' in path:
            ticker = path.split('/api/ticker/')[-1]
            result = get_ticker_data(ticker)
        elif '/api/search' in path:
            params = event.get('queryStringParameters', {}) or {}
            query = params.get('q', '')
            result = search_stocks(query)
        elif path == '/api/explore/markets':
            result = get_explore_markets()
        elif '/api/explore/stocks' in path:
            params = event.get('queryStringParameters', {}) or {}
            market = params.get('market', 'SP500')
            force_refresh = params.get('force_refresh', '').lower() == 'true'
            result = get_explore_stocks(market, force_refresh)
        else:
            result = {
                'statusCode': 404,
                'body': json.dumps({'error': 'Not found'})
            }
        
        # Add CORS headers to result
        result['headers'] = headers
        return result
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': str(e)})
        }
