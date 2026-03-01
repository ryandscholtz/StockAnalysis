"""
PDF Processing Lambda - Handles PDF uploads and text extraction
Dependencies: PyPDF2, pdfplumber, Pillow, boto3
"""
import json
import os
import base64
import boto3
from datetime import datetime

# Optional imports with fallbacks
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# S3 client
s3_client = boto3.client('s3', region_name='eu-west-1')
S3_BUCKET = os.getenv('PDF_BUCKET', 'stock-analysis-pdfs')


def extract_pdf_text(pdf_bytes: bytes) -> dict:
    """Extract text from PDF using available libraries"""
    
    if not PYPDF2_AVAILABLE and not PDFPLUMBER_AVAILABLE:
        return {
            'statusCode': 503,
            'body': json.dumps({'error': 'PDF processing libraries not available'})
        }
    
    try:
        # Try pdfplumber first (better extraction)
        if PDFPLUMBER_AVAILABLE:
            import io
            import pdfplumber
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'text': text,
                        'pages': len(pdf.pages),
                        'method': 'pdfplumber'
                    })
                }
        
        # Fallback to PyPDF2
        elif PYPDF2_AVAILABLE:
            import io
            import PyPDF2
            
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'text': text,
                    'pages': len(pdf_reader.pages),
                    'method': 'PyPDF2'
                })
            }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'PDF extraction failed: {str(e)}'})
        }


def upload_pdf(event: dict) -> dict:
    """Handle PDF upload to S3"""
    
    try:
        # Get PDF data from request body
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            pdf_bytes = base64.b64decode(body)
        else:
            # Assume JSON with base64 encoded file
            body_json = json.loads(body)
            pdf_data = body_json.get('file', '')
            pdf_bytes = base64.b64decode(pdf_data)
        
        # Generate S3 key
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ticker = event.get('queryStringParameters', {}).get('ticker', 'unknown')
        s3_key = f"pdfs/{ticker}_{timestamp}.pdf"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=pdf_bytes,
            ContentType='application/pdf'
        )
        
        # Extract text
        extraction_result = extract_pdf_text(pdf_bytes)
        
        if extraction_result['statusCode'] == 200:
            extraction_data = json.loads(extraction_result['body'])
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    's3_key': s3_key,
                    's3_bucket': S3_BUCKET,
                    'text': extraction_data['text'],
                    'pages': extraction_data['pages'],
                    'method': extraction_data['method']
                })
            }
        else:
            # Upload succeeded but extraction failed
            return {
                'statusCode': 200,
                'body': json.dumps({
                    's3_key': s3_key,
                    's3_bucket': S3_BUCKET,
                    'text': '',
                    'extraction_error': json.loads(extraction_result['body']).get('error')
                })
            }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'PDF upload failed: {str(e)}'})
        }


def lambda_handler(event, context):
    """AWS Lambda handler for PDF processing"""
    
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
    method = event.get('httpMethod', 'POST')
    
    try:
        if '/api/pdf/upload' in path and method == 'POST':
            result = upload_pdf(event)
        elif '/api/pdf/extract' in path and method == 'POST':
            body = json.loads(event.get('body', '{}'))
            pdf_data = body.get('file', '')
            pdf_bytes = base64.b64decode(pdf_data)
            result = extract_pdf_text(pdf_bytes)
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
