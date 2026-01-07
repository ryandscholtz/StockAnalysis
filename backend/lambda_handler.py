"""
AWS Lambda handler for Stock Analysis API

This module provides the Lambda handler function that wraps the FastAPI application
using Mangum for serverless deployment.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path for Lambda environment
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Import the FastAPI app
from app.main import app
from mangum import Mangum

# Configure Mangum for Lambda
handler = Mangum(
    app,
    lifespan="off",  # Disable lifespan for Lambda
    api_gateway_base_path="/",  # Base path for API Gateway
    text_mime_types=[
        "application/json",
        "application/javascript",
        "application/xml",
        "application/vnd.api+json",
        "text/css",
        "text/html",
        "text/plain",
        "text/xml"
    ]
)


def lambda_handler(event, context):
    """
    AWS Lambda handler function
    
    Args:
        event: Lambda event object from API Gateway
        context: Lambda context object
        
    Returns:
        API Gateway response object
    """
    # Add correlation ID from API Gateway if available
    if 'requestContext' in event and 'requestId' in event['requestContext']:
        os.environ['CORRELATION_ID'] = event['requestContext']['requestId']
    
    # Call the Mangum handler
    return handler(event, context)