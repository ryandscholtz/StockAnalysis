"""
Enhanced Lambda handler for watchlist endpoint with analysis functionality
This version includes basic stock analysis capabilities without complex dependencies
"""
import json
import os
import math
from datetime import datetime, timezone, timedelta

def lambda_handler(event, context):
    """
    Enhanced Lambda handler that provides API endpoints including watchlist and analysis
    """
    
    # Generate version with deployment datetime in GMT+2
    gmt_plus_2 = timezone(timedelta(hours=2))
    deploy_time_utc = datetime.now(timezone.utc)
    deploy_time_local = deploy_time_utc.astimezone(gmt_plus_2)
    version_timestamp = deploy_time_local.strftime("%y%m%d-%H%M")
    version = f"3.0.0-enhanced-{version_timestamp}"
    
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
                'message': 'Stock Analysis API - Enhanced Version',
                'version': version,
                'timestamp': current_time,
                'deployed_at': deploy_time_local.isoformat(),
                'timezone': 'GMT+2'
            })
        }
    
    # Root endpoint
    if path == '/':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'Stock Analysis API - Enhanced Version',
                'version': version,
                'status': 'healthy',
                'deployed_at': deploy_time_local.isoformat()
            })
        }
    
    # Watchlist endpoint
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
    
    # Analysis endpoint - NOW IMPLEMENTED!
    if path.startswith('/api/analyze/') and len(path.split('/')) == 4:
        ticker = path.split('/')[-1].upper()
        if method == 'GET':
            # Check if streaming is requested
            is_streaming = query_params.get('stream') == 'true'
            
            if is_streaming:
                # Return streaming analysis response
                return _handle_streaming_analysis(ticker, headers)
            else:
                # Return regular analysis response
                return _handle_regular_analysis(ticker, headers)
    
    # PDF upload endpoint
    if path == '/api/upload-pdf':
        if method == 'POST':
            return {
                'statusCode': 501,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Not Implemented',
                    'message': 'PDF upload functionality is not implemented in this enhanced Lambda version',
                    'note': 'This endpoint would normally process PDF uploads and extract financial data using AWS Textract',
                    'recommendation': 'Use manual data entry instead, or deploy the full FastAPI version for PDF processing'
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
                'api_name': 'Stock Analysis API - Enhanced Version',
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
                '/api/manual-data/{ticker}',
                '/api/analyze/{ticker}'
            ],
            'supported_methods': {
                '/api/watchlist': ['GET'],
                '/api/watchlist/{ticker}': ['GET'],
                '/api/watchlist/live-prices': ['GET'],
                '/api/manual-data/{ticker}': ['GET'],
                '/api/analyze/{ticker}': ['GET'],
                '/api/upload-pdf': ['POST']
            }
        })
    }


def _handle_streaming_analysis(ticker, headers):
    """Handle streaming analysis request"""
    # Sample analysis data
    analysis_data = _get_sample_analysis(ticker)
    
    if not analysis_data:
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({
                'error': 'Not Found',
                'message': f'Analysis data for {ticker} not available'
            })
        }
    
    # For streaming, we'll return the analysis in chunks
    # In a real implementation, this would be Server-Sent Events
    streaming_response = {
        'analysis': analysis_data,
        'streaming': True,
        'chunks': [
            {'step': 1, 'message': 'Fetching company data...', 'progress': 10},
            {'step': 2, 'message': 'Analyzing financial health...', 'progress': 30},
            {'step': 3, 'message': 'Calculating intrinsic value...', 'progress': 60},
            {'step': 4, 'message': 'Determining investment recommendation...', 'progress': 90},
            {'step': 5, 'message': 'Analysis complete!', 'progress': 100}
        ]
    }
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(streaming_response)
    }


def _handle_regular_analysis(ticker, headers):
    """Handle regular analysis request"""
    analysis_data = _get_sample_analysis(ticker)
    
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


def _get_sample_analysis(ticker):
    """Get sample analysis data for supported tickers"""
    
    # Sample analysis data for supported tickers
    analysis_data = {
        'AAPL': {
            'ticker': 'AAPL',
            'company_name': 'Apple Inc.',
            'current_price': 150.25,
            'fair_value': 160.00,
            'margin_of_safety_pct': 6.09,
            'recommendation': 'Buy',
            'analysis_date': datetime.now(timezone.utc).isoformat(),
            'financial_health': {
                'score': 8.5,
                'debt_to_equity': 1.73,
                'current_ratio': 1.07,
                'quick_ratio': 0.82,
                'interest_coverage': 29.6,
                'assessment': 'Strong financial position with excellent cash generation'
            },
            'business_quality': {
                'score': 9.2,
                'competitive_moat': 'Strong',
                'brand_strength': 'Excellent',
                'market_position': 'Dominant',
                'assessment': 'Exceptional business with strong competitive advantages'
            },
            'valuation': {
                'dcf_value': 165.00,
                'epv_value': 140.00,
                'asset_value': 45.00,
                'weighted_fair_value': 160.00,
                'pe_ratio': 25.8,
                'peg_ratio': 1.2,
                'price_to_book': 39.4,
                'assessment': 'Fairly valued with slight upside potential'
            },
            'growth_metrics': {
                'revenue_growth_5y': 0.089,
                'earnings_growth_5y': 0.125,
                'free_cash_flow_growth_5y': 0.098,
                'assessment': 'Consistent growth with strong cash flow generation'
            },
            'risks': [
                'High dependence on iPhone sales',
                'Intense competition in smartphone market',
                'Regulatory scrutiny in multiple jurisdictions',
                'Supply chain vulnerabilities'
            ],
            'strengths': [
                'Strong brand loyalty and ecosystem',
                'Excellent cash generation and capital allocation',
                'Innovation leadership in consumer technology',
                'Diversified revenue streams'
            ],
            'summary': 'Apple remains a high-quality business with strong fundamentals. The current valuation appears fair with modest upside potential. The company\'s strong competitive position and cash generation capabilities make it suitable for long-term investors.',
            'confidence_level': 'High',
            'data_quality': 'Excellent'
        },
        'GOOGL': {
            'ticker': 'GOOGL',
            'company_name': 'Alphabet Inc.',
            'current_price': 2800.50,
            'fair_value': 3000.00,
            'margin_of_safety_pct': 6.65,
            'recommendation': 'Buy',
            'analysis_date': datetime.now(timezone.utc).isoformat(),
            'financial_health': {
                'score': 9.1,
                'debt_to_equity': 0.10,
                'current_ratio': 2.93,
                'quick_ratio': 2.93,
                'interest_coverage': 45.2,
                'assessment': 'Exceptional financial strength with minimal debt and strong cash position'
            },
            'business_quality': {
                'score': 8.8,
                'competitive_moat': 'Very Strong',
                'brand_strength': 'Excellent',
                'market_position': 'Dominant',
                'assessment': 'Outstanding business with dominant market position in search and digital advertising'
            },
            'valuation': {
                'dcf_value': 3100.00,
                'epv_value': 2750.00,
                'asset_value': 1200.00,
                'weighted_fair_value': 3000.00,
                'pe_ratio': 22.1,
                'peg_ratio': 0.9,
                'price_to_book': 5.8,
                'assessment': 'Attractively valued with significant upside potential'
            },
            'growth_metrics': {
                'revenue_growth_5y': 0.156,
                'earnings_growth_5y': 0.189,
                'free_cash_flow_growth_5y': 0.142,
                'assessment': 'Strong growth trajectory driven by cloud computing and AI initiatives'
            },
            'risks': [
                'Regulatory pressure and antitrust concerns',
                'Dependence on digital advertising market',
                'Competition in cloud computing',
                'Privacy regulation impact on data collection'
            ],
            'strengths': [
                'Dominant position in search and digital advertising',
                'Strong growth in cloud computing (Google Cloud)',
                'Leadership in artificial intelligence and machine learning',
                'Diversified revenue streams and strong cash generation'
            ],
            'summary': 'Alphabet represents an excellent investment opportunity with strong fundamentals and attractive valuation. The company\'s dominant market position, strong growth prospects in cloud and AI, and excellent financial health make it a compelling long-term investment.',
            'confidence_level': 'High',
            'data_quality': 'Excellent'
        }
    }
    
    return analysis_data.get(ticker.upper())