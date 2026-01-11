"""
Simple Lambda handler for watchlist endpoint
This is a minimal version to get the watchlist working without complex dependencies
"""
import json
import os

def lambda_handler(event, context):
    """
    Simple Lambda handler that provides basic API endpoints including watchlist
    """
    
    # Extract path and method from the event
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    
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
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'status': 'healthy',
                'message': 'Stock Analysis API - Watchlist Fixed Version',
                'version': '2.0.0-watchlist-fix',
                'timestamp': '2026-01-11T10:30:00Z'
            })
        }
    
    # Root endpoint
    if path == '/':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'Stock Analysis API - Watchlist Fixed Version',
                'version': '2.0.0-watchlist-fix',
                'status': 'healthy'
            })
        }
    
    # Watchlist endpoint - the main fix
    if path == '/api/watchlist':
        if method == 'GET':
            # Return sample watchlist data
            watchlist_data = {
                'items': [
                    {
                        'ticker': 'AAPL',
                        'company_name': 'Apple Inc.',
                        'exchange': 'NASDAQ',
                        'added_at': '2024-01-01T00:00:00Z',
                        'notes': 'Strong tech company',
                        'current_price': 150.25,
                        'fair_value': 160.00,
                        'margin_of_safety_pct': 6.09,
                        'recommendation': 'Buy'
                    },
                    {
                        'ticker': 'GOOGL',
                        'company_name': 'Alphabet Inc.',
                        'exchange': 'NASDAQ',
                        'added_at': '2024-01-02T00:00:00Z',
                        'notes': 'Search and cloud leader',
                        'current_price': 2800.50,
                        'fair_value': 3000.00,
                        'margin_of_safety_pct': 6.65,
                        'recommendation': 'Buy'
                    }
                ],
                'total': 2
            }
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(watchlist_data)
            }
    
    # Watchlist live prices endpoint (must come before individual item endpoint)
    if path == '/api/watchlist/live-prices':
        if method == 'GET':
            live_prices_data = {
                'live_prices': {
                    'AAPL': {
                        'price': 150.25,
                        'company_name': 'Apple Inc.',
                        'success': True
                    },
                    'GOOGL': {
                        'price': 2800.50,
                        'company_name': 'Alphabet Inc.',
                        'success': True
                    }
                }
            }
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(live_prices_data)
            }
    
    # Individual watchlist item endpoint
    if path.startswith('/api/watchlist/') and len(path.split('/')) == 4:
        ticker = path.split('/')[-1].upper()
        if method == 'GET':
            # Return individual watchlist item data
            watchlist_items = {
                'AAPL': {
                    'ticker': 'AAPL',
                    'company_name': 'Apple Inc.',
                    'exchange': 'NASDAQ',
                    'added_at': '2024-01-01T00:00:00Z',
                    'notes': 'Strong tech company',
                    'current_price': 150.25,
                    'fair_value': 160.00,
                    'margin_of_safety_pct': 6.09,
                    'recommendation': 'Buy'
                },
                'GOOGL': {
                    'ticker': 'GOOGL',
                    'company_name': 'Alphabet Inc.',
                    'exchange': 'NASDAQ',
                    'added_at': '2024-01-02T00:00:00Z',
                    'notes': 'Search and cloud leader',
                    'current_price': 2800.50,
                    'fair_value': 3000.00,
                    'margin_of_safety_pct': 6.65,
                    'recommendation': 'Buy'
                }
            }
            
            if ticker in watchlist_items:
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(watchlist_items[ticker])
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
            # Return sample financial data
            financial_data = {
                'AAPL': {
                    'ticker': 'AAPL',
                    'company_name': 'Apple Inc.',
                    'financial_data': {
                        'income_statement': {
                            'revenue': 394328000000,
                            'gross_profit': 169148000000,
                            'operating_income': 114301000000,
                            'net_income': 99803000000
                        },
                        'balance_sheet': {
                            'total_assets': 352755000000,
                            'total_debt': 123930000000,
                            'shareholders_equity': 50672000000
                        },
                        'cash_flow': {
                            'operating_cash_flow': 110543000000,
                            'free_cash_flow': 99584000000
                        }
                    },
                    'has_data': True
                },
                'GOOGL': {
                    'ticker': 'GOOGL',
                    'company_name': 'Alphabet Inc.',
                    'financial_data': {
                        'income_statement': {
                            'revenue': 307394000000,
                            'gross_profit': 181690000000,
                            'operating_income': 84267000000,
                            'net_income': 73795000000
                        },
                        'balance_sheet': {
                            'total_assets': 402392000000,
                            'total_debt': 28810000000,
                            'shareholders_equity': 283893000000
                        },
                        'cash_flow': {
                            'operating_cash_flow': 101395000000,
                            'free_cash_flow': 69495000000
                        }
                    },
                    'has_data': True
                }
            }
            
            if ticker in financial_data:
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(financial_data[ticker])
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
    
    # PDF upload endpoint
    if path == '/api/upload-pdf':
        if method == 'POST':
            # For now, return a simple response indicating PDF upload is not implemented
            # In a full implementation, this would handle file upload and processing
            return {
                'statusCode': 501,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Not Implemented',
                    'message': 'PDF upload functionality is not implemented in this simple Lambda version',
                    'note': 'This endpoint would normally process PDF uploads and extract financial data using AWS Textract',
                    'recommendation': 'Use manual data entry instead, or deploy the full FastAPI version for PDF processing'
                })
            }
    
    # Analysis endpoint (placeholder)
    if path.startswith('/api/analyze/') and len(path.split('/')) == 4:
        ticker = path.split('/')[-1].upper()
        if method == 'GET':
            return {
                'statusCode': 501,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Not Implemented',
                    'message': f'Stock analysis for {ticker} is not implemented in this simple Lambda version',
                    'note': 'This endpoint would normally perform comprehensive stock analysis',
                    'recommendation': 'Deploy the full FastAPI version for analysis functionality'
                })
            }
    
    # Version endpoint
    if path == '/api/version':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'version': '2.0.0-watchlist-fix',
                'build_timestamp': '2026-01-11T10:30:00Z',
                'api_name': 'Stock Analysis API - Watchlist Fixed Version',
                'available_endpoints': [
                    '/health',
                    '/api/version',
                    '/api/watchlist',
                    '/api/watchlist/{ticker}',
                    '/api/watchlist/live-prices',
                    '/api/manual-data/{ticker}',
                    '/api/upload-pdf',
                    '/api/analyze/{ticker}'
                ]
            })
        }
    
    # Default 404 response with available endpoints
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
                '/api/manual-data/{ticker}'
            ],
            'supported_methods': {
                '/api/watchlist': ['GET'],
                '/api/watchlist/{ticker}': ['GET'],
                '/api/watchlist/live-prices': ['GET'],
                '/api/manual-data/{ticker}': ['GET'],
                '/api/upload-pdf': ['POST'],
                '/api/analyze/{ticker}': ['GET']
            }
        })
    }