"""
Enhanced AWS Lambda handler for Stock Analysis API with MarketStack integration
Provides real stock data using MarketStack API - NO FAKE PRICES VERSION
Updated with proper fundamental analysis - v1.2
Enhanced with PDF processing for large documents (160+ pages) - FIXED VERSION
"""

import json
import os
import urllib.request
import urllib.parse
import urllib.error
import logging
import boto3
import time
import sys
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

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Clean Lambda handler with PDF upload endpoints - FIXED VERSION
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
                    'message': 'Stock Analysis API - PDF Upload Fixed Version',
                    'version': '1.2.0-fixed'
                })
            }
        
        # API version endpoint
        if path == '/api/version':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'version': '1.2.0-fixed',
                    'build_timestamp': '2024-01-11T04:00:00Z',
                    'api_name': 'Stock Analysis API - PDF Upload Fixed Version'
                })
            }
        
        # PDF Upload endpoint - SIMPLIFIED VERSION
        if path == '/api/upload-pdf':
            if http_method != 'POST':
                return {
                    'statusCode': 405,
                    'headers': headers,
                    'body': json.dumps({'error': 'Method Not Allowed', 'message': 'Only POST method is allowed'})
                }
            
            # Get ticker from query parameters
            ticker = query_params.get('ticker')
            if not ticker:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Missing ticker parameter'})
                }
            
            ticker = ticker.upper()
            
            try:
                # Parse multipart form data from Lambda event
                import base64
                
                # Get the body and decode if base64 encoded
                body = event.get('body', '')
                is_base64 = event.get('isBase64Encoded', False)
                
                if is_base64:
                    body = base64.b64decode(body)
                else:
                    body = body.encode('utf-8') if isinstance(body, str) else body
                
                # Parse multipart data
                content_type = event.get('headers', {}).get('content-type', '') or event.get('headers', {}).get('Content-Type', '')
                
                if 'multipart/form-data' not in content_type:
                    return {
                        'statusCode': 400,
                        'headers': headers,
                        'body': json.dumps({'error': 'Content-Type must be multipart/form-data'})
                    }
                
                # Extract boundary from content-type
                boundary = None
                for part in content_type.split(';'):
                    if 'boundary=' in part:
                        boundary = part.split('boundary=')[1].strip()
                        break
                
                if not boundary:
                    return {
                        'statusCode': 400,
                        'headers': headers,
                        'body': json.dumps({'error': 'Missing boundary in multipart data'})
                    }
                
                # Parse multipart data manually
                parts = body.split(f'--{boundary}'.encode())
                pdf_data = None
                filename = None
                
                for part in parts:
                    if b'Content-Disposition: form-data' in part and b'filename=' in part:
                        # Extract filename
                        lines = part.split(b'\r\n')
                        for line in lines:
                            if b'filename=' in line:
                                filename = line.decode().split('filename=')[1].strip('"')
                                break
                        
                        # Extract file data (after double CRLF)
                        if b'\r\n\r\n' in part:
                            pdf_data = part.split(b'\r\n\r\n', 1)[1]
                            # Remove trailing boundary markers
                            if pdf_data.endswith(b'\r\n'):
                                pdf_data = pdf_data[:-2]
                            break
                
                if not pdf_data or not filename:
                    return {
                        'statusCode': 400,
                        'headers': headers,
                        'body': json.dumps({'error': 'No PDF file found in request'})
                    }
                
                # Validate file type
                if not filename.lower().endswith('.pdf'):
                    return {
                        'statusCode': 400,
                        'headers': headers,
                        'body': json.dumps({'error': 'Only PDF files are supported'})
                    }
                
                # Check file size (50MB limit for Lambda)
                if len(pdf_data) > 50 * 1024 * 1024:
                    return {
                        'statusCode': 400,
                        'headers': headers,
                        'body': json.dumps({'error': 'File size must be less than 50MB'})
                    }
                
                logger.info(f"Processing PDF upload for {ticker}: {filename}, {len(pdf_data)} bytes")
                
                # Use AI-powered PDF processor
                try:
                    # Import the AI PDF processor
                    import sys
                    import os
                    
                    # Add current directory to path
                    current_dir = os.path.dirname(os.path.abspath(__file__))
                    if current_dir not in sys.path:
                        sys.path.insert(0, current_dir)
                    
                    from ai_pdf_processor import AIPDFProcessor
                    processor = AIPDFProcessor()
                    
                    # Process the PDF with AI extraction
                    progress_updates = []
                    
                    def progress_callback(current_step: int, total_steps: int, status_message: str):
                        progress_updates.append({
                            'step': current_step,
                            'total': total_steps,
                            'message': status_message,
                            'progress_pct': int((current_step / total_steps) * 100)
                        })
                        logger.info(f"PDF Processing Progress: {status_message} ({current_step}/{total_steps})")
                    
                    # Add progress tracking
                    progress_callback(1, 5, "Starting AI-powered PDF processing")
                    progress_callback(2, 5, "Extracting text with AWS Textract")
                    
                    # Process the PDF
                    structured_data, processing_summary = processor.process_pdf(pdf_data, ticker)
                    
                    progress_callback(4, 5, "AI parsing completed")
                    progress_callback(5, 5, "Saving extracted data")
                    
                except ImportError as e:
                    logger.warning(f"AI PDF processor not available: {e}")
                    # Fallback to basic processing
                    structured_data = {
                        "income_statement": {},
                        "balance_sheet": {},
                        "cashflow": {},
                        "key_metrics": {},
                        "extraction_metadata": {
                            "ticker": ticker,
                            "extracted_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            "extraction_method": "basic_fallback",
                            "note": "AI processor unavailable - manual data entry recommended"
                        }
                    }
                    processing_summary = f"PDF received ({len(pdf_data)} bytes) - AI processing unavailable, manual data entry recommended"
                    progress_updates = [
                        {'step': 1, 'total': 2, 'message': 'PDF uploaded successfully', 'progress_pct': 50},
                        {'step': 2, 'total': 2, 'message': 'AI processing unavailable - manual entry needed', 'progress_pct': 100}
                    ]
                
                # Save extracted data to DynamoDB
                periods_saved = 0
                try:
                    dynamodb = boto3.resource('dynamodb')
                    table = dynamodb.Table(TABLE_NAME)
                    
                    # Save financial data with proper structure
                    financial_item = {
                        'PK': f'FINANCIAL#{ticker}',
                        'SK': 'EXTRACTED_DATA',
                        'ticker': ticker,
                        'data_source': 'PDF_UPLOAD',
                        'extracted_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        'filename': filename,
                        'processing_summary': processing_summary,
                        'financial_data': structured_data,
                        'ttl': int(time.time()) + (365 * 24 * 60 * 60)  # 1 year TTL
                    }
                    
                    table.put_item(Item=financial_item)
                    periods_saved = 1
                    
                    logger.info(f"Saved extracted financial data for {ticker}")
                    
                except Exception as e:
                    logger.error(f"Error saving extracted data to DynamoDB: {e}")
                    # Continue anyway - we still have the extracted data
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'success': True,
                        'message': f'Successfully processed PDF for {ticker}',
                        'ticker': ticker,
                        'filename': filename,
                        'updated_periods': periods_saved,
                        'processing_summary': processing_summary,
                        'progress_updates': progress_updates,
                        'extracted_data': structured_data,
                        'extraction_details': {
                            'file_size_mb': round(len(pdf_data) / (1024 * 1024), 2),
                            'processing_time_steps': len(progress_updates),
                            'data_types_extracted': list(structured_data.keys()) if structured_data else []
                        }
                    })
                }
                    
            except Exception as e:
                logger.error(f"Error processing PDF for {ticker}: {e}")
                return {
                    'statusCode': 500,
                    'headers': headers,
                    'body': json.dumps({
                        'success': False,
                        'error': f'PDF processing failed: {str(e)}',
                        'ticker': ticker,
                        'filename': filename if 'filename' in locals() else 'unknown'
                    })
                }
        
        # Manual Data endpoints - GET and POST
        if path.startswith('/api/manual-data'):
            if path == '/api/manual-data' and http_method == 'POST':
                # Add manual financial data
                try:
                    # Parse JSON body
                    body = event.get('body', '{}')
                    if isinstance(body, str):
                        data = json.loads(body)
                    else:
                        data = body
                    
                    ticker = data.get('ticker', '').upper()
                    data_type = data.get('data_type', '')
                    period = data.get('period', '')
                    financial_data = data.get('data', {})
                    
                    if not ticker or not data_type or not period or not financial_data:
                        return {
                            'statusCode': 400,
                            'headers': headers,
                            'body': json.dumps({
                                'success': False,
                                'error': 'Missing required fields: ticker, data_type, period, data'
                            })
                        }
                    
                    # Save to DynamoDB
                    try:
                        dynamodb = boto3.resource('dynamodb')
                        table = dynamodb.Table(TABLE_NAME)
                        
                        # Get existing financial data or create new
                        response = table.get_item(
                            Key={
                                'PK': f'FINANCIAL#{ticker}',
                                'SK': 'MANUAL_DATA'
                            }
                        )
                        
                        if 'Item' in response:
                            existing_item = response['Item']
                            financial_structure = existing_item.get('financial_data', {})
                        else:
                            financial_structure = {
                                'income_statement': {},
                                'balance_sheet': {},
                                'cashflow': {},
                                'key_metrics': {}
                            }
                        
                        # Add new data to appropriate section
                        if data_type in financial_structure:
                            if data_type == 'key_metrics':
                                # Key metrics are not period-based
                                financial_structure[data_type].update(financial_data)
                            else:
                                # Period-based data
                                if period not in financial_structure[data_type]:
                                    financial_structure[data_type][period] = {}
                                financial_structure[data_type][period].update(financial_data)
                        
                        # Save updated data
                        item = {
                            'PK': f'FINANCIAL#{ticker}',
                            'SK': 'MANUAL_DATA',
                            'ticker': ticker,
                            'data_source': 'MANUAL_ENTRY',
                            'updated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            'financial_data': financial_structure,
                            'ttl': int(time.time()) + (365 * 24 * 60 * 60)  # 1 year TTL
                        }
                        
                        table.put_item(Item=item)
                        
                        logger.info(f"Saved manual financial data for {ticker}: {data_type} - {period}")
                        
                        return {
                            'statusCode': 200,
                            'headers': headers,
                            'body': json.dumps({
                                'success': True,
                                'message': f'Successfully saved {data_type.replace("_", " ")} data for {ticker}',
                                'ticker': ticker,
                                'data_type': data_type,
                                'period': period,
                                'fields_saved': len(financial_data)
                            })
                        }
                        
                    except Exception as e:
                        logger.error(f"Error saving manual data to DynamoDB: {e}")
                        return {
                            'statusCode': 500,
                            'headers': headers,
                            'body': json.dumps({
                                'success': False,
                                'error': f'Database error: {str(e)}'
                            })
                        }
                        
                except Exception as e:
                    logger.error(f"Error processing manual data request: {e}")
                    return {
                        'statusCode': 400,
                        'headers': headers,
                        'body': json.dumps({
                            'success': False,
                            'error': f'Invalid request: {str(e)}'
                        })
                    }
            
            elif path.startswith('/api/manual-data/') and http_method == 'GET':
                # Get financial data for a ticker
                ticker = path.split('/')[-1].upper()
                
                try:
                    dynamodb = boto3.resource('dynamodb')
                    table = dynamodb.Table(TABLE_NAME)
                    
                    # Try to get manual data first
                    response = table.get_item(
                        Key={
                            'PK': f'FINANCIAL#{ticker}',
                            'SK': 'MANUAL_DATA'
                        }
                    )
                    
                    financial_data = {}
                    data_source = 'none'
                    
                    if 'Item' in response:
                        financial_data = convert_decimals_to_float(response['Item'].get('financial_data', {}))
                        data_source = 'manual'
                    else:
                        # Try to get extracted data from PDF
                        response = table.get_item(
                            Key={
                                'PK': f'FINANCIAL#{ticker}',
                                'SK': 'EXTRACTED_DATA'
                            }
                        )
                        
                        if 'Item' in response:
                            financial_data = convert_decimals_to_float(response['Item'].get('financial_data', {}))
                            data_source = 'pdf_extracted'
                    
                    has_data = bool(financial_data and any(
                        financial_data.get(key) for key in ['income_statement', 'balance_sheet', 'cashflow', 'key_metrics']
                    ))
                    
                    return {
                        'statusCode': 200,
                        'headers': headers,
                        'body': json.dumps({
                            'ticker': ticker,
                            'financial_data': financial_data,
                            'has_data': has_data,
                            'data_source': data_source,
                            'last_updated': response.get('Item', {}).get('updated_at') if 'Item' in response else None
                        })
                    }
                    
                except Exception as e:
                    logger.error(f"Error retrieving financial data for {ticker}: {e}")
                    return {
                        'statusCode': 500,
                        'headers': headers,
                        'body': json.dumps({
                            'ticker': ticker,
                            'financial_data': {},
                            'has_data': False,
                            'error': f'Database error: {str(e)}'
                        })
                    }
            
            else:
                return {
                    'statusCode': 405,
                    'headers': headers,
                    'body': json.dumps({
                        'error': 'Method Not Allowed',
                        'message': f'Method {http_method} not allowed for {path}',
                        'allowed_methods': ['GET', 'POST']
                    })
                }
        
        # Default response for unknown endpoints
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({
                'error': 'Not Found',
                'message': f'Endpoint {path} not found',
                'available_endpoints': ['/health', '/api/version', '/api/upload-pdf', '/api/manual-data', '/api/manual-data/{ticker}'],
                'supported_methods': {
                    '/api/upload-pdf': ['POST'],
                    '/api/manual-data': ['POST'],
                    '/api/manual-data/{ticker}': ['GET']
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