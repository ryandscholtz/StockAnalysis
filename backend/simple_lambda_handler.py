"""
Enhanced AWS Lambda handler for Stock Analysis API with MarketStack integration
Provides real stock data using MarketStack API
"""

import json
import os
import urllib.request
import urllib.parse
import urllib.error
import logging
import boto3
from typing import Dict, Any, Optional

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

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
                logger.warning("MarketStack rate limit exceeded")
            else:
                logger.warning(f"MarketStack HTTP error: {e.code}")
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

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Simplified Lambda handler that provides basic API responses
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
                    'message': 'Stock Analysis API - Simplified Handler',
                    'version': '1.0.0'
                })
            }
        
        # API version endpoint
        if path == '/api/version':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'version': '1.0.0',
                    'build_timestamp': '2024-01-01T00:00:00Z',
                    'api_name': 'Stock Analysis API - Simplified Handler'
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
            
            # Comprehensive list of popular tickers for search
            all_tickers = [
                # Technology
                {'ticker': 'AAPL', 'companyName': 'Apple Inc.', 'exchange': 'NASDAQ'},
                {'ticker': 'MSFT', 'companyName': 'Microsoft Corporation', 'exchange': 'NASDAQ'},
                {'ticker': 'GOOGL', 'companyName': 'Alphabet Inc. Class A', 'exchange': 'NASDAQ'},
                {'ticker': 'GOOG', 'companyName': 'Alphabet Inc. Class C', 'exchange': 'NASDAQ'},
                {'ticker': 'AMZN', 'companyName': 'Amazon.com Inc.', 'exchange': 'NASDAQ'},
                {'ticker': 'TSLA', 'companyName': 'Tesla Inc.', 'exchange': 'NASDAQ'},
                {'ticker': 'META', 'companyName': 'Meta Platforms Inc.', 'exchange': 'NASDAQ'},
                {'ticker': 'NVDA', 'companyName': 'NVIDIA Corporation', 'exchange': 'NASDAQ'},
                {'ticker': 'NFLX', 'companyName': 'Netflix Inc.', 'exchange': 'NASDAQ'},
                {'ticker': 'CRM', 'companyName': 'Salesforce Inc.', 'exchange': 'NYSE'},
                {'ticker': 'ORCL', 'companyName': 'Oracle Corporation', 'exchange': 'NYSE'},
                {'ticker': 'ADBE', 'companyName': 'Adobe Inc.', 'exchange': 'NASDAQ'},
                {'ticker': 'INTC', 'companyName': 'Intel Corporation', 'exchange': 'NASDAQ'},
                {'ticker': 'AMD', 'companyName': 'Advanced Micro Devices Inc.', 'exchange': 'NASDAQ'},
                {'ticker': 'PYPL', 'companyName': 'PayPal Holdings Inc.', 'exchange': 'NASDAQ'},
                
                # Financial
                {'ticker': 'JPM', 'companyName': 'JPMorgan Chase & Co.', 'exchange': 'NYSE'},
                {'ticker': 'BAC', 'companyName': 'Bank of America Corporation', 'exchange': 'NYSE'},
                {'ticker': 'WFC', 'companyName': 'Wells Fargo & Company', 'exchange': 'NYSE'},
                {'ticker': 'GS', 'companyName': 'The Goldman Sachs Group Inc.', 'exchange': 'NYSE'},
                {'ticker': 'MS', 'companyName': 'Morgan Stanley', 'exchange': 'NYSE'},
                {'ticker': 'V', 'companyName': 'Visa Inc.', 'exchange': 'NYSE'},
                {'ticker': 'MA', 'companyName': 'Mastercard Incorporated', 'exchange': 'NYSE'},
                {'ticker': 'BRK.B', 'companyName': 'Berkshire Hathaway Inc. Class B', 'exchange': 'NYSE'},
                
                # Healthcare
                {'ticker': 'JNJ', 'companyName': 'Johnson & Johnson', 'exchange': 'NYSE'},
                {'ticker': 'PFE', 'companyName': 'Pfizer Inc.', 'exchange': 'NYSE'},
                {'ticker': 'UNH', 'companyName': 'UnitedHealth Group Incorporated', 'exchange': 'NYSE'},
                {'ticker': 'ABBV', 'companyName': 'AbbVie Inc.', 'exchange': 'NYSE'},
                {'ticker': 'MRK', 'companyName': 'Merck & Co. Inc.', 'exchange': 'NYSE'},
                {'ticker': 'TMO', 'companyName': 'Thermo Fisher Scientific Inc.', 'exchange': 'NYSE'},
                
                # Consumer
                {'ticker': 'KO', 'companyName': 'The Coca-Cola Company', 'exchange': 'NYSE'},
                {'ticker': 'PEP', 'companyName': 'PepsiCo Inc.', 'exchange': 'NASDAQ'},
                {'ticker': 'WMT', 'companyName': 'Walmart Inc.', 'exchange': 'NYSE'},
                {'ticker': 'HD', 'companyName': 'The Home Depot Inc.', 'exchange': 'NYSE'},
                {'ticker': 'MCD', 'companyName': 'McDonald\'s Corporation', 'exchange': 'NYSE'},
                {'ticker': 'NKE', 'companyName': 'NIKE Inc.', 'exchange': 'NYSE'},
                {'ticker': 'SBUX', 'companyName': 'Starbucks Corporation', 'exchange': 'NASDAQ'},
                
                # Industrial
                {'ticker': 'BA', 'companyName': 'The Boeing Company', 'exchange': 'NYSE'},
                {'ticker': 'CAT', 'companyName': 'Caterpillar Inc.', 'exchange': 'NYSE'},
                {'ticker': 'GE', 'companyName': 'General Electric Company', 'exchange': 'NYSE'},
                {'ticker': 'MMM', 'companyName': '3M Company', 'exchange': 'NYSE'},
                
                # Energy
                {'ticker': 'XOM', 'companyName': 'Exxon Mobil Corporation', 'exchange': 'NYSE'},
                {'ticker': 'CVX', 'companyName': 'Chevron Corporation', 'exchange': 'NYSE'},
                
                # Telecom
                {'ticker': 'VZ', 'companyName': 'Verizon Communications Inc.', 'exchange': 'NYSE'},
                {'ticker': 'T', 'companyName': 'AT&T Inc.', 'exchange': 'NYSE'},
            ]
            
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
        
        # Watchlist endpoint - return mock data
        if path == '/api/watchlist':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'items': [
                        {
                            'ticker': 'AAPL',
                            'company_name': 'Apple Inc.',
                            'exchange': 'NASDAQ',
                            'added_at': '2024-01-01T00:00:00Z',
                            'current_price': 150.00,
                            'fair_value': 180.00,
                            'margin_of_safety_pct': 16.67,
                            'recommendation': 'BUY'
                        }
                    ],
                    'total': 1
                })
            }
        
        # Watchlist live prices endpoint - Enhanced with MarketStack (MUST BE BEFORE individual item handler)
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
                        live_prices[ticker] = {
                            'price': float(price_data['price']),
                            'company_name': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
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
                            live_prices[ticker] = {
                                'price': float(eod_data['price']),
                                'company_name': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
                                'success': True,
                                'timestamp': eod_data.get('timestamp'),
                                'volume': eod_data.get('volume'),
                                'source': 'MarketStack (EOD)',
                                'comment': 'End-of-day price (intraday not available)'
                            }
                            logger.info(f"Got EOD price for {ticker}: ${eod_data['price']}")
                        else:
                            # Final fallback to mock data with error indication
                            live_prices[ticker] = {
                                'price': 150.00,
                                'company_name': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
                                'success': False,
                                'error': 'MarketStack API unavailable',
                                'comment': 'Using cached/mock price - API limit may be reached',
                                'source': 'Mock (fallback)'
                            }
                            logger.warning(f"Using mock price for {ticker} - MarketStack unavailable")
                            
                except Exception as e:
                    logger.error(f"Error fetching price for {ticker}: {e}")
                    live_prices[ticker] = {
                        'price': 150.00,
                        'company_name': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
                        'success': False,
                        'error': f'Error: {str(e)}',
                        'source': 'Mock (error fallback)'
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
        
        # Individual watchlist item endpoint - handle GET, POST, DELETE (AFTER live-prices check)
        if path.startswith('/api/watchlist/') and not path.endswith('/live-prices'):
            ticker = path.split('/')[-1].upper()
            
            # Handle different HTTP methods
            if http_method == 'POST':
                # Add ticker to watchlist - THIS SHOULD BE FIRST
                # In a real implementation, this would save to database
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'success': True,
                        'message': f'Successfully added {ticker} to watchlist',
                        'ticker': ticker
                    })
                }
            
            elif http_method == 'GET':
                # Get individual watchlist item
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'watchlist_item': {
                            'ticker': ticker,
                            'company_name': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
                            'exchange': 'NASDAQ',
                            'added_at': '2024-01-01T00:00:00Z',
                            'current_price': 150.00,
                            'fair_value': 180.00,
                            'margin_of_safety_pct': 16.67,
                            'recommendation': 'BUY'
                        },
                        'latest_analysis': {
                            'ticker': ticker,
                            'companyName': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
                            'currentPrice': 150.00,
                            'fairValue': 180.00,
                            'recommendation': 'Buy',
                            'timestamp': '2024-01-01T00:00:00Z',
                            'financialHealth': {'score': 85},
                            'businessQuality': {'score': 90},
                            'valuation': {
                                'dcf': 185.00,
                                'earningsPower': 175.00,
                                'assetBased': 160.00,
                                'weightedAverage': 180.00
                            }
                        }
                    })
                }
            
            elif http_method == 'DELETE':
                # Remove ticker from watchlist
                # In a real implementation, this would remove from database
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
        
        # Analysis endpoint - Enhanced with real MarketStack data
        if path.startswith('/api/analyze/'):
            ticker = path.split('/')[-1].upper()
            
            # Initialize MarketStack client
            marketstack = MarketStackClient()
            
            # Try to get real current price
            real_price = None
            price_source = 'Mock'
            
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
            
            # Use real price if available, otherwise fallback to mock
            current_price = real_price if real_price else 150.00
            
            # Calculate fair value based on a simple multiple of current price
            # This is a simplified valuation - in reality, this would use complex DCF models
            if real_price:
                # Use a P/E-based fair value estimation (assuming average P/E of 20)
                fair_value = current_price * 1.2  # 20% premium for quality companies
            else:
                fair_value = 180.00  # Mock fair value
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'ticker': ticker,
                    'companyName': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
                    'currentPrice': current_price,
                    'fairValue': fair_value,
                    'marginOfSafety': ((fair_value - current_price) / current_price * 100) if current_price > 0 else 0,
                    'upsidePotential': ((fair_value - current_price) / current_price * 100) if current_price > 0 else 0,
                    'priceToIntrinsicValue': (current_price / fair_value) if fair_value > 0 else 1.0,
                    'recommendation': 'Buy' if fair_value > current_price else 'Hold',
                    'recommendationReasoning': f'Analysis based on real market data from {price_source}. Fair value estimated using market multiples.',
                    'valuation': {
                        'dcf': fair_value * 1.03,  # Slight variation for DCF
                        'earningsPower': fair_value * 0.97,
                        'assetBased': fair_value * 0.85,
                        'weightedAverage': fair_value
                    },
                    'financialHealth': {
                        'score': 85,
                        'metrics': {
                            'debtToEquity': 1.73,
                            'currentRatio': 1.2,
                            'quickRatio': 1.0,
                            'interestCoverage': 15.5,
                            'roe': 0.26,
                            'roic': 0.29,
                            'roa': 0.15,
                            'fcfMargin': 0.22
                        }
                    },
                    'businessQuality': {
                        'score': 90,
                        'moatIndicators': ['Brand strength', 'Network effects', 'Switching costs'],
                        'competitivePosition': 'Strong market leader with sustainable competitive advantages'
                    },
                    'growthMetrics': {
                        'revenueGrowth1Y': 0.08,
                        'revenueGrowth3Y': 0.12,
                        'revenueGrowth5Y': 0.15,
                        'earningsGrowth1Y': 0.12,
                        'earningsGrowth3Y': 0.18,
                        'earningsGrowth5Y': 0.20
                    },
                    'priceRatios': {
                        'priceToEarnings': 25.5,
                        'priceToBook': 8.2,
                        'priceToSales': 6.8,
                        'priceToFCF': 22.1,
                        'enterpriseValueToEBITDA': 18.5
                    },
                    'currency': 'USD',
                    'financialCurrency': 'USD',
                    'timestamp': '2024-01-01T00:00:00Z',
                    'sector': 'Technology',
                    'industry': 'Consumer Electronics',
                    'marketCap': current_price * 15800000000 if current_price else 2800000000000,  # Approximate shares outstanding
                    'analysisWeights': {
                        'dcf_weight': 0.5,
                        'epv_weight': 0.3,
                        'asset_weight': 0.2
                    },
                    'businessType': 'Technology',
                    'missingData': {
                        'has_missing_data': False,
                        'missing_fields': []
                    },
                    'dataSource': {
                        'price_source': price_source,
                        'has_real_price': bool(real_price),
                        'api_available': bool(marketstack.api_key)
                    }
                })
            }
        
        # Watchlist live prices endpoint - Enhanced with MarketStack
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
                        live_prices[ticker] = {
                            'price': float(price_data['price']),
                            'company_name': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
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
                            live_prices[ticker] = {
                                'price': float(eod_data['price']),
                                'company_name': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
                                'success': True,
                                'timestamp': eod_data.get('timestamp'),
                                'volume': eod_data.get('volume'),
                                'source': 'MarketStack (EOD)',
                                'comment': 'End-of-day price (intraday not available)'
                            }
                            logger.info(f"Got EOD price for {ticker}: ${eod_data['price']}")
                        else:
                            # Final fallback to mock data with error indication
                            live_prices[ticker] = {
                                'price': 150.00,
                                'company_name': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
                                'success': False,
                                'error': 'MarketStack API unavailable',
                                'comment': 'Using cached/mock price - API limit may be reached',
                                'source': 'Mock (fallback)'
                            }
                            logger.warning(f"Using mock price for {ticker} - MarketStack unavailable")
                            
                except Exception as e:
                    logger.error(f"Error fetching price for {ticker}: {e}")
                    live_prices[ticker] = {
                        'price': 150.00,
                        'company_name': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
                        'success': False,
                        'error': f'Error: {str(e)}',
                        'source': 'Mock (error fallback)'
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
        
        # Watchlist live prices endpoint - Enhanced with MarketStack
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
                        live_prices[ticker] = {
                            'price': float(price_data['price']),
                            'company_name': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
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
                            live_prices[ticker] = {
                                'price': float(eod_data['price']),
                                'company_name': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
                                'success': True,
                                'timestamp': eod_data.get('timestamp'),
                                'volume': eod_data.get('volume'),
                                'source': 'MarketStack (EOD)',
                                'comment': 'End-of-day price (intraday not available)'
                            }
                            logger.info(f"Got EOD price for {ticker}: ${eod_data['price']}")
                        else:
                            # Final fallback to mock data with error indication
                            live_prices[ticker] = {
                                'price': 150.00,
                                'company_name': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
                                'success': False,
                                'error': 'MarketStack API unavailable',
                                'comment': 'Using cached/mock price - API limit may be reached',
                                'source': 'Mock (fallback)'
                            }
                            logger.warning(f"Using mock price for {ticker} - MarketStack unavailable")
                            
                except Exception as e:
                    logger.error(f"Error fetching price for {ticker}: {e}")
                    live_prices[ticker] = {
                        'price': 150.00,
                        'company_name': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
                        'success': False,
                        'error': f'Error: {str(e)}',
                        'source': 'Mock (error fallback)'
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
                    <h1>Stock Analysis API</h1>
                    <p>Simplified version running on AWS Lambda</p>
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
                        'version': '1.0.0',
                        'description': 'Simplified Stock Analysis API'
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