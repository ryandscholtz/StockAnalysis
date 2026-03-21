"""
Lightweight API Gateway Lambda - Routes requests to specialized Lambdas
This Lambda is small and just handles routing
"""
import json
import boto3
import os

# Lambda client for invoking other Lambdas
lambda_client = boto3.client('lambda', region_name='eu-west-1')

# Lambda function names
STOCK_DATA_LAMBDA = os.getenv('STOCK_DATA_LAMBDA', 'stock-analysis-stock-data')
PDF_LAMBDA = os.getenv('PDF_LAMBDA', 'stock-analysis-pdf-processor')
ANALYSIS_LAMBDA = os.getenv('ANALYSIS_LAMBDA', 'stock-analysis-analyzer')
AUTH_LAMBDA = os.getenv('AUTH_LAMBDA', 'stock-analysis-auth')

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': '*',
    'Content-Type': 'application/json'
}


def invoke_lambda(function_name: str, event: dict) -> dict:
    """Invoke another Lambda function and return its response"""
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        
        result = json.loads(response['Payload'].read())
        return result
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': f'Lambda invocation failed: {str(e)}'})
        }


def route_request(event: dict) -> dict:
    """Route request to appropriate Lambda based on path"""
    
    path = event.get('path', event.get('rawPath', ''))
    method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'GET'))
    
    # Handle OPTIONS preflight
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': ''
        }
    
    # Health check
    if path in ['/', '/health', '/api/version']:
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'status': 'healthy',
                'service': 'API Gateway',
                'version': '1.0.0'
            })
        }
    
    # Route to appropriate Lambda
    if '/api/ticker/' in path or '/api/search' in path or '/api/explore' in path or '/api/quote/' in path:
        return invoke_lambda(STOCK_DATA_LAMBDA, event)
    
    elif '/api/upload-pdf' in path:
        return invoke_lambda(ANALYSIS_LAMBDA, event)

    elif '/api/pdf/' in path:
        return invoke_lambda(PDF_LAMBDA, event)
    
    elif '/api/analysis' in path or '/api/analyze' in path or '/api/batch-analyze' in path or '/api/bulk-analyze' in path or '/api/bulk-status' in path or '/api/financial-data' in path:
        return invoke_lambda(ANALYSIS_LAMBDA, event)
    
    elif '/api/watchlist' in path or '/api/manual-data' in path or '/api/auth' in path:
        return invoke_lambda(AUTH_LAMBDA, event)
    
    else:
        return {
            'statusCode': 404,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Not found', 'path': path})
        }


def lambda_handler(event, context):
    """AWS Lambda handler - routes requests to specialized Lambdas"""
    
    try:
        return route_request(event)
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': f'Gateway error: {str(e)}'})
        }
