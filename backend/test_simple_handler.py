"""
Minimal test version of the Lambda handler to debug the PDF upload issue
"""

import json
import time
from typing import Dict, Any

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Minimal Lambda handler for testing PDF upload endpoints
    """
    
    try:
        # Extract request information
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        
        # CORS headers
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
                    'message': 'Test Lambda Handler - PDF Upload Debug Version',
                    'version': '1.0.0-debug'
                })
            }
        
        # PDF Upload endpoint - TEST VERSION
        if path == '/api/upload-pdf':
            if http_method != 'POST':
                return {
                    'statusCode': 405,
                    'headers': headers,
                    'body': json.dumps({'error': 'Method Not Allowed', 'message': 'Only POST method is allowed'})
                }
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'success': True,
                    'message': 'PDF upload endpoint is working!',
                    'debug': True,
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                })
            }
        
        # Manual data endpoint - TEST VERSION
        if path.startswith('/api/manual-data'):
            if path == '/api/manual-data' and http_method == 'POST':
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'success': True,
                        'message': 'Manual data POST endpoint is working!',
                        'debug': True
                    })
                }
            elif path.startswith('/api/manual-data/') and http_method == 'GET':
                ticker = path.split('/')[-1].upper()
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps({
                        'ticker': ticker,
                        'message': 'Manual data GET endpoint is working!',
                        'debug': True
                    })
                }
        
        # Default response for unknown endpoints
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({
                'error': 'Not Found',
                'message': f'Endpoint {path} not found in DEBUG version',
                'available_endpoints': ['/health', '/api/upload-pdf', '/api/manual-data', '/api/manual-data/{ticker}'],
                'debug': True,
                'received_path': path,
                'received_method': http_method
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
                'debug': True
            })
        }