"""
Stock Data Lambda - Handles stock price data and market information
Dependencies: stdlib only (urllib), optional yfinance
"""
import json
import os
import boto3
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
            'currency': currency,
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

        # Fetch ticker info for company name
        name = ticker
        try:
            info_url = f"https://api.marketstack.com/v1/tickers/{ticker}?{urlencode({'access_key': api_key})}"
            info_data = _urllib_get(info_url)
            name = info_data.get('name') or ticker
        except Exception:
            pass

        return {
            'ticker': ticker,
            'name': name,
            'price': price,
            'currentPrice': price,
            'currency': item.get('adj_currency') or 'USD',
            'exchange': item.get('exchange', ''),
            'source': 'marketstack'
        }
    except Exception as e:
        return {'error': str(e)}


def get_ticker_data(ticker: str) -> dict:
    """Get stock ticker data - MarketStack (paid) first, Yahoo Finance fallback"""
    # Try MarketStack first (paid plan, HTTPS, no IP restrictions)
    ms_data = get_ticker_data_marketstack(ticker)
    if 'error' not in ms_data:
        return {
            'statusCode': 200,
            'body': json.dumps(ms_data)
        }

    # Fall back to Yahoo Finance unofficial API
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
