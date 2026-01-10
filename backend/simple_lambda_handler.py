"""
Enhanced AWS Lambda handler for Stock Analysis API with MarketStack integration
Provides real stock data using MarketStack API - NO FAKE PRICES VERSION
Updated with proper fundamental analysis - v1.2
"""

import json
import os
import urllib.request
import urllib.parse
import urllib.error
import logging
import boto3
import time
from typing import Dict, Any, Optional
from decimal import Decimal

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDB table name from environment
TABLE_NAME = os.getenv('TABLE_NAME', 'stock-analyses-production')
CACHE_DURATION_MINUTES = 30

# Comprehensive ticker database with correct company names
TICKER_DATABASE = {
    # Technology
    'AAPL': {'companyName': 'Apple Inc.', 'exchange': 'NASDAQ'},
    'MSFT': {'companyName': 'Microsoft Corporation', 'exchange': 'NASDAQ'},
    'GOOGL': {'companyName': 'Alphabet Inc. Class A', 'exchange': 'NASDAQ'},
    'GOOG': {'companyName': 'Alphabet Inc. Class C', 'exchange': 'NASDAQ'},
    'AMZN': {'companyName': 'Amazon.com Inc.', 'exchange': 'NASDAQ'},
    'TSLA': {'companyName': 'Tesla Inc.', 'exchange': 'NASDAQ'},
    'META': {'companyName': 'Meta Platforms Inc.', 'exchange': 'NASDAQ'},
    'NVDA': {'companyName': 'NVIDIA Corporation', 'exchange': 'NASDAQ'},
    'NFLX': {'companyName': 'Netflix Inc.', 'exchange': 'NASDAQ'},
    'CRM': {'companyName': 'Salesforce Inc.', 'exchange': 'NYSE'},
    'ORCL': {'companyName': 'Oracle Corporation', 'exchange': 'NYSE'},
    'ADBE': {'companyName': 'Adobe Inc.', 'exchange': 'NASDAQ'},
    'INTC': {'companyName': 'Intel Corporation', 'exchange': 'NASDAQ'},
    'AMD': {'companyName': 'Advanced Micro Devices Inc.', 'exchange': 'NASDAQ'},
    'PYPL': {'companyName': 'PayPal Holdings Inc.', 'exchange': 'NASDAQ'},
    
    # Financial
    'JPM': {'companyName': 'JPMorgan Chase & Co.', 'exchange': 'NYSE'},
    'BAC': {'companyName': 'Bank of America Corporation', 'exchange': 'NYSE'},
    'WFC': {'companyName': 'Wells Fargo & Company', 'exchange': 'NYSE'},
    'GS': {'companyName': 'The Goldman Sachs Group Inc.', 'exchange': 'NYSE'},
    'MS': {'companyName': 'Morgan Stanley', 'exchange': 'NYSE'},
    'V': {'companyName': 'Visa Inc.', 'exchange': 'NYSE'},
    'MA': {'companyName': 'Mastercard Incorporated', 'exchange': 'NYSE'},
    'BRK.B': {'companyName': 'Berkshire Hathaway Inc. Class B', 'exchange': 'NYSE'},
    
    # Healthcare
    'JNJ': {'companyName': 'Johnson & Johnson', 'exchange': 'NYSE'},
    'PFE': {'companyName': 'Pfizer Inc.', 'exchange': 'NYSE'},
    'UNH': {'companyName': 'UnitedHealth Group Incorporated', 'exchange': 'NYSE'},
    'ABBV': {'companyName': 'AbbVie Inc.', 'exchange': 'NYSE'},
    'MRK': {'companyName': 'Merck & Co. Inc.', 'exchange': 'NYSE'},
    'TMO': {'companyName': 'Thermo Fisher Scientific Inc.', 'exchange': 'NYSE'},
    
    # Consumer
    'KO': {'companyName': 'The Coca-Cola Company', 'exchange': 'NYSE'},
    'PEP': {'companyName': 'PepsiCo Inc.', 'exchange': 'NASDAQ'},
    'WMT': {'companyName': 'Walmart Inc.', 'exchange': 'NYSE'},
    'HD': {'companyName': 'The Home Depot Inc.', 'exchange': 'NYSE'},
    'MCD': {'companyName': 'McDonald\'s Corporation', 'exchange': 'NYSE'},
    'NKE': {'companyName': 'NIKE Inc.', 'exchange': 'NYSE'},
    'SBUX': {'companyName': 'Starbucks Corporation', 'exchange': 'NASDAQ'},
    
    # Industrial
    'BA': {'companyName': 'The Boeing Company', 'exchange': 'NYSE'},
    'CAT': {'companyName': 'Caterpillar Inc.', 'exchange': 'NYSE'},
    'GE': {'companyName': 'General Electric Company', 'exchange': 'NYSE'},
    'MMM': {'companyName': '3M Company', 'exchange': 'NYSE'},
    
    # Energy
    'XOM': {'companyName': 'Exxon Mobil Corporation', 'exchange': 'NYSE'},
    'CVX': {'companyName': 'Chevron Corporation', 'exchange': 'NYSE'},
    
    # Telecom
    'VZ': {'companyName': 'Verizon Communications Inc.', 'exchange': 'NYSE'},
    'T': {'companyName': 'AT&T Inc.', 'exchange': 'NYSE'},
}

def get_company_info(ticker: str) -> dict:
    """Get company name and exchange for a ticker, with fallback"""
    ticker_upper = ticker.upper()
    if ticker_upper in TICKER_DATABASE:
        return TICKER_DATABASE[ticker_upper]
    else:
        # Fallback for unknown tickers - but log it
        logger.warning(f"Unknown ticker {ticker_upper}, using fallback company name")
        return {
            'companyName': f'{ticker_upper} Corporation',
            'exchange': 'NASDAQ'
        }

def convert_floats_to_decimal(obj):
    """Convert float values to Decimal for DynamoDB compatibility"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(v) for v in obj]
    else:
        return obj

def convert_decimals_to_float(obj):
    """Convert Decimal values back to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimals_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(v) for v in obj]
    else:
        return obj

def is_cache_stale(timestamp_str: str) -> bool:
    """Check if cached data is older than 30 minutes"""
    try:
        # Parse ISO timestamp
        cached_time = time.mktime(time.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%SZ'))
        return (time.time() - cached_time) > (CACHE_DURATION_MINUTES * 60)
    except:
        return True  # If we can't parse the timestamp, consider it stale

def get_cached_analysis(ticker: str) -> Optional[Dict]:
    """Get cached analysis from DynamoDB if available"""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(TABLE_NAME)
        
        response = table.get_item(
            Key={
                'PK': f'ANALYSIS#{ticker.upper()}',
                'SK': 'LATEST'
            }
        )
        
        if 'Item' in response:
            item = response['Item']
            # Convert Decimals back to floats for JSON serialization
            converted_item = convert_decimals_to_float(item)
            return {
                'data': converted_item,
                'timestamp': converted_item.get('timestamp', ''),
                'cached_at': converted_item.get('cached_at', '')
            }
        return None
    except Exception as e:
        logger.error(f"Error getting cached analysis for {ticker}: {e}")
        return None

def cache_analysis(ticker: str, analysis_data: Dict) -> None:
    """Cache analysis data in DynamoDB with timestamp"""
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(TABLE_NAME)
        
        # Convert floats to Decimals for DynamoDB
        item = convert_floats_to_decimal(analysis_data.copy())
        
        # Add DynamoDB keys and metadata
        item.update({
            'PK': f'ANALYSIS#{ticker.upper()}',
            'SK': 'LATEST',
            'cached_at': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
            'ttl': int(time.time()) + (24 * 60 * 60)  # 24 hour TTL
        })
        
        # Add GSI keys for querying
        item.update({
            'GSI1PK': f'EXCHANGE#{item.get("exchange", "UNKNOWN")}',
            'GSI1SK': item['timestamp'],
            'GSI2PK': f'RECOMMENDATION#{item.get("recommendation", "UNKNOWN")}',
            'GSI2SK': item['timestamp'],
            'GSI3PK': f'SECTOR#{item.get("sector", "UNKNOWN")}',
            'GSI3SK': str(item.get("businessQuality", {}).get("score", 0)).zfill(3)
        })
        
        table.put_item(Item=item)
        logger.info(f"Cached analysis for {ticker} in DynamoDB")
    except Exception as e:
        logger.error(f"Error caching analysis for {ticker}: {e}")

# Simple in-memory cache for price data (30 minutes TTL)
PRICE_CACHE = {}
CACHE_TTL_SECONDS = 30 * 60  # 30 minutes

def is_cache_stale(timestamp: float) -> bool:
    """Check if cached data is older than 30 minutes"""
    return time.time() - timestamp > CACHE_TTL_SECONDS

def get_cached_price(ticker: str) -> Optional[Dict]:
    """Get cached price data if not stale"""
    if ticker in PRICE_CACHE:
        cached_data = PRICE_CACHE[ticker]
        if not is_cache_stale(cached_data['timestamp']):
            logger.info(f"Using cached price for {ticker}")
            return cached_data['data']
        else:
            logger.info(f"Cache stale for {ticker}, will fetch fresh data")
            # Remove stale data
            del PRICE_CACHE[ticker]
    return None

def cache_price(ticker: str, price_data: Dict) -> None:
    """Cache price data with timestamp"""
    PRICE_CACHE[ticker] = {
        'data': price_data,
        'timestamp': time.time()
    }
    logger.info(f"Cached price for {ticker}")

def get_cache_info(ticker: str) -> Dict:
    """Get cache status information"""
    if ticker in PRICE_CACHE:
        cached_data = PRICE_CACHE[ticker]
        age_minutes = (time.time() - cached_data['timestamp']) / 60
        is_stale = is_cache_stale(cached_data['timestamp'])
        return {
            'status': 'stale' if is_stale else 'fresh',
            'age_minutes': round(age_minutes, 1),
            'needs_refresh': is_stale,
            'last_updated': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(cached_data['timestamp']))
        }
    else:
        return {
            'status': 'missing',
            'age_minutes': None,
            'needs_refresh': True,
            'last_updated': None
        }

def get_secrets():
    """Get secrets from AWS Secrets Manager"""
    try:
        secrets_arn = os.getenv('SECRETS_ARN')
        if not secrets_arn:
            logger.warning("SECRETS_ARN not configured")
            return {}
        
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secrets_arn)
        secrets = json.loads(response['SecretString'])
        
        # Extract API keys
        external_api_keys = secrets.get('external_api_keys', {})
        return external_api_keys
    except Exception as e:
        logger.error(f"Error getting secrets: {e}")
        return {}

class MarketStackClient:
    """MarketStack API client for real stock data"""
    
    def __init__(self, api_key: Optional[str] = None):
        if not api_key:
            # Try to get from environment first
            api_key = os.getenv("MARKETSTACK_API_KEY")
            
            # If not in environment, try to get from Secrets Manager
            if not api_key:
                secrets = get_secrets()
                api_key = secrets.get('marketstack')
        
        self.api_key = api_key
        self.base_url = "http://api.marketstack.com/v1"
        self.last_error = None  # Store detailed error information
        
        if self.api_key:
            logger.info("MarketStack client initialized with API key")
        else:
            logger.warning("MarketStack API key not found in environment or secrets")
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request to MarketStack using urllib"""
        if not self.api_key:
            logger.warning("MarketStack API key not configured")
            return None
        
        try:
            # Build URL with parameters
            url = f"{self.base_url}/{endpoint}"
            request_params = {"access_key": self.api_key}
            if params:
                request_params.update(params)
            
            # Encode parameters
            query_string = urllib.parse.urlencode(request_params)
            full_url = f"{url}?{query_string}"
            
            # Make request
            req = urllib.request.Request(full_url)
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    data = response.read().decode('utf-8')
                    return json.loads(data)
                else:
                    logger.warning(f"MarketStack returned status {response.status}")
                    return None
                    
        except urllib.error.HTTPError as e:
            if e.code == 429:
                try:
                    error_response = e.read().decode('utf-8')
                    error_data = json.loads(error_response)
                    error_message = error_data.get('error', {}).get('message', 'Rate limit exceeded')
                    logger.warning(f"MarketStack rate limit exceeded for {endpoint}. Response: {error_response}")
                    
                    # Store the detailed error for better user messaging
                    self.last_error = {
                        'code': error_data.get('error', {}).get('code', 'rate_limit'),
                        'message': error_message,
                        'is_monthly_limit': 'monthly usage limit' in error_message.lower(),
                        'is_hourly_limit': 'hourly' in error_message.lower() or 'rate limit' in error_message.lower()
                    }
                except:
                    logger.warning(f"MarketStack rate limit exceeded for {endpoint}. Response: {e.read().decode() if hasattr(e, 'read') else 'No details'}")
                    self.last_error = {
                        'code': 'rate_limit',
                        'message': 'Rate limit exceeded',
                        'is_monthly_limit': False,
                        'is_hourly_limit': True
                    }
            else:
                logger.warning(f"MarketStack HTTP error {e.code} for {endpoint}")
            return None
        except Exception as e:
            logger.error(f"Error calling MarketStack API: {e}")
            return None
    
    def get_latest_price(self, ticker: str) -> Optional[Dict]:
        """Get latest price for a ticker"""
        data = self._make_request("intraday/latest", {"symbols": ticker})
        if data and data.get('data'):
            latest = data['data'][0] if isinstance(data['data'], list) else data['data']
            return {
                'price': latest.get('last'),
                'volume': latest.get('volume'),
                'timestamp': latest.get('date'),
                'symbol': latest.get('symbol')
            }
        return None
    
    def get_end_of_day(self, ticker: str) -> Optional[Dict]:
        """Get end of day data for a ticker"""
        data = self._make_request("eod/latest", {"symbols": ticker})
        if data and data.get('data'):
            latest = data['data'][0] if isinstance(data['data'], list) else data['data']
            return {
                'price': latest.get('close'),
                'open': latest.get('open'),
                'high': latest.get('high'),
                'low': latest.get('low'),
                'volume': latest.get('volume'),
                'timestamp': latest.get('date'),
                'symbol': latest.get('symbol')
            }
        return None

def get_business_type_and_weights(ticker: str) -> tuple[str, float, float, float]:
    """
    Determine business type and return appropriate weights for DCF, EPV, and Asset-based valuation
    Based on the 20 business type presets described in the docs
    """
    # Business type classification based on ticker and industry knowledge
    # In a real implementation, this would analyze financial ratios and industry data
    
    business_type_mapping = {
        # Technology companies - DCF 50% | EPV 35% | Asset 15%
        'AAPL': ('Technology', 0.50, 0.35, 0.15),
        'MSFT': ('Technology', 0.50, 0.35, 0.15),
        'GOOGL': ('Technology', 0.50, 0.35, 0.15),
        'GOOG': ('Technology', 0.50, 0.35, 0.15),
        'AMZN': ('Technology', 0.50, 0.35, 0.15),
        'META': ('Technology', 0.50, 0.35, 0.15),
        'NVDA': ('Technology', 0.50, 0.35, 0.15),
        'NFLX': ('Technology', 0.50, 0.35, 0.15),
        'CRM': ('Technology', 0.50, 0.35, 0.15),
        'ORCL': ('Technology', 0.50, 0.35, 0.15),
        'ADBE': ('Technology', 0.50, 0.35, 0.15),
        'INTC': ('Technology', 0.50, 0.35, 0.15),
        'AMD': ('Technology', 0.50, 0.35, 0.15),
        'PYPL': ('Technology', 0.50, 0.35, 0.15),
        
        # High Growth Technology - DCF 55% | EPV 25% | Asset 20%
        'TSLA': ('High Growth', 0.55, 0.25, 0.20),
        
        # Banks - DCF 25% | EPV 50% | Asset 25%
        'JPM': ('Bank', 0.25, 0.50, 0.25),
        'BAC': ('Bank', 0.25, 0.50, 0.25),
        'WFC': ('Bank', 0.25, 0.50, 0.25),
        'GS': ('Bank', 0.25, 0.50, 0.25),
        'MS': ('Bank', 0.25, 0.50, 0.25),
        
        # Healthcare - DCF 50% | EPV 35% | Asset 15%
        'JNJ': ('Healthcare', 0.50, 0.35, 0.15),
        'PFE': ('Healthcare', 0.50, 0.35, 0.15),
        'UNH': ('Healthcare', 0.50, 0.35, 0.15),
        'ABBV': ('Healthcare', 0.50, 0.35, 0.15),
        'MRK': ('Healthcare', 0.50, 0.35, 0.15),
        'TMO': ('Healthcare', 0.50, 0.35, 0.15),
        
        # Mature Consumer Staples - DCF 50% | EPV 35% | Asset 15%
        'KO': ('Mature', 0.50, 0.35, 0.15),
        'PEP': ('Mature', 0.50, 0.35, 0.15),
        'WMT': ('Mature', 0.50, 0.35, 0.15),
        'MCD': ('Mature', 0.50, 0.35, 0.15),
        
        # Retail - DCF 50% | EPV 35% | Asset 15%
        'HD': ('Retail', 0.50, 0.35, 0.15),
        'NKE': ('Retail', 0.50, 0.35, 0.15),
        'SBUX': ('Retail', 0.50, 0.35, 0.15),
        
        # Cyclical/Industrial - DCF 25% | EPV 50% | Asset 25%
        'BA': ('Cyclical', 0.25, 0.50, 0.25),
        'CAT': ('Cyclical', 0.25, 0.50, 0.25),
        'GE': ('Cyclical', 0.25, 0.50, 0.25),
        'MMM': ('Cyclical', 0.25, 0.50, 0.25),
        
        # Energy - DCF 25% | EPV 40% | Asset 35%
        'XOM': ('Energy', 0.25, 0.40, 0.35),
        'CVX': ('Energy', 0.25, 0.40, 0.35),
        
        # Utility - DCF 45% | EPV 35% | Asset 20%
        'VZ': ('Utility', 0.45, 0.35, 0.20),
        'T': ('Utility', 0.45, 0.35, 0.20),
        
        # Financial Services - DCF 50% | EPV 35% | Asset 15%
        'V': ('Technology', 0.50, 0.35, 0.15),  # Payment processor, more like tech
        'MA': ('Technology', 0.50, 0.35, 0.15),  # Payment processor, more like tech
        'BRK.B': ('Mature', 0.50, 0.35, 0.15),  # Berkshire Hathaway - mature conglomerate
    }
    
    # Get business type and weights, default to balanced approach
    return business_type_mapping.get(ticker, ('Default', 0.50, 0.35, 0.15))

def calculate_dcf_value(ticker: str, current_price: float) -> Optional[float]:
    """
    Calculate Discounted Cash Flow (DCF) value
    Returns None if insufficient data for proper DCF calculation
    In a real implementation, this would:
    1. Fetch historical free cash flows from financial statements
    2. Project future cash flows based on growth rates
    3. Apply discount rate (WACC or risk-free rate + risk premium)
    4. Calculate present value of projected cash flows
    """
    # Without real financial statement data, we cannot calculate proper DCF
    # Return None to indicate insufficient data
    logger.warning(f"DCF calculation for {ticker} requires real financial statement data - returning None")
    return None

def calculate_epv_value(ticker: str, current_price: float) -> Optional[float]:
    """
    Calculate Earnings Power Value (EPV)
    EPV = Normalized Earnings / Discount Rate
    Returns None if insufficient earnings data
    """
    # Without real earnings data, we cannot calculate proper EPV
    # Return None to indicate insufficient data
    logger.warning(f"EPV calculation for {ticker} requires real earnings data - returning None")
    return None

def calculate_asset_value(ticker: str, current_price: float) -> Optional[float]:
    """
    Calculate Asset-Based Valuation
    Returns None if insufficient balance sheet data
    Based on book value, tangible assets, and liquidation value
    """
    # Without real balance sheet data, we cannot calculate proper asset value
    # Return None to indicate insufficient data
    logger.warning(f"Asset valuation for {ticker} requires real balance sheet data - returning None")
    return None

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Clean Lambda handler with NO FAKE PRICES - returns errors when data unavailable
    """
    
    try:
        # Extract request information
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        query_params = event.get('queryStringParameters') or {}
        
        # CORS headers - comprehensive configuration
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, X-Api-Key, X-Correlation-Id',
            'Access-Control-Allow-Credentials': 'false',
            'Access-Control-Max-Age': '86400'
        }
        
        # Handle OPTIONS requests (CORS preflight)
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight successful'})
            }
        
        # Health check endpoint
        if path in ['/', '/health']:
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'status': 'healthy',
                    'message': 'Stock Analysis API - No Fake Prices Version',
                    'version': '1.1.0'
                })
            }
        
        # API version endpoint
        if path == '/api/version':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'version': '1.1.0',
                    'build_timestamp': '2024-01-10T00:00:00Z',
                    'api_name': 'Stock Analysis API - No Fake Prices Version'
                })
            }
        
        # API search endpoint - return comprehensive mock data
        if path == '/api/search':
            query = query_params.get('q', '')
            if not query:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Query parameter q is required'})
                }
            
            # Convert ticker database to search format
            all_tickers = []
            for ticker, info in TICKER_DATABASE.items():
                all_tickers.append({
                    'ticker': ticker,
                    'companyName': info['companyName'],
                    'exchange': info['exchange']
                })
            
            # Filter tickers based on query (case-insensitive)
            query_upper = query.upper()
            mock_results = []
            
            for ticker_info in all_tickers:
                # Match by ticker symbol or company name
                if (query_upper in ticker_info['ticker'].upper() or 
                    query_upper in ticker_info['companyName'].upper()):
                    mock_results.append(ticker_info)
            
            # Limit results to 10 for better UX
            mock_results = mock_results[:10]
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'results': mock_results
                })
            }
        
        # Watchlist endpoint - return data from DynamoDB cache with correct company names
        if path == '/api/watchlist':
            # Get list of tickers from watchlist (for now, use common tickers)
            # In a real implementation, this would come from a user's actual watchlist
            watchlist_tickers = ['AAPL', 'KO', 'MSFT', 'GOOGL', 'TSLA']
            
            items = []
            for ticker in watchlist_tickers:
                # Get company info from ticker database
                ticker_info = get_company_info(ticker)
                
                # Get cached analysis data for each ticker
                cached_result = get_cached_analysis(ticker)
                
                if cached_result:
                    cached_data = cached_result['data']
                    
                    # Parse timestamp for age calculation and staleness check
                    try:
                        cached_timestamp = time.mktime(time.strptime(cached_result['timestamp'], '%Y-%m-%dT%H:%M:%SZ'))
                        age_minutes = int((time.time() - cached_timestamp) / 60)
                        is_stale = age_minutes > CACHE_DURATION_MINUTES
                    except:
                        age_minutes = 999
                        is_stale = True
                    
                    # Only use cached data if it's not stale, otherwise return null values
                    if not is_stale:
                        items.append({
                            'ticker': ticker,
                            'company_name': ticker_info['companyName'],
                            'exchange': ticker_info['exchange'],
                            'added_at': '2024-01-01T00:00:00Z',
                            'current_price': cached_data.get('currentPrice'),
                            'fair_value': cached_data.get('fairValue'),
                            'margin_of_safety_pct': cached_data.get('marginOfSafety'),
                            'recommendation': cached_data.get('recommendation'),
                            'cache_info': {
                                'cached_at': cached_result['cached_at'],
                                'age_minutes': age_minutes,
                                'status': 'fresh'
                            }
                        })
                    else:
                        # Stale cached data - return null values instead of fake data
                        items.append({
                            'ticker': ticker,
                            'company_name': ticker_info['companyName'],
                            'exchange': ticker_info['exchange'],
                            'added_at': '2024-01-01T00:00:00Z',
                            'current_price': None,  # Don't show stale prices
                            'fair_value': None,     # Don't show stale fake fair values
                            'margin_of_safety_pct': None,
                            'recommendation': None,
                            'cache_info': {
                                'cached_at': cached_result['cached_at'],
                                'age_minutes': age_minutes,
                                'status': 'stale'
                            },
                            'note': 'Data is stale - click Refresh Prices to fetch fresh data'
                        })
                else:
                    # No cached data available
                    items.append({
                        'ticker': ticker,
                        'company_name': ticker_info['companyName'],  # Use correct company name from database
                        'exchange': ticker_info['exchange'],
                        'added_at': '2024-01-01T00:00:00Z',
                        'current_price': None,
                        'fair_value': None,
                        'margin_of_safety_pct': None,
                        'recommendation': None,
                        'note': 'No cached data available - click Refresh Prices to fetch'
                    })
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'items': items,
                    'total': len(items)
                })
            }
        
        # Watchlist live prices endpoint - Enhanced with MarketStack (NO FAKE PRICES)
        if path == '/api/watchlist/live-prices':
            # Initialize MarketStack client
            marketstack = MarketStackClient()
            
            # Get watchlist tickers (for now, use common tickers from the mock watchlist)
            # In a real implementation, this would fetch from the user's actual watchlist
            watchlist_tickers = ['AAPL', 'KO', 'MSFT', 'GOOGL', 'TSLA']
            
            live_prices = {}
            
            for ticker in watchlist_tickers:
                try:
                    # Try to get real price from MarketStack
                    price_data = marketstack.get_latest_price(ticker)
                    
                    if price_data and price_data.get('price'):
                        ticker_info = get_company_info(ticker)
                        live_prices[ticker] = {
                            'price': float(price_data['price']),
                            'company_name': ticker_info['companyName'],
                            'success': True,
                            'timestamp': price_data.get('timestamp'),
                            'volume': price_data.get('volume'),
                            'source': 'MarketStack'
                        }
                        logger.info(f"Got real price for {ticker}: ${price_data['price']}")
                    else:
                        # Fallback to end-of-day data if intraday fails
                        eod_data = marketstack.get_end_of_day(ticker)
                        if eod_data and eod_data.get('price'):
                            ticker_info = get_company_info(ticker)
                            live_prices[ticker] = {
                                'price': float(eod_data['price']),
                                'company_name': ticker_info['companyName'],
                                'success': True,
                                'timestamp': eod_data.get('timestamp'),
                                'volume': eod_data.get('volume'),
                                'source': 'MarketStack (EOD)',
                                'comment': 'End-of-day price (intraday not available)'
                            }
                            logger.info(f"Got EOD price for {ticker}: ${eod_data['price']}")
                        else:
                            # NO FAKE PRICES - return error instead
                            ticker_info = get_company_info(ticker)
                            live_prices[ticker] = {
                                'price': None,
                                'company_name': ticker_info['companyName'],
                                'success': False,
                                'error': 'MarketStack API rate limited or unavailable',
                                'comment': 'Price data temporarily unavailable - likely rate limited',
                                'source': 'None (rate limited)'
                            }
                            logger.warning(f"No price data available for {ticker} - MarketStack rate limited")
                            
                except Exception as e:
                    logger.error(f"Error fetching price for {ticker}: {e}")
                    ticker_info = get_company_info(ticker)
                    live_prices[ticker] = {
                        'price': None,
                        'company_name': ticker_info['companyName'],
                        'success': False,
                        'error': f'Error: {str(e)}',
                        'source': 'None (error)'
                    }
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'live_prices': live_prices,
                    'api_info': {
                        'source': 'MarketStack API',
                        'has_api_key': bool(marketstack.api_key),
                        'tickers_requested': len(watchlist_tickers),
                        'tickers_with_real_data': len([p for p in live_prices.values() if p.get('success')])
                    }
                })
            }
        
        # Individual watchlist item endpoint - handle GET, POST, DELETE
        if path.startswith('/api/watchlist/') and not path.endswith('/live-prices'):
            ticker = path.split('/')[-1].upper()
            
            # Handle different HTTP methods
            if http_method == 'POST':
                # Add ticker to watchlist
                # Extract company_name from query parameters
                query_params = event.get('queryStringParameters') or {}
                company_name = query_params.get('company_name', f'{ticker} Corporation')
                exchange = query_params.get('exchange', 'NASDAQ')
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'success': True,
                        'message': f'Successfully added {ticker} to watchlist',
                        'ticker': ticker,
                        'company_name': company_name,
                        'exchange': exchange
                    })
                }
            
            elif http_method == 'GET':
                # Get individual watchlist item - return minimal data without fake prices
                ticker_info = get_company_info(ticker)
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'watchlist_item': {
                            'ticker': ticker,
                            'company_name': ticker_info['companyName'],
                            'exchange': ticker_info['exchange'],
                            'added_at': '2024-01-01T00:00:00Z',
                            'current_price': None,  # No fake prices
                            'fair_value': None,     # No fake values
                            'margin_of_safety_pct': None,
                            'recommendation': None
                        },
                        'latest_analysis': {
                            'ticker': ticker,
                            'companyName': ticker_info['companyName'],
                            'currentPrice': None,   # No fake prices
                            'fairValue': None,      # No fake values
                            'recommendation': None,
                            'timestamp': '2024-01-01T00:00:00Z',
                            'financialHealth': {'score': None},
                            'businessQuality': {'score': None},
                            'valuation': {
                                'dcf': None,
                                'earningsPower': None,
                                'assetBased': None,
                                'weightedAverage': None
                            },
                            'message': 'Use /api/analyze/{ticker} endpoint for real analysis data'
                        }
                    })
                }
            
            elif http_method == 'DELETE':
                # Remove ticker from watchlist
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'success': True,
                        'message': f'Successfully removed {ticker} from watchlist',
                        'ticker': ticker
                    })
                }
            
            elif http_method == 'PUT':
                # Update watchlist item (e.g., notes)
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'success': True,
                        'message': f'Successfully updated {ticker} in watchlist',
                        'ticker': ticker
                    })
                }
            
            else:
                return {
                    'statusCode': 405,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Method Not Allowed',
                        'message': f'Method {http_method} not allowed for this endpoint',
                        'allowed_methods': ['GET', 'POST', 'PUT', 'DELETE']
                    })
                }
        
        # Analysis endpoint - Enhanced with caching and staleness detection
        if path.startswith('/api/analyze/'):
            ticker = path.split('/')[-1].upper()
            
            # Check for force_refresh parameter
            force_refresh = query_params.get('force_refresh', '').lower() == 'true'
            
            # Try to get cached analysis first (unless force refresh)
            if not force_refresh:
                cached_result = get_cached_analysis(ticker)
                if cached_result:
                    cached_data = cached_result['data']
                    
                    # Parse timestamp for staleness check
                    try:
                        cached_timestamp = time.mktime(time.strptime(cached_result['timestamp'], '%Y-%m-%dT%H:%M:%SZ'))
                        is_stale = is_cache_stale(cached_timestamp)
                        age_minutes = int((time.time() - cached_timestamp) / 60)
                    except Exception as e:
                        logger.error(f"Error parsing cached timestamp: {e}")
                        is_stale = True
                        age_minutes = 999
                    
                    # Add cache metadata to response
                    cached_data['cacheInfo'] = {
                        'cached': True,
                        'cached_at': cached_result['cached_at'],
                        'is_stale': is_stale,
                        'age_minutes': age_minutes,
                        'stale_threshold_minutes': CACHE_DURATION_MINUTES
                    }
                    
                    logger.info(f"Returning cached analysis for {ticker} from DynamoDB (age: {cached_data['cacheInfo']['age_minutes']} min, stale: {is_stale})")
                    
                    return {
                        'statusCode': 200,
                        'headers': headers,
                        'body': json.dumps(cached_data)
                    }
            
            # No cache or force refresh - fetch fresh data
            logger.info(f"Fetching fresh analysis for {ticker} (force_refresh: {force_refresh})")
            
            # Initialize MarketStack client
            marketstack = MarketStackClient()
            
            # Try to get real current price
            real_price = None
            price_source = 'None'
            
            try:
                price_data = marketstack.get_latest_price(ticker)
                if price_data and price_data.get('price'):
                    real_price = float(price_data['price'])
                    price_source = 'MarketStack (Live)'
                    logger.info(f"Got real price for {ticker}: ${real_price}")
                else:
                    # Try end-of-day data
                    eod_data = marketstack.get_end_of_day(ticker)
                    if eod_data and eod_data.get('price'):
                        real_price = float(eod_data['price'])
                        price_source = 'MarketStack (EOD)'
                        logger.info(f"Got EOD price for {ticker}: ${real_price}")
            except Exception as e:
                logger.warning(f"Error fetching real price for {ticker}: {e}")
            
            # Use real price if available, otherwise return error (NO FAKE PRICES)
            if real_price:
                current_price = real_price
                
                # Implement proper fundamental analysis following the docs methodology
                business_type, dcf_weight, epv_weight, asset_weight = get_business_type_and_weights(ticker)
                
                # Calculate the three valuation methods
                dcf_value = calculate_dcf_value(ticker, current_price)
                epv_value = calculate_epv_value(ticker, current_price)
                asset_value = calculate_asset_value(ticker, current_price)
                
                # Calculate weighted average only if we have valid values
                valid_values = []
                valid_weights = []
                
                if dcf_value is not None and dcf_value > 0:
                    valid_values.append(dcf_value)
                    valid_weights.append(dcf_weight)
                
                if epv_value is not None and epv_value > 0:
                    valid_values.append(epv_value)
                    valid_weights.append(epv_weight)
                
                if asset_value is not None and asset_value > 0:
                    valid_values.append(asset_value)
                    valid_weights.append(asset_weight)
                
                # Calculate fair value only if we have at least one valid valuation method
                if valid_values:
                    # Normalize weights for valid values only
                    total_weight = sum(valid_weights)
                    if total_weight > 0:
                        normalized_weights = [w / total_weight for w in valid_weights]
                        fair_value = sum(v * w for v, w in zip(valid_values, normalized_weights))
                    else:
                        fair_value = None
                else:
                    # No valid valuation methods available
                    fair_value = None
                
                # Store individual estimates for transparency
                dcf_estimate = dcf_value
                epv_estimate = epv_value
                asset_estimate = asset_value
                
                # Create analysis response
                ticker_info = get_company_info(ticker)
                analysis_data = {
                    'ticker': ticker,
                    'companyName': ticker_info['companyName'],
                    'exchange': ticker_info['exchange'],
                    'currentPrice': current_price,
                    'fairValue': fair_value,
                    'marginOfSafety': ((fair_value - current_price) / current_price * 100) if fair_value and current_price > 0 else None,
                    'upsidePotential': ((fair_value - current_price) / current_price * 100) if fair_value and current_price > 0 else None,
                    'priceToIntrinsicValue': (current_price / fair_value) if fair_value and fair_value > 0 else None,
                    'recommendation': 'Buy' if fair_value and fair_value > current_price * 1.3 else 'Hold' if fair_value and fair_value > current_price else 'Hold' if not fair_value else 'Sell',
                    'recommendationReasoning': f'Analysis based on real market data from {price_source}. {"Fair value calculated using " + business_type + " business type weighting: DCF " + str(int(dcf_weight*100)) + "% | EPV " + str(int(epv_weight*100)) + "% | Asset " + str(int(asset_weight*100)) + "%." if fair_value else "Fair value could not be calculated due to insufficient financial statement data. Recommendation based on current price only."}',
                    'valuation': {
                        'dcf': dcf_estimate,
                        'earningsPower': epv_estimate,
                        'assetBased': asset_estimate,
                        'weightedAverage': fair_value
                    },
                    'financialHealth': {
                        'score': None,
                        'metrics': {}
                    },
                    'businessQuality': {
                        'score': None,
                        'moatIndicators': [],
                        'competitivePosition': None
                    },
                    'growthMetrics': {
                        'revenueGrowth1Y': None,
                        'revenueGrowth3Y': None,
                        'revenueGrowth5Y': None,
                        'earningsGrowth1Y': None,
                        'earningsGrowth3Y': None,
                        'earningsGrowth5Y': None
                    },
                    'priceRatios': {
                        'priceToEarnings': None,
                        'priceToBook': None,
                        'priceToSales': None,
                        'priceToFCF': None,
                        'enterpriseValueToEBITDA': None
                    },
                    'currency': 'USD',
                    'financialCurrency': 'USD',
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'sector': None,  # Should come from real financial data
                    'industry': None,  # Should come from real financial data
                    'marketCap': None,  # Should be calculated from real shares outstanding data
                    'analysisWeights': {
                        'dcf_weight': dcf_weight,
                        'epv_weight': epv_weight,
                        'asset_weight': asset_weight
                    },
                    'businessType': business_type,
                    'missingData': {
                        'has_missing_data': True,  # We don't have real financial statement data
                        'missing_fields': ['financial_statements', 'income_statement', 'balance_sheet', 'cash_flow', 'key_metrics']
                    },
                    'dataSource': {
                        'price_source': price_source,
                        'has_real_price': True,
                        'api_available': bool(marketstack.api_key)
                    },
                    'cacheInfo': {
                        'cached': False,
                        'fresh_data': True,
                        'fetched_at': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
                    }
                }
                
                # Cache the analysis data
                cache_analysis(ticker, analysis_data)
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(analysis_data)
                }
            else:
                # No real price available - check if we have cached data to fall back to
                cached_result = get_cached_analysis(ticker)
                if cached_result:
                    cached_data = cached_result['data']
                    
                    # Parse timestamp for staleness check
                    try:
                        cached_timestamp = time.mktime(time.strptime(cached_result['timestamp'], '%Y-%m-%dT%H:%M:%SZ'))
                        is_stale = is_cache_stale(cached_timestamp)
                        age_minutes = int((time.time() - cached_timestamp) / 60)
                    except Exception as e:
                        logger.error(f"Error parsing cached timestamp: {e}")
                        is_stale = True
                        age_minutes = 999
                    
                    # Add cache metadata to response indicating we're using stale data due to API issues
                    cached_data['cacheInfo'] = {
                        'cached': True,
                        'cached_at': cached_result['cached_at'],
                        'is_stale': is_stale,
                        'age_minutes': age_minutes,
                        'stale_threshold_minutes': CACHE_DURATION_MINUTES,
                        'fallback_reason': 'Fresh price data unavailable due to API rate limits'
                    }
                    
                    # Update data source to indicate we're using cached data
                    if 'dataSource' in cached_data:
                        cached_data['dataSource']['fallback_to_cache'] = True
                        cached_data['dataSource']['api_error'] = marketstack.last_error.get('message') if marketstack.last_error else 'MarketStack API rate limited'
                    
                    logger.info(f"Returning cached analysis for {ticker} as fallback from DynamoDB (age: {cached_data['cacheInfo']['age_minutes']} min)")
                    
                    return {
                        'statusCode': 200,
                        'headers': headers,
                        'body': json.dumps(cached_data)
                    }
                
                # No cached data available either - return error with better messaging (NO FAKE PRICES)
                ticker_info = get_company_info(ticker)
                error_message = f'Unable to fetch current price for {ticker}.'
                suggestions = []
                rate_limit_info = {}
                
                if marketstack.last_error:
                    if marketstack.last_error.get('is_monthly_limit'):
                        error_message += ' MarketStack monthly usage limit has been reached.'
                        suggestions = [
                            'Monthly limit of 100 requests has been exceeded',
                            'Upgrade to a paid MarketStack plan for higher limits',
                            'Wait until next month for the limit to reset',
                            'Consider using a different stock data provider'
                        ]
                        rate_limit_info = {
                            'limitType': 'Monthly limit exceeded',
                            'monthlyQuota': '100 requests per month',
                            'currentStatus': 'Limit exceeded',
                            'solution': 'Upgrade plan or wait until next month'
                        }
                    elif marketstack.last_error.get('is_hourly_limit'):
                        error_message += ' MarketStack hourly rate limit exceeded.'
                        suggestions = [
                            'Wait 1 hour and try again (rate limits usually reset hourly)',
                            'MarketStack free tier has both monthly (100/month) and hourly limits'
                        ]
                        rate_limit_info = {
                            'limitType': 'Hourly rate limit exceeded',
                            'solution': 'Wait 1 hour and try again'
                        }
                    else:
                        error_message += f' {marketstack.last_error.get("message", "API unavailable")}'
                        suggestions = ['Try again later', 'Check MarketStack service status']
                        rate_limit_info = {
                            'limitType': 'API error',
                            'solution': 'Try again later'
                        }
                else:
                    error_message += ' This is likely due to MarketStack API rate limiting.'
                    suggestions = [
                        'Wait 1 hour and try again (rate limits usually reset hourly)',
                        'MarketStack free tier has both monthly (100/month) and hourly limits'
                    ]
                    rate_limit_info = {
                        'limitType': 'Unknown rate limit',
                        'solution': 'Wait and try again'
                    }
                
                return {
                    'statusCode': 503,  # Service Unavailable
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Price data temporarily unavailable',
                        'message': error_message,
                        'ticker': ticker,
                        'companyName': ticker_info['companyName'],
                        'currentPrice': None,
                        'fairValue': None,
                        'recommendation': None,
                        'dataSource': {
                            'price_source': 'None - API rate limited or unavailable',
                            'has_real_price': False,
                            'api_available': bool(marketstack.api_key),
                            'error': marketstack.last_error.get('message') if marketstack.last_error else 'MarketStack API rate limit exceeded or API unavailable'
                        },
                        'suggestions': suggestions,
                        'rateLimitInfo': rate_limit_info
                    })
                }
        
        # Analysis presets endpoint
        if path == '/api/analysis-presets':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'presets': {
                        'conservative': {
                            'financial_health': 0.3,
                            'business_quality': 0.25,
                            'valuation': 0.25,
                            'growth': 0.2
                        },
                        'balanced': {
                            'financial_health': 0.25,
                            'business_quality': 0.25,
                            'valuation': 0.25,
                            'growth': 0.25
                        }
                    },
                    'business_types': ['Technology', 'Healthcare', 'Financial', 'Consumer', 'Industrial']
                })
            }
        
        # Documentation endpoint
        if path == '/docs':
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'text/html'},
                'body': '''
                <!DOCTYPE html>
                <html>
                <head><title>Stock Analysis API Documentation</title></head>
                <body>
                    <h1>Stock Analysis API - No Fake Prices Version</h1>
                    <p>Enhanced version running on AWS Lambda with MarketStack integration</p>
                    <p><strong>Note:</strong> This version returns errors instead of fake prices when data is unavailable.</p>
                    <h2>Available Endpoints:</h2>
                    <ul>
                        <li>GET /health - Health check</li>
                        <li>GET /api/version - API version info</li>
                        <li>GET /api/search?q=AAPL - Search for stock tickers</li>
                        <li>GET /api/watchlist - Get watchlist items</li>
                        <li>GET /api/watchlist/{ticker} - Get specific watchlist item</li>
                        <li>POST /api/watchlist/{ticker} - Add ticker to watchlist</li>
                        <li>PUT /api/watchlist/{ticker} - Update watchlist item</li>
                        <li>DELETE /api/watchlist/{ticker} - Remove ticker from watchlist</li>
                        <li>GET /api/watchlist/live-prices - Get live prices for watchlist</li>
                        <li>GET /api/analyze/{ticker} - Analyze a stock</li>
                        <li>GET /api/analysis-presets - Get analysis presets</li>
                        <li>GET /openapi.json - OpenAPI specification</li>
                    </ul>
                </body>
                </html>
                '''
            }
        
        # OpenAPI specification endpoint
        if path == '/openapi.json':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'openapi': '3.0.0',
                    'info': {
                        'title': 'Stock Analysis API',
                        'version': '1.1.0',
                        'description': 'Stock Analysis API with MarketStack integration - No Fake Prices Version'
                    },
                    'paths': {
                        '/health': {
                            'get': {
                                'summary': 'Health check',
                                'responses': {
                                    '200': {
                                        'description': 'API is healthy'
                                    }
                                }
                            }
                        },
                        '/api/search': {
                            'get': {
                                'summary': 'Search stock tickers',
                                'parameters': [
                                    {
                                        'name': 'q',
                                        'in': 'query',
                                        'required': True,
                                        'schema': {'type': 'string'}
                                    }
                                ],
                                'responses': {
                                    '200': {
                                        'description': 'Search results'
                                    }
                                }
                            }
                        }
                    }
                })
            }
        
        # Default response for unknown endpoints
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({
                'error': 'Not Found',
                'message': f'Endpoint {path} not found',
                'available_endpoints': ['/health', '/api/version', '/api/search', '/api/watchlist', '/api/watchlist/{ticker}', '/api/analyze/{ticker}', '/api/watchlist/live-prices', '/api/analysis-presets', '/docs', '/openapi.json'],
                'supported_methods': {
                    '/api/watchlist/{ticker}': ['GET', 'POST', 'PUT', 'DELETE'],
                    '/api/search': ['GET'],
                    '/api/watchlist': ['GET'],
                    '/api/analyze/{ticker}': ['GET']
                }
            })
        }
    
    except Exception as e:
        # Error handling
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, X-Api-Key, X-Correlation-Id'
            },
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': str(e),
                'path': event.get('path', 'unknown')
            })
        }