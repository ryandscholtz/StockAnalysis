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
# Explore Stocks – fetch ticker lists from API when available
# ---------------------------------------------------------------------------

# Cache for API-sourced ticker lists: {market_id: {"tickers": [...], "timestamp": datetime}}
_explore_ticker_list_cache = {}
_EXPLORE_TICKER_LIST_CACHE_TTL = 86400  # 24 hours

# MarketStack MIC -> Yahoo suffix for symbol conversion (e.g. XJSE -> .JO)
_MIC_TO_YAHOO_SUFFIX = {
    "XJSE": ".JO",   # Johannesburg
}


def _fetch_tickers_from_marketstack(mic: str, yahoo_suffix: str) -> list[str]:
    """
    Fetch all ticker symbols for an exchange from MarketStack GET /v1/exchanges/{mic}/tickers.
    Returns list of symbols in Yahoo Finance format (e.g. NPN.JO for JSE).
    """
    api_key = os.getenv('MARKETSTACK_API_KEY', '')
    if not api_key:
        return []

    all_symbols = []
    limit = 1000
    offset = 0

    try:
        while True:
            url = (
                f"https://api.marketstack.com/v1/exchanges/{mic}/tickers"
                f"?{urlencode({'access_key': api_key, 'limit': limit, 'offset': offset})}"
            )
            data = _urllib_get(url)
            if data.get('error'):
                break
            items = data.get('data', [])
            pagination = data.get('pagination', {})
            for item in items:
                raw = (item.get('symbol') or '').strip()
                if not raw:
                    continue
                # Convert to Yahoo format: BEL.XJSE -> BEL.JO, or plain NPN -> NPN.JO
                sym = _yahoo_symbol(raw) if raw.upper().endswith('.XJSE') else (raw + yahoo_suffix if yahoo_suffix and not raw.endswith(yahoo_suffix) else raw)
                if sym and sym not in all_symbols:
                    all_symbols.append(sym)
            count = pagination.get('count', 0)
            total = pagination.get('total', 0)
            offset += count
            if count < limit or offset >= total:
                break
        return all_symbols
    except Exception as e:
        print(f"[DEBUG] MarketStack tickers fetch failed for {mic}: {e}")
        return []


def _fetch_screener_tickers(screener_exchange: str, max_count: int = 10_000) -> list:
    """
    Fetch all equity tickers for an exchange via Yahoo Finance screener, sorted by market cap.
    screener_exchange is the Yahoo Finance exchange code (e.g. 'JNB' for JSE, 'NYQ' for NYSE).
    Works without a paid API key — uses the same crumb/cookie session.
    """
    # _get_yahoo_session is defined later in the file; import json is already at top level
    try:
        # _get_yahoo_session will be available at call time (defined below)
        crumb, cookie_str = _get_yahoo_session()
    except Exception as e:
        print(f"[DEBUG] Yahoo session error for screener {screener_exchange}: {e}")
        return []

    from urllib.request import Request as _Req, urlopen as _uopen
    url = (
        f"https://query2.finance.yahoo.com/v1/finance/screener"
        f"?formatted=false&crumb={crumb}&lang=en-US&region=US"
    )
    all_symbols = []
    batch = 250

    for offset in range(0, max_count, batch):
        size = min(batch, max_count - offset)
        body = json.dumps({
            "size": size,
            "offset": offset,
            "sortField": "intradaymarketcap",
            "sortType": "DESC",
            "quoteType": "EQUITY",
            "topOperator": "AND",
            "query": {
                "operator": "AND",
                "operands": [{"operator": "EQ", "operands": ["exchange", screener_exchange]}],
            },
            "userId": "",
            "userIdType": "guid",
        }).encode("utf-8")
        req = _Req(url, data=body, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Cookie": cookie_str,
        })
        try:
            with _uopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
            result = data.get("finance", {}).get("result") or []
            quotes = result[0].get("quotes", []) if result else []
            symbols = [q["symbol"] for q in quotes if q.get("symbol")]
            all_symbols.extend(symbols)
            print(f"[DEBUG] Screener {screener_exchange} offset={offset}: {len(symbols)} symbols")
            if len(symbols) < size:
                break  # exhausted
        except Exception as e:
            print(f"[DEBUG] Screener error {screener_exchange} offset={offset}: {e}")
            break

    return all_symbols


def _get_tickers_for_market(market_id: str, market_config: dict) -> list:
    """
    Return ticker list for a market.
    Priority: Yahoo screener > MarketStack > static tickers list.
    Results are cached for 24h inside _explore_ticker_list_cache.
    """
    screener_exchange = market_config.get('screener_exchange')
    mic = market_config.get('exchange_mic')
    yahoo_suffix = market_config.get('yahoo_suffix', _MIC_TO_YAHOO_SUFFIX.get(mic or '', ''))

    if screener_exchange or mic:
        now = datetime.utcnow()
        cache_entry = _explore_ticker_list_cache.get(market_id)
        if cache_entry:
            age = (now - cache_entry["timestamp"]).total_seconds()
            if age < _EXPLORE_TICKER_LIST_CACHE_TTL:
                return list(cache_entry["tickers"])

        tickers = []
        if screener_exchange:
            tickers = _fetch_screener_tickers(screener_exchange, max_count=market_config.get('screener_max', 10_000))
        if not tickers and mic:
            tickers = _fetch_tickers_from_marketstack(mic, yahoo_suffix)
        if tickers:
            _explore_ticker_list_cache[market_id] = {"tickers": tickers, "timestamp": now}
            return tickers
        # Fallback to static list
        static = market_config.get('tickers', [])
        if static:
            return list(static)
        return []

    return list(dict.fromkeys(market_config.get('tickers', [])))


# ---------------------------------------------------------------------------
# Explore Stocks – market/exchange browser
# ---------------------------------------------------------------------------

MARKET_TICKERS = {
    # ── Americas ────────────────────────────────────────────────────────────────
    "NYSE": {
        "name": "NYSE",
        "description": "New York Stock Exchange – all listed companies",
        "region": "US", "continent": "Americas",
        "screener_exchange": "NYQ",
        "tickers": [],  # screener-driven
    },
    "NASDAQ": {
        "name": "NASDAQ",
        "description": "NASDAQ Global Select Market – all listed companies",
        "region": "US", "continent": "Americas",
        "screener_exchange": "NMS",
        "tickers": [],  # screener-driven
    },
    "TSX": {
        "name": "TSX",
        "description": "Toronto Stock Exchange – all listed Canadian companies",
        "region": "CA", "continent": "Americas",
        "screener_exchange": "TOR",
        "tickers": [  # fallback
            "RY.TO", "TD.TO", "BNS.TO", "BMO.TO", "CM.TO", "ENB.TO", "CNR.TO",
            "TRP.TO", "SU.TO", "ABX.TO", "MFC.TO", "SLF.TO", "CP.TO", "BCE.TO",
            "T.TO", "CNQ.TO", "PPL.TO", "ATD.TO", "GWO.TO", "AEM.TO",
        ],
    },
    "SP500": {
        "name": "S&P 500",
        "description": "S&P 500 – 500 largest US public companies by market cap",
        "region": "US", "continent": "Americas",
        "tickers": [
            # A
            "A", "AAL", "AAPL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE", "ADI",
            "ADM", "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIZ", "AJG",
            "AKAM", "ALB", "ALGN", "ALL", "ALLE", "AMAT", "AMCR", "AMD", "AME", "AMGN",
            "AMP", "AMT", "AMZN", "ANET", "ANSS", "AON", "AOS", "APA", "APD", "APH",
            "APTV", "ARE", "ATO", "AVB", "AVGO", "AVY", "AWK", "AXON", "AXP", "AZO",
            # B
            "BA", "BAC", "BALL", "BAX", "BBWI", "BBY", "BDX", "BEN", "BF-B", "BIIB",
            "BIO", "BK", "BKNG", "BKR", "BLK", "BMY", "BR", "BRK-B", "BRO", "BSX",
            "BWA", "BX", "BXP",
            # C
            "C", "CAG", "CAH", "CARR", "CAT", "CB", "CBOE", "CBRE", "CCI", "CCL",
            "CDNS", "CDW", "CE", "CEG", "CF", "CFG", "CHD", "CHRW", "CHTR", "CI",
            "CINF", "CL", "CLX", "CMA", "CMCSA", "CME", "CMG", "CMI", "CMS", "CNC",
            "CNP", "COF", "COO", "COP", "COR", "COST", "CPAY", "CPB", "CPRT", "CPT",
            "CRL", "CRM", "CRWD", "CSCO", "CSGP", "CSX", "CTAS", "CTLT", "CTSH", "CTVA",
            "CVS", "CVX", "CZR",
            # D
            "D", "DAL", "DAY", "DD", "DE", "DECK", "DELL", "DFS", "DG", "DGX",
            "DHI", "DHR", "DIS", "DLR", "DLTR", "DOC", "DOV", "DOW", "DPZ", "DRI",
            "DTE", "DUK", "DVA", "DVN", "DXCM",
            # E
            "EA", "EBAY", "ECL", "ED", "EFX", "EG", "EIX", "EL", "ELV", "EMN",
            "EMR", "ENPH", "EOG", "EPAM", "EQIX", "EQR", "EQT", "ES", "ESS", "ETN",
            "ETR", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR",
            # F
            "F", "FANG", "FAST", "FCX", "FDS", "FDX", "FE", "FFIV", "FI", "FICO",
            "FIS", "FITB", "FLT", "FMC", "FOX", "FOXA", "FRT", "FSLR", "FTNT", "FTV",
            # G
            "GD", "GDDY", "GE", "GEHC", "GEN", "GILD", "GIS", "GL", "GLW", "GM",
            "GOOGL", "GOOG", "GPC", "GPN", "GRMN", "GS", "GWW",
            # H
            "HAL", "HAS", "HBAN", "HCA", "HD", "HES", "HIG", "HII", "HLT", "HOLX",
            "HON", "HPE", "HPQ", "HRL", "HSIC", "HST", "HSY", "HUBB", "HUM", "HWM",
            # I
            "IBM", "ICE", "IDXX", "IEX", "IFF", "ILMN", "INCY", "INTC", "INTU", "INVH",
            "IP", "IPG", "IQV", "IR", "IRM", "ISRG", "IT", "ITW", "IVZ",
            # J
            "J", "JBHT", "JBL", "JCI", "JKHY", "JNJ", "JNPR", "JPM",
            # K
            "K", "KDP", "KEY", "KEYS", "KHC", "KIM", "KKR", "KLAC", "KMB", "KMI",
            "KMX", "KO", "KR",
            # L
            "L", "LDOS", "LEN", "LH", "LHX", "LIN", "LKQ", "LLY", "LMT", "LNT",
            "LOW", "LRCX", "LULU", "LUV", "LVS", "LW", "LYB", "LYV",
            # M
            "MA", "MAA", "MAR", "MAS", "MCD", "MCHP", "MCK", "MCO", "MDLZ", "MDT",
            "MET", "META", "MGM", "MHK", "MKC", "MKTX", "MLM", "MMC", "MMM", "MNST",
            "MO", "MOH", "MOS", "MPC", "MPWR", "MRK", "MRNA", "MRO", "MS", "MSCI",
            "MSFT", "MSI", "MTB", "MTCH", "MTD", "MU",
            # N
            "NCLH", "NDAQ", "NEE", "NEM", "NFLX", "NI", "NKE", "NOC", "NOW", "NRG",
            "NSC", "NTAP", "NTRS", "NUE", "NVDA", "NVR", "NWS", "NWSA", "NXPI",
            # O
            "O", "ODFL", "OKE", "OMC", "ON", "ORCL", "ORLY", "OTIS", "OXY",
            # P
            "PANW", "PARA", "PAYC", "PAYX", "PCAR", "PCG", "PEG", "PEP", "PFE", "PFG",
            "PG", "PGR", "PH", "PHM", "PKG", "PLD", "PM", "PNC", "PNR", "PNW",
            "PODD", "POOL", "PPG", "PPL", "PRU", "PSA", "PSX", "PTC", "PWR", "PYPL",
            # Q
            "QCOM", "QRVO",
            # R
            "RCL", "REG", "REGN", "RF", "RJF", "RL", "RMD", "ROK", "ROL", "ROP",
            "ROST", "RSG", "RTX", "RVTY",
            # S
            "SBAC", "SBUX", "SCHW", "SHW", "SJM", "SLB", "SMCI", "SNA", "SNPS", "SO",
            "SPG", "SPGI", "SRE", "STE", "STLD", "STT", "STX", "STZ", "SWK", "SWKS",
            "SYF", "SYK", "SYY",
            # T
            "T", "TAP", "TDG", "TDY", "TECH", "TEL", "TER", "TFC", "TFX", "TGT",
            "TJX", "TMO", "TMUS", "TPR", "TRGP", "TRMB", "TROW", "TRV", "TSCO", "TSLA",
            "TSN", "TT", "TTWO", "TXN", "TXT", "TYL",
            # U
            "UAL", "UDR", "UHS", "ULTA", "UNH", "UNP", "UPS", "URI", "USB",
            # V
            "V", "VFC", "VICI", "VLO", "VLTO", "VMC", "VNO", "VRSK", "VRSN", "VRTX",
            "VST", "VZ",
            # W
            "WAB", "WAT", "WBA", "WBD", "WDC", "WEC", "WELL", "WFC", "WM", "WMB",
            "WMT", "WRB", "WST", "WTW", "WY", "WYNN",
            # X–Z
            "XEL", "XOM", "XYL", "YUM", "ZBH", "ZBRA", "ZTS",
        ],
    },
    "NASDAQ100": {
        "name": "NASDAQ 100",
        "description": "NASDAQ 100 – top 100 non-financial companies listed on NASDAQ",
        "region": "US", "continent": "Americas",
        "tickers": [
            "AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "GOOGL", "GOOG", "AVGO", "COST",
            "NFLX", "TMUS", "AMD", "CSCO", "ADBE", "PEP", "TXN", "QCOM", "HON", "INTU",
            "AMAT", "AMGN", "ISRG", "MU", "BKNG", "LRCX", "REGN", "ADI", "VRTX", "PANW",
            "KLAC", "SNPS", "MRVL", "CDNS", "GILD", "SBUX", "ADP", "MDLZ", "PYPL", "CTAS",
            "ABNB", "ORLY", "FTNT", "MELI", "MNST", "CRWD", "PCAR", "KDP", "INTC", "ASML",
            "IDXX", "PAYX", "FAST", "ROP", "ROST", "ODFL", "DXCM", "ON", "CEG", "ANSS",
            "GEHC", "FANG", "CSGP", "XEL", "CPRT", "KHC", "DLTR", "TTD", "EXC", "EA",
            "BIIB", "VRSK", "NXPI", "BKR", "TTWO", "ADSK", "LULU", "CHTR", "AEP", "CSX",
            "CMCSA", "NDAQ", "ILMN", "WBD", "MRNA", "CCEP", "CDW", "SIRI", "DASH", "ARM",
            "SMCI", "MSTR", "GEHC", "ZS", "DDOG", "WDAY", "TEAM", "OKTA", "SPLK", "PDD",
        ],
    },
    "DOW30": {
        "name": "Dow Jones 30",
        "description": "Dow Jones Industrial Average – 30 blue-chip stocks",
        "region": "US", "continent": "Americas",
        "tickers": [
            "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW",
            "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM",
            "MRK", "MSFT", "NKE", "PG", "TRV", "UNH", "V", "VZ", "WBA", "WMT",
        ],
    },
    "B3": {
        "name": "B3 São Paulo",
        "description": "B3 – all listed Brazilian companies",
        "region": "BR", "continent": "Americas",
        "screener_exchange": "SAO",
        "tickers": [  # fallback
            "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "ABEV3.SA",
            "WEGE3.SA", "RENT3.SA", "B3SA3.SA", "SUZB3.SA",
        ],
    },
    "BOVESPA": {
        "name": "Ibovespa",
        "description": "B3 São Paulo – top Brazilian companies",
        "region": "BR", "continent": "Americas",
        "tickers": [
            "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "ABEV3.SA",
            "WEGE3.SA", "RENT3.SA", "B3SA3.SA", "SUZB3.SA", "JBSS3.SA", "EQTL3.SA",
            "ELET3.SA", "CMIG4.SA", "SBSP3.SA", "TOTS3.SA", "GGBR4.SA", "LREN3.SA",
            "MGLU3.SA", "RAIL3.SA",
        ],
    },
    "BMV": {
        "name": "Bolsa Mexicana",
        "description": "Bolsa Mexicana de Valores – all listed Mexican companies",
        "region": "MX", "continent": "Americas",
        "screener_exchange": "MEX",
        "tickers": [  # fallback
            "AMXL.MX", "WALMEXV.MX", "FEMSAUBD.MX", "GFNORTEO.MX", "CEMEXCPO.MX",
            "BIMBOA.MX", "KOFL.MX", "GRUMAB.MX",
        ],
    },
    "IPC": {
        "name": "IPC Mexico",
        "description": "Bolsa Mexicana – top Mexican companies",
        "region": "MX", "continent": "Americas",
        "tickers": [
            "AMXL.MX", "WALMEXV.MX", "FEMSAUBD.MX", "GFNORTEO.MX", "CEMEXCPO.MX",
            "BIMBOA.MX", "KOFL.MX", "GRUMAB.MX", "GMEXICOB.MX", "GAPB.MX",
            "OMAB.MX", "ASURB.MX", "ALFAA.MX", "IENOVA.MX", "ALSEA.MX",
        ],
    },
    # ── Europe ──────────────────────────────────────────────────────────────────
    "LSE": {
        "name": "London Stock Exchange",
        "description": "London Stock Exchange – all listed UK companies",
        "region": "GB", "continent": "Europe",
        "screener_exchange": "LSE",
        "tickers": [  # fallback
            "AZN.L", "SHEL.L", "HSBA.L", "ULVR.L", "BP.L", "BATS.L", "GSK.L", "RIO.L",
            "DGE.L", "REL.L", "BA.L", "LSEG.L", "PRU.L", "IMB.L", "NG.L", "VOD.L",
            "BT-A.L", "LLOY.L", "BARC.L", "NWG.L",
        ],
    },
    "XETRA": {
        "name": "Frankfurt (XETRA)",
        "description": "Deutsche Börse XETRA – all listed German companies",
        "region": "DE", "continent": "Europe",
        "screener_exchange": "GER",
        "tickers": [  # fallback
            "SAP.DE", "SIE.DE", "ALV.DE", "MBG.DE", "DTE.DE", "BAYN.DE", "BMW.DE",
            "VOW3.DE", "MUV2.DE", "DB1.DE", "RWE.DE", "BAS.DE", "MRK.DE", "HEI.DE",
            "ADS.DE", "IFX.DE",
        ],
    },
    "EURONEXT_PA": {
        "name": "Euronext Paris",
        "description": "Euronext Paris – all listed French companies",
        "region": "FR", "continent": "Europe",
        "screener_exchange": "PAR",
        "tickers": [  # fallback
            "MC.PA", "TTE.PA", "SAN.PA", "OR.PA", "AIR.PA", "SU.PA", "BNP.PA", "AI.PA",
            "KER.PA", "RMS.PA", "DSY.PA", "ACA.PA", "GLE.PA",
        ],
    },
    "EURONEXT_AM": {
        "name": "Euronext Amsterdam",
        "description": "Euronext Amsterdam – all listed Dutch companies",
        "region": "NL", "continent": "Europe",
        "screener_exchange": "AMS",
        "tickers": [  # fallback
            "ASML.AS", "HEIA.AS", "PHIA.AS", "ABN.AS", "ING.AS", "NN.AS", "AKZA.AS",
            "AD.AS", "WKL.AS", "RAND.AS",
        ],
    },
    "BORSA_IT": {
        "name": "Borsa Italiana",
        "description": "Borsa Italiana – all listed Italian companies",
        "region": "IT", "continent": "Europe",
        "screener_exchange": "MIL",
        "tickers": [  # fallback
            "ENI.MI", "ENEL.MI", "ISP.MI", "UCG.MI", "STLAM.MI", "RACE.MI", "STM.MI",
            "LDO.MI", "MONC.MI", "AMP.MI",
        ],
    },
    "BME": {
        "name": "Bolsa de Madrid",
        "description": "Bolsa de Madrid – all listed Spanish companies",
        "region": "ES", "continent": "Europe",
        "screener_exchange": "MCE",
        "tickers": [  # fallback
            "ITX.MC", "SAN.MC", "BBVA.MC", "IBE.MC", "TEF.MC", "REP.MC", "AMS.MC",
            "CABK.MC", "SAB.MC", "ENG.MC",
        ],
    },
    "NASDAQ_ST": {
        "name": "Nasdaq Stockholm",
        "description": "Nasdaq Stockholm – all listed Swedish companies",
        "region": "SE", "continent": "Europe",
        "screener_exchange": "STO",
        "tickers": [  # fallback
            "VOLV-B.ST", "ERIC-B.ST", "INVE-B.ST", "ATCO-A.ST", "HM-B.ST", "SEB-A.ST",
            "SHB-A.ST", "SWED-A.ST", "NIBE-B.ST", "SAND.ST",
        ],
    },
    "NASDAQ_CO": {
        "name": "Nasdaq Copenhagen",
        "description": "Nasdaq Copenhagen – all listed Danish companies",
        "region": "DK", "continent": "Europe",
        "screener_exchange": "CPH",
        "tickers": [  # fallback
            "NOVO-B.CO", "MAERSK-B.CO", "ORSTED.CO", "COLOB.CO", "GMAB.CO",
            "VWS.CO", "DSV.CO", "CARL-B.CO",
        ],
    },
    "OSLO": {
        "name": "Oslo Børs",
        "description": "Oslo Stock Exchange – all listed Norwegian companies",
        "region": "NO", "continent": "Europe",
        "screener_exchange": "OSL",
        "tickers": [  # fallback
            "EQNR.OL", "DNB.OL", "TEL.OL", "ORK.OL", "YAR.OL", "MOWI.OL",
            "SALM.OL", "AKRBP.OL",
        ],
    },
    "EURONEXT_BR": {
        "name": "Euronext Brussels",
        "description": "Euronext Brussels – all listed Belgian companies",
        "region": "BE", "continent": "Europe",
        "screener_exchange": "BRU",
        "tickers": [  # fallback
            "ABI.BR", "UCB.BR", "SOLB.BR", "ACKB.BR", "GBLB.BR", "KBC.BR",
            "PROX.BR", "COLR.BR",
        ],
    },
    "EURONEXT_LI": {
        "name": "Euronext Lisbon",
        "description": "Euronext Lisbon – all listed Portuguese companies",
        "region": "PT", "continent": "Europe",
        "screener_exchange": "LIS",
        "tickers": [  # fallback
            "EDP.LS", "GALP.LS", "JMT.LS", "NOS.LS", "BCP.LS", "EDPR.LS",
        ],
    },
    "GPW": {
        "name": "Warsaw Stock Exchange",
        "description": "Warsaw Stock Exchange – all listed Polish companies",
        "region": "PL", "continent": "Europe",
        "screener_exchange": "WSE",
        "tickers": [  # fallback
            "PKN.WA", "PKO.WA", "PZU.WA", "KGHM.WA", "PGE.WA", "OPL.WA",
            "CDR.WA", "JSW.WA", "LPP.WA",
        ],
    },
    "WIENER": {
        "name": "Vienna Stock Exchange",
        "description": "Vienna Stock Exchange – all listed Austrian companies",
        "region": "AT", "continent": "Europe",
        "screener_exchange": "VIE",
        "tickers": [  # fallback
            "OMV.VI", "VOE.VI", "ANDR.VI", "EBS.VI", "RBI.VI", "ATS.VI", "VIG.VI",
        ],
    },
    "NASDAQ_HE": {
        "name": "Nasdaq Helsinki",
        "description": "Nasdaq Helsinki – all listed Finnish companies",
        "region": "FI", "continent": "Europe",
        "screener_exchange": "HEL",
        "tickers": [  # fallback
            "NOKIA.HE", "NESTE.HE", "SAMPO.HE", "KNEBV.HE", "WRT1V.HE",
            "METSO.HE", "KESKO.HE",
        ],
    },
    "SIX": {
        "name": "SIX Swiss Exchange",
        "description": "SIX Swiss Exchange – all listed Swiss companies",
        "region": "CH", "continent": "Europe",
        "screener_exchange": "ZRH",
        "tickers": [  # fallback
            "NOVN.SW", "NESN.SW", "ROG.SW", "ABBN.SW", "ZURN.SW", "CFR.SW",
            "SIKA.SW", "ALC.SW", "LONN.SW", "SLHN.SW",
        ],
    },
    "FTSE100": {
        "name": "FTSE 100",
        "description": "London Stock Exchange – largest UK companies by market cap",
        "region": "GB", "continent": "Europe",
        "tickers": [
            "AZN.L", "SHEL.L", "HSBA.L", "ULVR.L", "BP.L", "BATS.L", "GSK.L", "RIO.L",
            "DGE.L", "REL.L", "BA.L", "LSEG.L", "PRU.L", "IMB.L", "NG.L", "VOD.L",
            "BT-A.L", "LLOY.L", "BARC.L", "NWG.L", "STAN.L", "AAL.L", "ANTO.L", "ABF.L",
            "CNA.L", "SSE.L", "WPP.L", "HLN.L", "MNDI.L", "RKT.L",
        ],
    },
    "DAX": {
        "name": "DAX 40",
        "description": "Frankfurt Stock Exchange – largest German companies by market cap",
        "region": "DE", "continent": "Europe",
        "tickers": [
            "SAP.DE", "SIE.DE", "ALV.DE", "MBG.DE", "DTE.DE", "BAYN.DE", "BMW.DE",
            "VOW3.DE", "MUV2.DE", "DB1.DE", "RWE.DE", "BAS.DE", "MRK.DE", "HEI.DE",
            "ADS.DE", "IFX.DE", "LIN.DE", "EOAN.DE", "HEN3.DE", "DHER.DE",
        ],
    },
    "CAC40": {
        "name": "CAC 40",
        "description": "Euronext Paris – largest French companies by market cap",
        "region": "FR", "continent": "Europe",
        "tickers": [
            "MC.PA", "TTE.PA", "SAN.PA", "OR.PA", "AIR.PA", "SU.PA", "BNP.PA", "AI.PA",
            "KER.PA", "RMS.PA", "DSY.PA", "ACA.PA", "GLE.PA", "LR.PA", "CAP.PA", "SAF.PA",
            "DG.PA", "VIE.PA", "ORA.PA", "HO.PA", "RI.PA", "BN.PA", "ML.PA", "STM.PA",
            "RNO.PA", "SGO.PA", "EL.PA", "CS.PA", "PUB.PA", "EN.PA",
        ],
    },
    "IBEX35": {
        "name": "IBEX 35",
        "description": "Bolsa de Madrid – largest Spanish companies by market cap",
        "region": "ES", "continent": "Europe",
        "tickers": [
            "ITX.MC", "SAN.MC", "BBVA.MC", "IBE.MC", "TEF.MC", "REP.MC", "AMS.MC",
            "CABK.MC", "SAB.MC", "ENG.MC", "GRF.MC", "ACS.MC", "FER.MC", "MAP.MC",
            "IAG.MC", "ELE.MC", "NTGY.MC", "MTS.MC", "MEL.MC", "CLNX.MC",
        ],
    },
    "FTSEMIB": {
        "name": "FTSE MIB",
        "description": "Borsa Italiana – top Italian companies",
        "region": "IT", "continent": "Europe",
        "tickers": [
            "ENI.MI", "ENEL.MI", "ISP.MI", "UCG.MI", "STLAM.MI", "RACE.MI", "STM.MI",
            "TIT.MI", "LDO.MI", "MONC.MI", "AMP.MI", "BAMI.MI", "MB.MI", "PRY.MI",
            "A2A.MI", "G.MI", "SRG.MI", "TRN.MI", "CPR.MI", "PIRC.MI",
        ],
    },
    "SMI": {
        "name": "SMI",
        "description": "SIX Swiss Exchange – largest Swiss companies by market cap",
        "region": "CH", "continent": "Europe",
        "tickers": [
            "NOVN.SW", "NESN.SW", "ROG.SW", "ABBN.SW", "ZURN.SW", "CFR.SW", "SIKA.SW",
            "ALC.SW", "LONN.SW", "SLHN.SW", "SREN.SW", "GIVN.SW", "UBSG.SW", "SOON.SW",
            "PGHN.SW", "VACN.SW", "BAER.SW", "SCMN.SW", "KNIN.SW", "UHR.SW",
        ],
    },
    "AEX": {
        "name": "AEX",
        "description": "Euronext Amsterdam – top Dutch companies",
        "region": "NL", "continent": "Europe",
        "tickers": [
            "ASML.AS", "HEIA.AS", "PHIA.AS", "ABN.AS", "ING.AS", "NN.AS", "AKZA.AS",
            "AD.AS", "WKL.AS", "RAND.AS", "IMCD.AS", "BESI.AS", "EXOR.AS", "AGN.AS",
            "URW.AS", "OCI.AS", "FLOW.AS", "LIGHT.AS", "TKWY.AS", "DSFIR.AS",
        ],
    },
    "OMXS30": {
        "name": "OMX Stockholm",
        "description": "Nasdaq Stockholm – largest Swedish companies by market cap",
        "region": "SE", "continent": "Europe",
        "tickers": [
            "VOLV-B.ST", "ERIC-B.ST", "INVE-B.ST", "ATCO-A.ST", "HM-B.ST", "SEB-A.ST",
            "SHB-A.ST", "SWED-A.ST", "NIBE-B.ST", "SAND.ST", "SKF-B.ST", "EVO.ST",
            "ALFA.ST", "BOL.ST", "HEXA-B.ST", "NDA-SE.ST", "ESSITY-B.ST", "ASSA-B.ST",
            "SSAB-B.ST", "KINV-B.ST",
        ],
    },
    "OMXC25": {
        "name": "OMX Copenhagen",
        "description": "Nasdaq Copenhagen – largest Danish companies by market cap",
        "region": "DK", "continent": "Europe",
        "tickers": [
            "NOVO-B.CO", "MAERSK-B.CO", "ORSTED.CO", "COLOB.CO", "GMAB.CO", "VWS.CO",
            "DSV.CO", "CARL-B.CO", "NZYM-B.CO", "GN.CO", "TRYG.CO", "ISS.CO",
            "CHR.CO", "PNDORA.CO", "DEMANT.CO",
        ],
    },
    "OBX": {
        "name": "Oslo Børs",
        "description": "Oslo Stock Exchange – top Norwegian companies",
        "region": "NO", "continent": "Europe",
        "tickers": [
            "EQNR.OL", "DNB.OL", "TEL.OL", "ORK.OL", "YAR.OL", "MOWI.OL", "SALM.OL",
            "AKRBP.OL", "AKER.OL", "SUBC.OL", "FRO.OL", "NEL.OL", "ENTRA.OL",
            "SCATC.OL", "KAHOT.OL",
        ],
    },
    "BEL20": {
        "name": "BEL 20",
        "description": "Euronext Brussels – largest Belgian companies by market cap",
        "region": "BE", "continent": "Europe",
        "tickers": [
            "ABI.BR", "UCB.BR", "SOLB.BR", "ACKB.BR", "GBLB.BR", "KBC.BR", "PROX.BR",
            "COLR.BR", "BPOST.BR", "BARN.BR", "AGS.BR", "WDP.BR", "ONTEX.BR",
            "BELIMO.BR", "SOFINA.BR",
        ],
    },
    "PSI20": {
        "name": "PSI 20",
        "description": "Euronext Lisbon – largest Portuguese companies by market cap",
        "region": "PT", "continent": "Europe",
        "tickers": [
            "EDP.LS", "GALP.LS", "JMT.LS", "NOS.LS", "BCP.LS", "EDPR.LS",
            "CTT.LS", "SONC.LS", "NVG.LS", "RAM.LS",
        ],
    },
    "WIG20": {
        "name": "WIG 20",
        "description": "Warsaw Stock Exchange – largest Polish companies by market cap",
        "region": "PL", "continent": "Europe",
        "tickers": [
            "PKN.WA", "PKO.WA", "PZU.WA", "KGHM.WA", "PGE.WA", "OPL.WA", "CDR.WA",
            "JSW.WA", "LPP.WA", "MBK.WA", "PEO.WA", "ALR.WA", "CCC.WA", "DNP.WA",
            "ALE.WA",
        ],
    },
    "ATX": {
        "name": "ATX",
        "description": "Vienna Stock Exchange – top Austrian companies",
        "region": "AT", "continent": "Europe",
        "tickers": [
            "OMV.VI", "VOE.VI", "ANDR.VI", "EBS.VI", "RBI.VI", "ATS.VI",
            "VIG.VI", "CAI.VI", "POST.VI", "EVN.VI",
        ],
    },
    "OMXH25": {
        "name": "OMX Helsinki",
        "description": "Nasdaq Helsinki – largest Finnish companies by market cap",
        "region": "FI", "continent": "Europe",
        "tickers": [
            "NOKIA.HE", "NESTE.HE", "SAMPO.HE", "KNEBV.HE", "WRT1V.HE",
            "METSO.HE", "KESKO.HE", "FORTUM.HE", "STERV.HE", "ORNBV.HE",
        ],
    },
    # ── Asia Pacific ────────────────────────────────────────────────────────────
    "ASX200": {
        "name": "ASX",
        "description": "Australian Securities Exchange – all listed Australian companies",
        "region": "AU", "continent": "Asia Pacific",
        "screener_exchange": "ASX",
        "tickers": [  # fallback
            "BHP.AX", "CSL.AX", "CBA.AX", "NAB.AX", "WBC.AX", "ANZ.AX", "WES.AX",
            "MQG.AX", "RIO.AX", "TLS.AX", "WOW.AX", "FMG.AX", "AMC.AX",
            "ALL.AX", "REA.AX", "QBE.AX", "SUN.AX", "IAG.AX", "MPL.AX", "ORG.AX",
        ],
    },
    "HANGSENG": {
        "name": "HKEX",
        "description": "Hong Kong Stock Exchange – all listed companies",
        "region": "HK", "continent": "Asia Pacific",
        "screener_exchange": "HKG",
        "tickers": [  # fallback
            "0700.HK", "9988.HK", "0939.HK", "1398.HK", "3988.HK", "0005.HK",
            "0388.HK", "2318.HK", "0941.HK", "0883.HK", "0857.HK", "0688.HK",
            "0011.HK", "0992.HK", "0027.HK", "0001.HK", "1177.HK", "0762.HK",
            "0003.HK", "2020.HK",
        ],
    },
    "KOSPI": {
        "name": "Korea Exchange",
        "description": "Korea Exchange – all listed South Korean companies",
        "region": "KR", "continent": "Asia Pacific",
        "screener_exchange": "KOE",
        "tickers": [  # fallback
            "005930.KS", "000660.KS", "035420.KS", "005380.KS", "000270.KS",
            "051910.KS", "035720.KS", "006400.KS", "017670.KS", "015760.KS",
            "012330.KS", "009150.KS", "028260.KS", "032830.KS", "033780.KS",
        ],
    },
    "TWSE": {
        "name": "TWSE",
        "description": "Taiwan Stock Exchange – all listed Taiwanese companies",
        "region": "TW", "continent": "Asia Pacific",
        "screener_exchange": "TAI",
        "tickers": [  # fallback
            "2330.TW", "2454.TW", "2317.TW", "2308.TW", "2303.TW", "2412.TW",
            "2882.TW", "1303.TW", "1301.TW", "2886.TW", "2891.TW", "1326.TW",
            "2881.TW", "2002.TW", "2207.TW",
        ],
    },
    "TSE": {
        "name": "Tokyo Stock Exchange",
        "description": "Tokyo Stock Exchange – all listed Japanese companies",
        "region": "JP", "continent": "Asia Pacific",
        "screener_exchange": "TKS",
        "tickers": [  # fallback
            "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "8316.T", "6902.T",
            "9432.T", "9433.T", "4063.T", "6954.T", "7974.T",
        ],
    },
    "NSE": {
        "name": "NSE India",
        "description": "National Stock Exchange of India – all listed Indian companies",
        "region": "IN", "continent": "Asia Pacific",
        "screener_exchange": "NSI",
        "tickers": [  # fallback
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
            "ICICIBANK.NS", "KOTAKBANK.NS", "SBIN.NS",
        ],
    },
    "SGX": {
        "name": "Singapore Exchange",
        "description": "Singapore Exchange – all listed companies",
        "region": "SG", "continent": "Asia Pacific",
        "screener_exchange": "SGX",
        "tickers": [  # fallback
            "D05.SI", "O39.SI", "U11.SI", "Z74.SI", "C6L.SI", "BN4.SI",
            "J36.SI", "S63.SI",
        ],
    },
    "SSE": {
        "name": "Shanghai Stock Exchange",
        "description": "Shanghai Stock Exchange – all listed Chinese A-share companies",
        "region": "CN", "continent": "Asia Pacific",
        "screener_exchange": "SHH",
        "tickers": [  # fallback
            "600519.SS", "601318.SS", "601398.SS", "600036.SS", "600900.SS",
            "601166.SS", "600690.SS",
        ],
    },
    "SZSE": {
        "name": "Shenzhen Stock Exchange",
        "description": "Shenzhen Stock Exchange – all listed Chinese companies",
        "region": "CN", "continent": "Asia Pacific",
        "screener_exchange": "SHZ",
        "tickers": [  # fallback
            "000858.SZ", "300750.SZ", "000333.SZ", "002415.SZ", "002594.SZ",
            "000001.SZ", "000002.SZ",
        ],
    },
    "NIKKEI": {
        "name": "Nikkei 225",
        "description": "Tokyo Stock Exchange – top Japanese companies",
        "region": "JP", "continent": "Asia Pacific",
        "tickers": [
            "7203.T", "6758.T", "9984.T", "6861.T", "8306.T", "8316.T", "6902.T",
            "9432.T", "9433.T", "4063.T", "6954.T", "7974.T", "8035.T", "4519.T",
            "6367.T", "5108.T", "4661.T", "9022.T", "8591.T", "6098.T",
        ],
    },
    "NIFTY50": {
        "name": "Nifty 50",
        "description": "NSE India – largest Indian companies by market cap",
        "region": "IN", "continent": "Asia Pacific",
        "tickers": [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "HINDUNILVR.NS",
            "ICICIBANK.NS", "KOTAKBANK.NS", "SBIN.NS", "BAJFINANCE.NS", "BHARTIARTL.NS",
            "WIPRO.NS", "ITC.NS", "TATAMOTORS.NS", "HCLTECH.NS", "AXISBANK.NS",
            "ASIANPAINT.NS", "MARUTI.NS", "NESTLEIND.NS", "ULTRACEMCO.NS", "LT.NS",
            "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "SUNPHARMA.NS", "TITAN.NS",
        ],
    },
    "STI": {
        "name": "STI Singapore",
        "description": "Singapore Exchange – top Singaporean companies",
        "region": "SG", "continent": "Asia Pacific",
        "tickers": [
            "D05.SI", "O39.SI", "U11.SI", "Z74.SI", "C6L.SI", "BN4.SI", "J36.SI",
            "S63.SI", "9CI.SI", "C38U.SI", "A17U.SI", "G13.SI", "V03.SI",
            "BS6.SI", "F34.SI",
        ],
    },
    "CSI300": {
        "name": "CSI 300",
        "description": "Shanghai/Shenzhen – top Chinese A-share companies",
        "region": "CN", "continent": "Asia Pacific",
        "tickers": [
            "600519.SS", "000858.SZ", "300750.SZ", "601318.SS", "601398.SS",
            "600036.SS", "601888.SS", "000333.SZ", "002415.SZ", "600900.SS",
            "601166.SS", "600690.SS", "000001.SZ", "601857.SS", "002594.SZ",
        ],
    },
    # ── Middle East & Africa ─────────────────────────────────────────────────────
    "TADAWUL": {
        "name": "Tadawul",
        "description": "Saudi Exchange – all listed Saudi Arabian companies",
        "region": "SA", "continent": "Middle East & Africa",
        "screener_exchange": "SAU",
        "tickers": [  # fallback
            "2222.SR", "1180.SR", "2010.SR", "4200.SR", "1050.SR", "2030.SR",
            "1150.SR", "4005.SR", "8010.SR", "2350.SR", "4001.SR", "4030.SR",
            "1111.SR", "2380.SR", "7010.SR",
        ],
    },
    "TASE": {
        "name": "Tel Aviv Stock Exchange",
        "description": "Tel Aviv Stock Exchange – all listed Israeli companies",
        "region": "IL", "continent": "Middle East & Africa",
        "screener_exchange": "TLV",
        "tickers": [  # fallback
            "NICE.TA", "ESLT.TA", "ICL.TA", "TEVA.TA", "BEZQ.TA", "LUMI.TA",
            "HAPO.TA", "MZTF.TA", "AZRG.TA", "FIBI.TA", "POLI.TA", "ENLT.TA",
            "KRNT.TA", "DSCT.TA", "BIDI.TA",
        ],
    },
    "JSE": {
        "name": "JSE",
        "description": "Johannesburg Stock Exchange – all listed companies",
        "region": "ZA", "continent": "Middle East & Africa",
        "screener_exchange": "JNB",
        "exchange_mic": "XJSE",  # MarketStack fallback
        "yahoo_suffix": ".JO",
        "tickers": [  # fallback if both screener and MarketStack fail
            "NPN.JO", "PRX.JO", "CPI.JO", "FSR.JO", "SBK.JO", "MTN.JO", "AGL.JO",
            "SOL.JO", "SHP.JO", "WHL.JO", "REM.JO", "DSY.JO", "GRT.JO", "AMS.JO",
            "ABG.JO", "NED.JO", "BID.JO", "IMP.JO", "SGL.JO", "GFI.JO", "HAR.JO",
        ],
    },
}

# In-process cache: {market_id: {"data": [...], "timestamp": datetime}}
_explore_cache = {}
_EXPLORE_CACHE_TTL = 900  # 15 minutes


# Module-level Yahoo Finance session cache (lives for Lambda container lifetime)
_yahoo_session: dict = {"crumb": None, "cookie_str": None, "expires": 0}

_YF_FIELDS = (
    "regularMarketPrice,regularMarketChange,regularMarketChangePercent,"
    "marketCap,trailingPE,forwardPE,priceToBook,priceToSalesTrailing12Months,"
    "enterpriseToEbitda,trailingAnnualDividendYield,trailingEps,"
    "fiftyTwoWeekHigh,fiftyTwoWeekLow,regularMarketVolume,beta,"
    "sector,industry,shortName,longName,currency,fullExchangeName"
)


def _get_yahoo_session():
    """Return (crumb, cookie_str) for authenticated Yahoo Finance API calls.
    Performs the fc.yahoo.com → getcrumb handshake once per cold start.
    Returns plain strings — safe to pass across threads.
    """
    import time
    import http.cookiejar
    from urllib.request import build_opener, HTTPCookieProcessor, Request as _Req

    now = time.time()
    if _yahoo_session["crumb"] and now < _yahoo_session["expires"]:
        return _yahoo_session["crumb"], _yahoo_session["cookie_str"]

    jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # Step 1: visit fc.yahoo.com to collect session cookies
    try:
        opener.open(_Req("https://fc.yahoo.com", headers=headers), timeout=10)
    except Exception as e:
        print(f"[DEBUG] fc.yahoo.com step: {e}")  # expected — may 404/redirect

    # Step 2: fetch crumb
    req = _Req("https://query1.finance.yahoo.com/v1/test/getcrumb", headers=headers)
    with opener.open(req, timeout=10) as resp:
        crumb = resp.read().decode().strip()

    # Extract cookies as a plain string for thread-safe concurrent use
    cookie_str = "; ".join(f"{c.name}={c.value}" for c in jar)

    print(f"[DEBUG] Yahoo crumb obtained: {crumb!r}, cookies: {len(cookie_str)} chars")
    _yahoo_session["crumb"] = crumb
    _yahoo_session["cookie_str"] = cookie_str
    _yahoo_session["expires"] = now + 3600
    return crumb, cookie_str


def _fetch_one_batch(batch, crumb, cookie_str):
    """Fetch one batch of tickers. Designed to be called concurrently across threads."""
    from urllib.request import Request as _Request, urlopen as _urlopen
    symbols = ','.join(batch)
    url = (
        f"https://query1.finance.yahoo.com/v7/finance/quote"
        f"?symbols={symbols}&crumb={crumb}&fields={_YF_FIELDS}"
    )
    req = _Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Cookie": cookie_str,
    })
    with _urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode())
    results = []
    for s in data.get('quoteResponse', {}).get('result', []):
        price = s.get('regularMarketPrice')
        if not price:
            continue
        div_yield = s.get('trailingAnnualDividendYield')
        if div_yield and div_yield < 1:
            div_yield = div_yield * 100  # convert 0.03 → 3.0 %
        results.append({
            "ticker": s.get('symbol', ''),
            "companyName": (s.get('shortName') or s.get('longName') or s.get('symbol', '')).strip(),
            "exchange": s.get('fullExchangeName', ''),
            "sector": s.get('sector', ''),
            "industry": s.get('industry', ''),
            "currency": s.get('currency', 'USD'),
            "price": price,
            "priceChange": s.get('regularMarketChange'),
            "priceChangePct": s.get('regularMarketChangePercent'),
            "marketCap": s.get('marketCap'),
            "peRatio": s.get('trailingPE'),
            "forwardPE": s.get('forwardPE'),
            "pbRatio": s.get('priceToBook'),
            "psRatio": s.get('priceToSalesTrailing12Months'),
            "evToEbitda": s.get('enterpriseToEbitda'),
            "dividendYield": div_yield,
            "week52High": s.get('fiftyTwoWeekHigh'),
            "week52Low": s.get('fiftyTwoWeekLow'),
            "volume": s.get('regularMarketVolume'),
            "beta": s.get('beta'),
            "eps": s.get('trailingEps'),
        })
    return results


def _fetch_stocks_batch(tickers, batch_size=50):
    """Fetch stock data using Yahoo Finance v7 quote API (concurrent batches).
    Uses crumb/cookie auth with ThreadPoolExecutor — all batches run in parallel.
    """
    try:
        crumb, cookie_str = _get_yahoo_session()
    except Exception as e:
        print(f"[DEBUG] Yahoo session error: {e}")
        return []

    batches = [tickers[i:i + batch_size] for i in range(0, len(tickers), batch_size)]
    print(f"[DEBUG] Fetching {len(tickers)} tickers in {len(batches)} concurrent batches")

    all_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(batches))) as executor:
        futures = {
            executor.submit(_fetch_one_batch, batch, crumb, cookie_str): idx
            for idx, batch in enumerate(batches)
        }
        for future in concurrent.futures.as_completed(futures):
            idx = futures[future]
            try:
                batch_results = future.result()
                all_results.extend(batch_results)
                print(f"[DEBUG] Batch {idx}: {len(batch_results)} stocks")
            except Exception as exc:
                print(f"[DEBUG] v7 batch fetch error (batch {idx}): {exc}")

    return all_results


def get_quote_data(ticker: str) -> dict:
    """Return rich market data for a single ticker using the v7 quote API.
    Returns: price, marketCap, peRatio, forwardPE, pbRatio, psRatio, evToEbitda,
             dividendYield, eps, beta, week52High, week52Low, volume, priceChangePct, etc.
    """
    try:
        results = _fetch_one_batch([ticker.upper()], *_get_yahoo_session())
        if not results:
            return {'statusCode': 404, 'body': json.dumps({'error': f'No data for {ticker}'})}
        return {'statusCode': 200, 'body': json.dumps(results[0])}
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}


def get_explore_markets():
    """Return available markets for the explore page."""
    markets = []
    for key, val in MARKET_TICKERS.items():
        is_screener = bool(val.get("screener_exchange") or val.get("exchange_mic"))
        if is_screener and key in _explore_ticker_list_cache:
            ticker_count = len(_explore_ticker_list_cache[key]["tickers"])
        elif is_screener:
            ticker_count = None  # unknown until first fetch
        else:
            ticker_count = len(val.get("tickers") or [])
        markets.append({
            "id": key,
            "name": val["name"],
            "description": val["description"],
            "region": val["region"],
            "continent": val.get("continent", "Other"),
            "ticker_count": ticker_count,
            "screener_based": is_screener,
        })
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

    tickers = _get_tickers_for_market(market_id, MARKET_TICKERS[market_id])
    tickers = list(dict.fromkeys(tickers))  # deduplicate, preserve order
    stocks = _fetch_stocks_batch(tickers)
    seen = set()
    stocks = [s for s in stocks if s["ticker"] not in seen and not seen.add(s["ticker"])]
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
        elif '/api/quote/' in path:
            ticker = path.split('/api/quote/')[-1]
            result = get_quote_data(ticker)
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
