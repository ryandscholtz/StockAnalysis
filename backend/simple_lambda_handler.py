"""
Simplified AWS Lambda handler for Stock Analysis API
This is a minimal version to get basic functionality working
"""

import json
import os
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Simplified Lambda handler that provides basic API responses
    """
    
    try:
        # Extract request information
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        query_params = event.get('queryStringParameters') or {}
        
        # CORS headers
        headers = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
        }
        
        # Handle OPTIONS requests (CORS preflight)
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
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
        
        # API search endpoint - return mock data for now
        if path == '/api/search':
            query = query_params.get('q', '')
            if not query:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Query parameter q is required'})
                }
            
            # Mock search results
            mock_results = [
                {
                    'ticker': 'AAPL',
                    'companyName': 'Apple Inc.',
                    'exchange': 'NASDAQ'
                },
                {
                    'ticker': 'MSFT', 
                    'companyName': 'Microsoft Corporation',
                    'exchange': 'NASDAQ'
                }
            ] if query.upper() in ['A', 'AP', 'APP', 'APPL', 'AAPL', 'M', 'MS', 'MSF', 'MSFT'] else []
            
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
        
        # Individual watchlist item endpoint
        if path.startswith('/api/watchlist/'):
            ticker = path.split('/')[-1].upper()
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
                        'recommendation': 'BUY',
                        'analysisDate': '2024-01-01',
                        'financialHealthScore': 85,
                        'businessQualityScore': 90,
                        'valuationScore': 75,
                        'growthScore': 80
                    }
                })
            }
        
        # Analysis endpoint - return mock analysis data
        if path.startswith('/api/analyze/'):
            ticker = path.split('/')[-1].upper()
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'ticker': ticker,
                    'companyName': f'{ticker} Inc.' if ticker == 'AAPL' else f'{ticker} Corporation',
                    'currentPrice': 150.00,
                    'fairValue': 180.00,
                    'recommendation': 'BUY',
                    'analysisDate': '2024-01-01',
                    'financialHealthScore': 85,
                    'businessQualityScore': 90,
                    'valuationScore': 75,
                    'growthScore': 80,
                    'marginOfSafety': 16.67,
                    'sector': 'Technology',
                    'industry': 'Consumer Electronics',
                    'marketCap': 2800000000000,
                    'peRatio': 25.5,
                    'pbRatio': 8.2,
                    'debtToEquity': 1.73,
                    'roe': 0.26,
                    'roic': 0.29,
                    'revenueGrowth': 0.08,
                    'earningsGrowth': 0.12,
                    'summary': f'Mock analysis for {ticker}. This is a simplified response for demonstration purposes.',
                    'risks': ['Market volatility', 'Competition', 'Regulatory changes'],
                    'strengths': ['Strong brand', 'Innovation', 'Financial position'],
                    'missingData': {
                        'has_missing_data': False,
                        'missing_fields': []
                    }
                })
            }
        
        # Watchlist live prices endpoint
        if path == '/api/watchlist/live-prices':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'live_prices': {
                        'AAPL': {
                            'price': 150.00,
                            'company_name': 'Apple Inc.',
                            'success': True
                        }
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
                        <li>GET /api/search?q=AAPL - Search for stock tickers</li>
                        <li>GET /api/watchlist - Get watchlist items</li>
                        <li>GET /api/watchlist/live-prices - Get live prices for watchlist</li>
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
                'available_endpoints': ['/health', '/api/search', '/api/watchlist', '/api/watchlist/{ticker}', '/api/analyze/{ticker}', '/api/watchlist/live-prices', '/api/analysis-presets', '/docs', '/openapi.json']
            })
        }
    
    except Exception as e:
        # Error handling
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Internal Server Error',
                'message': str(e),
                'path': event.get('path', 'unknown')
            })
        }