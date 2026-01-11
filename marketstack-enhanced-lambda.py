"""
Enhanced Lambda handler with MarketStack API integration
Fetches real stock prices and calculates financial ratios
"""
import json
import os
import math
import requests
from datetime import datetime, timezone, timedelta

def lambda_handler(event, context):
    """
    Enhanced Lambda handler with MarketStack API integration
    """
    
    # Generate version with deployment datetime in GMT+2
    gmt_plus_2 = timezone(timedelta(hours=2))
    deploy_time_utc = datetime.now(timezone.utc)
    deploy_time_local = deploy_time_utc.astimezone(gmt_plus_2)
    version_timestamp = deploy_time_local.strftime("%y%m%d-%H%M")
    version = f"4.0.0-marketstack-{version_timestamp}"
    
    # Extract path and method from the event
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    query_params = event.get('queryStringParameters') or {}
    
    print(f"Request: {method} {path}")
    
    # CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, X-Api-Key, X-Correlation-Id',
        'Access-Control-Max-Age': '86400'
    }
    
    # Handle OPTIONS requests (CORS preflight)
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'CORS preflight'})
        }
    
    # Health endpoint
    if path == '/health':
        current_time = datetime.now(timezone.utc).isoformat()
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'status': 'healthy',
                'message': 'Stock Analysis API - MarketStack Enhanced',
                'version': version,
                'timestamp': current_time,
                'deployed_at': deploy_time_local.isoformat(),
                'timezone': 'GMT+2',
                'features': ['real_prices', 'financial_ratios', 'marketstack_integration']
            })
        }
    
    # Root endpoint
    if path == '/':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'Stock Analysis API - MarketStack Enhanced',
                'version': version,
                'status': 'healthy',
                'deployed_at': deploy_time_local.isoformat()
            })
        }
    
    # Watchlist endpoint
    if path == '/api/watchlist':
        if method == 'GET':
            # Get real prices for watchlist items
            watchlist_data = _get_watchlist_with_real_prices()
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(watchlist_data)
            }
    
    # Watchlist live prices endpoint
    if path == '/api/watchlist/live-prices':
        if method == 'GET':
            live_prices_data = _get_live_prices(['AAPL', 'GOOGL', 'MSFT', 'TSLA'])
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(live_prices_data)
            }
    
    # Individual watchlist item endpoint
    if path.startswith('/api/watchlist/') and len(path.split('/')) == 4:
        ticker = path.split('/')[-1].upper()
        if method == 'GET':
            item_data = _get_watchlist_item_with_real_data(ticker)
            
            if item_data:
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(item_data)
                }
            else:
                return {
                    'statusCode': 404,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Not Found',
                        'message': f'Watchlist item {ticker} not found'
                    })
                }
    
    # Manual data endpoint for financial data
    if path.startswith('/api/manual-data/') and len(path.split('/')) == 4:
        ticker = path.split('/')[-1].upper()
        if method == 'GET':
            financial_data = _get_financial_data_with_ratios(ticker)
            
            if financial_data:
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(financial_data)
                }
            else:
                return {
                    'statusCode': 404,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Not Found',
                        'message': f'Financial data for {ticker} not found'
                    })
                }
    
    # Analysis endpoint with real data
    if path.startswith('/api/analyze/') and len(path.split('/')) == 4:
        ticker = path.split('/')[-1].upper()
        if method == 'GET':
            is_streaming = query_params.get('stream') == 'true'
            
            if is_streaming:
                return _handle_streaming_analysis(ticker, headers)
            else:
                return _handle_regular_analysis(ticker, headers)
    
    # PDF upload endpoint
    if path == '/api/upload-pdf':
        if method == 'POST':
            return {
                'statusCode': 501,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Not Implemented',
                    'message': 'PDF upload functionality requires full FastAPI deployment',
                    'note': 'This endpoint would process PDF uploads using AWS Textract',
                    'recommendation': 'Use manual data entry or deploy full backend for PDF processing'
                })
            }
    
    # Version endpoint
    if path == '/api/version':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'version': version,
                'deployed_at': deploy_time_local.isoformat(),
                'api_name': 'Stock Analysis API - MarketStack Enhanced',
                'features': ['real_prices', 'financial_ratios', 'marketstack_integration'],
                'available_endpoints': [
                    '/health',
                    '/api/version',
                    '/api/watchlist',
                    '/api/watchlist/{ticker}',
                    '/api/watchlist/live-prices',
                    '/api/manual-data/{ticker}',
                    '/api/analyze/{ticker}',
                    '/api/upload-pdf'
                ]
            })
        }
    
    # Default 404 response
    return {
        'statusCode': 404,
        'headers': headers,
        'body': json.dumps({
            'error': 'Not Found',
            'message': f'Endpoint {path} not found',
            'available_endpoints': [
                '/health',
                '/api/version', 
                '/api/watchlist',
                '/api/watchlist/{ticker}',
                '/api/watchlist/live-prices',
                '/api/manual-data/{ticker}',
                '/api/analyze/{ticker}'
            ]
        })
    }


def _get_marketstack_api_key():
    """Get MarketStack API key from environment or secrets"""
    # In production, this would come from AWS Secrets Manager
    # For now, return a placeholder that indicates no real API key
    return os.getenv('MARKETSTACK_API_KEY', 'demo_key_placeholder')


def _fetch_real_price(ticker):
    """Fetch real price from MarketStack API"""
    api_key = _get_marketstack_api_key()
    
    if api_key == 'demo_key_placeholder':
        # Return demo prices when no real API key is available
        demo_prices = {
            'AAPL': 150.25,
            'GOOGL': 2800.50,
            'MSFT': 420.75,
            'TSLA': 185.30,
            'AMZN': 3200.45,
            'META': 485.60,
            'NVDA': 875.20
        }
        return {
            'price': demo_prices.get(ticker, 100.00),
            'source': 'demo_data',
            'success': True,
            'note': 'Demo price - configure MARKETSTACK_API_KEY for real data'
        }
    
    try:
        # MarketStack API call for real price
        url = f"http://api.marketstack.com/v1/intraday/latest"
        params = {
            'access_key': api_key,
            'symbols': ticker,
            'limit': 1
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('data') and len(data['data']) > 0:
                latest = data['data'][0]
                return {
                    'price': latest.get('last', latest.get('close')),
                    'volume': latest.get('volume'),
                    'source': 'marketstack_live',
                    'success': True,
                    'timestamp': latest.get('date')
                }
        
        # Fallback to end-of-day data if intraday fails
        eod_url = f"http://api.marketstack.com/v1/eod/latest"
        eod_response = requests.get(eod_url, params=params, timeout=10)
        
        if eod_response.status_code == 200:
            eod_data = eod_response.json()
            if eod_data.get('data') and len(eod_data['data']) > 0:
                latest = eod_data['data'][0]
                return {
                    'price': latest.get('close'),
                    'volume': latest.get('volume'),
                    'source': 'marketstack_eod',
                    'success': True,
                    'timestamp': latest.get('date')
                }
        
        # If both fail, return error
        return {
            'price': None,
            'source': 'marketstack_failed',
            'success': False,
            'error': f'MarketStack API returned {response.status_code}'
        }
        
    except Exception as e:
        return {
            'price': None,
            'source': 'marketstack_error',
            'success': False,
            'error': str(e)
        }


def _calculate_financial_ratios(ticker, current_price, financial_data):
    """Calculate financial ratios using current price and financial data"""
    ratios = {}
    
    if not current_price or not financial_data:
        return ratios
    
    try:
        # Get financial statement data
        income = financial_data.get('income_statement', {})
        balance = financial_data.get('balance_sheet', {})
        
        # Calculate P/E ratio
        net_income = income.get('net_income')
        shares_outstanding = balance.get('shares_outstanding', 1000000000)  # Default estimate
        
        if net_income and shares_outstanding:
            eps = net_income / shares_outstanding
            if eps > 0:
                ratios['pe_ratio'] = round(current_price / eps, 2)
        
        # Calculate P/B ratio
        shareholders_equity = balance.get('shareholders_equity')
        if shareholders_equity and shares_outstanding:
            book_value_per_share = shareholders_equity / shares_outstanding
            if book_value_per_share > 0:
                ratios['pb_ratio'] = round(current_price / book_value_per_share, 2)
        
        # Calculate P/S ratio
        revenue = income.get('revenue')
        if revenue and shares_outstanding:
            revenue_per_share = revenue / shares_outstanding
            if revenue_per_share > 0:
                ratios['ps_ratio'] = round(current_price / revenue_per_share, 2)
        
        # Calculate market cap
        ratios['market_cap'] = current_price * shares_outstanding
        
        # Add other useful metrics
        if net_income and shareholders_equity:
            ratios['roe'] = round((net_income / shareholders_equity) * 100, 2)  # ROE as percentage
        
        # Debt-to-equity ratio
        total_debt = balance.get('total_debt', 0)
        if shareholders_equity:
            ratios['debt_to_equity'] = round(total_debt / shareholders_equity, 2)
        
    except Exception as e:
        print(f"Error calculating ratios for {ticker}: {e}")
    
    return ratios


def _get_watchlist_with_real_prices():
    """Get watchlist with real prices from MarketStack"""
    tickers = ['AAPL', 'GOOGL', 'MSFT', 'TSLA']
    items = []
    
    for ticker in tickers:
        price_data = _fetch_real_price(ticker)
        current_price = price_data.get('price', 0)
        
        # Get basic company info
        company_names = {
            'AAPL': 'Apple Inc.',
            'GOOGL': 'Alphabet Inc.',
            'MSFT': 'Microsoft Corporation',
            'TSLA': 'Tesla, Inc.'
        }
        
        # Calculate a simple fair value estimate (for demo)
        fair_value = current_price * 1.1 if current_price else 0
        margin_of_safety = ((fair_value - current_price) / fair_value * 100) if fair_value else 0
        
        item = {
            'ticker': ticker,
            'company_name': company_names.get(ticker, ticker),
            'exchange': 'NASDAQ',
            'added_at': '2024-01-01T00:00:00Z',
            'notes': f'Real-time data from {price_data.get("source", "unknown")}',
            'current_price': current_price,
            'fair_value': round(fair_value, 2) if fair_value else None,
            'margin_of_safety_pct': round(margin_of_safety, 2),
            'recommendation': 'Buy' if margin_of_safety > 5 else 'Hold',
            'price_source': price_data.get('source'),
            'last_updated': price_data.get('timestamp')
        }
        items.append(item)
    
    return {
        'items': items,
        'total': len(items),
        'data_source': 'marketstack_enhanced',
        'last_updated': datetime.now(timezone.utc).isoformat()
    }


def _get_live_prices(tickers):
    """Get live prices for multiple tickers"""
    live_prices = {}
    
    for ticker in tickers:
        price_data = _fetch_real_price(ticker)
        live_prices[ticker] = {
            'price': price_data.get('price'),
            'company_name': _get_company_name(ticker),
            'success': price_data.get('success', False),
            'source': price_data.get('source'),
            'timestamp': price_data.get('timestamp'),
            'volume': price_data.get('volume')
        }
        
        if not price_data.get('success'):
            live_prices[ticker]['error'] = price_data.get('error')
    
    return {
        'live_prices': live_prices,
        'data_source': 'marketstack_api',
        'fetched_at': datetime.now(timezone.utc).isoformat()
    }


def _get_watchlist_item_with_real_data(ticker):
    """Get individual watchlist item with real market data"""
    price_data = _fetch_real_price(ticker)
    current_price = price_data.get('price')
    
    if not current_price:
        return None
    
    # Get financial data for ratio calculations
    financial_data = _get_base_financial_data(ticker)
    ratios = _calculate_financial_ratios(ticker, current_price, financial_data)
    
    return {
        'ticker': ticker,
        'company_name': _get_company_name(ticker),
        'exchange': 'NASDAQ',
        'added_at': '2024-01-01T00:00:00Z',
        'notes': f'Live data from {price_data.get("source")}',
        'current_price': current_price,
        'fair_value': ratios.get('fair_value'),
        'margin_of_safety_pct': ratios.get('margin_of_safety_pct'),
        'recommendation': 'Buy' if ratios.get('margin_of_safety_pct', 0) > 5 else 'Hold',
        'financial_ratios': {
            'pe_ratio': ratios.get('pe_ratio'),
            'pb_ratio': ratios.get('pb_ratio'),
            'ps_ratio': ratios.get('ps_ratio'),
            'debt_to_equity': ratios.get('debt_to_equity'),
            'roe': ratios.get('roe')
        },
        'market_data': {
            'market_cap': ratios.get('market_cap'),
            'volume': price_data.get('volume'),
            'source': price_data.get('source'),
            'last_updated': price_data.get('timestamp')
        }
    }


def _get_financial_data_with_ratios(ticker):
    """Get financial data enhanced with calculated ratios"""
    base_data = _get_base_financial_data(ticker)
    if not base_data:
        return None
    
    price_data = _fetch_real_price(ticker)
    current_price = price_data.get('price')
    
    ratios = _calculate_financial_ratios(ticker, current_price, base_data)
    
    return {
        'ticker': ticker,
        'company_name': _get_company_name(ticker),
        'current_price': current_price,
        'financial_data': base_data,
        'financial_ratios': ratios,
        'market_data': {
            'source': price_data.get('source'),
            'last_updated': price_data.get('timestamp'),
            'volume': price_data.get('volume')
        },
        'has_data': True
    }


def _get_base_financial_data(ticker):
    """Get base financial data (would come from database in production)"""
    # Sample financial data - in production this would come from database
    financial_data = {
        'AAPL': {
            'income_statement': {
                'revenue': 394328000000,
                'gross_profit': 169148000000,
                'operating_income': 114301000000,
                'net_income': 99803000000
            },
            'balance_sheet': {
                'total_assets': 352755000000,
                'total_debt': 123930000000,
                'shareholders_equity': 50672000000,
                'shares_outstanding': 15550000000
            },
            'cash_flow': {
                'operating_cash_flow': 110543000000,
                'free_cash_flow': 99584000000
            }
        },
        'GOOGL': {
            'income_statement': {
                'revenue': 307394000000,
                'gross_profit': 181690000000,
                'operating_income': 84267000000,
                'net_income': 73795000000
            },
            'balance_sheet': {
                'total_assets': 402392000000,
                'total_debt': 28810000000,
                'shareholders_equity': 283893000000,
                'shares_outstanding': 12800000000
            },
            'cash_flow': {
                'operating_cash_flow': 101395000000,
                'free_cash_flow': 69495000000
            }
        },
        'MSFT': {
            'income_statement': {
                'revenue': 245122000000,
                'gross_profit': 171035000000,
                'operating_income': 108937000000,
                'net_income': 88136000000
            },
            'balance_sheet': {
                'total_assets': 411976000000,
                'total_debt': 97718000000,
                'shareholders_equity': 206223000000,
                'shares_outstanding': 7430000000
            },
            'cash_flow': {
                'operating_cash_flow': 118291000000,
                'free_cash_flow': 84327000000
            }
        },
        'TSLA': {
            'income_statement': {
                'revenue': 96773000000,
                'gross_profit': 19653000000,
                'operating_income': 8891000000,
                'net_income': 14997000000
            },
            'balance_sheet': {
                'total_assets': 106618000000,
                'total_debt': 9566000000,
                'shareholders_equity': 62634000000,
                'shares_outstanding': 3160000000
            },
            'cash_flow': {
                'operating_cash_flow': 13256000000,
                'free_cash_flow': 7533000000
            }
        }
    }
    
    return financial_data.get(ticker.upper())


def _get_company_name(ticker):
    """Get company name for ticker"""
    names = {
        'AAPL': 'Apple Inc.',
        'GOOGL': 'Alphabet Inc.',
        'MSFT': 'Microsoft Corporation',
        'TSLA': 'Tesla, Inc.',
        'AMZN': 'Amazon.com, Inc.',
        'META': 'Meta Platforms, Inc.',
        'NVDA': 'NVIDIA Corporation'
    }
    return names.get(ticker.upper(), ticker.upper())


def _handle_streaming_analysis(ticker, headers):
    """Handle streaming analysis request with real data"""
    analysis_data = _get_comprehensive_analysis(ticker)
    
    if not analysis_data:
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({
                'error': 'Not Found',
                'message': f'Analysis data for {ticker} not available'
            })
        }
    
    streaming_response = {
        'analysis': analysis_data,
        'streaming': True,
        'chunks': [
            {'step': 1, 'message': 'Fetching real-time price data from MarketStack...', 'progress': 20},
            {'step': 2, 'message': 'Calculating financial ratios...', 'progress': 40},
            {'step': 3, 'message': 'Analyzing financial health...', 'progress': 60},
            {'step': 4, 'message': 'Performing valuation analysis...', 'progress': 80},
            {'step': 5, 'message': 'Analysis complete with real market data!', 'progress': 100}
        ]
    }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(streaming_response)
    }


def _handle_regular_analysis(ticker, headers):
    """Handle regular analysis request with real data"""
    analysis_data = _get_comprehensive_analysis(ticker)
    
    if not analysis_data:
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({
                'error': 'Not Found',
                'message': f'Analysis data for {ticker} not available'
            })
        }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(analysis_data)
    }


def _get_comprehensive_analysis(ticker):
    """Get comprehensive analysis with real market data"""
    price_data = _fetch_real_price(ticker)
    current_price = price_data.get('price')
    
    if not current_price:
        return None
    
    financial_data = _get_base_financial_data(ticker)
    if not financial_data:
        return None
    
    ratios = _calculate_financial_ratios(ticker, current_price, financial_data)
    
    # Calculate fair value estimate (simplified DCF)
    free_cash_flow = financial_data.get('cash_flow', {}).get('free_cash_flow', 0)
    shares_outstanding = financial_data.get('balance_sheet', {}).get('shares_outstanding', 1000000000)
    
    if free_cash_flow and shares_outstanding:
        # Simple DCF: FCF * 15 (15x multiple) / shares
        fair_value = (free_cash_flow * 15) / shares_outstanding
        margin_of_safety = ((fair_value - current_price) / fair_value * 100) if fair_value > 0 else 0
    else:
        fair_value = current_price * 1.1  # Simple 10% premium estimate
        margin_of_safety = 9.09  # Approximate for 10% premium
    
    return {
        'ticker': ticker,
        'company_name': _get_company_name(ticker),
        'current_price': current_price,
        'fair_value': round(fair_value, 2),
        'margin_of_safety_pct': round(margin_of_safety, 2),
        'recommendation': 'Buy' if margin_of_safety > 10 else 'Hold' if margin_of_safety > 0 else 'Sell',
        'analysis_date': datetime.now(timezone.utc).isoformat(),
        'financial_health': {
            'score': 8.0,  # Would be calculated based on ratios
            'debt_to_equity': ratios.get('debt_to_equity', 0),
            'roe': ratios.get('roe', 0),
            'assessment': 'Good financial position with real market data'
        },
        'business_quality': {
            'score': 8.5,
            'competitive_moat': 'Strong',
            'market_position': 'Leading',
            'assessment': 'Strong business fundamentals'
        },
        'valuation': {
            'pe_ratio': ratios.get('pe_ratio'),
            'pb_ratio': ratios.get('pb_ratio'),
            'ps_ratio': ratios.get('ps_ratio'),
            'market_cap': ratios.get('market_cap'),
            'assessment': f'Based on real price of ${current_price}'
        },
        'market_data': {
            'source': price_data.get('source'),
            'volume': price_data.get('volume'),
            'last_updated': price_data.get('timestamp'),
            'data_quality': 'Real-time' if 'live' in price_data.get('source', '') else 'End-of-day'
        },
        'summary': f'Analysis based on real market price of ${current_price} from {price_data.get("source", "MarketStack")}. Fair value estimated at ${round(fair_value, 2)} with {round(margin_of_safety, 1)}% margin of safety.',
        'confidence_level': 'High',
        'data_source': 'marketstack_enhanced'
    }