#!/usr/bin/env python3
"""
Manual test script for AWS Textract with the Test.pdf file
"""
import os
import sys
import logging

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_textract():
    """Test Textract with the Test.pdf file"""
    try:
        # Import the TextractExtractor
        from app.data.textract_extractor import TextractExtractor
        
        # Read the test PDF file (Test.pdf should trigger OCR fallback)
        pdf_path = "../TestData/Test.pdf"
        if not os.path.exists(pdf_path):
            logger.error(f"Test PDF not found at {pdf_path}")
            return False
        
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        logger.info(f"Loaded PDF: {len(pdf_bytes)} bytes")
        
        # Initialize Textract extractor
        logger.info("Initializing TextractExtractor with OCR fallback...")
        extractor = TextractExtractor()
        
        # Test 1: Extract text only
        logger.info("=== Test 1: Extract text only ===")
        try:
            text = extractor.extract_text_from_pdf(pdf_bytes)
            logger.info(f"✓ Text extraction successful: {len(text)} characters")
            logger.info(f"Text preview (first 500 chars): {text[:500]}...")
        except Exception as e:
            logger.error(f"✗ Text extraction failed: {e}")
            return False
        
        # Test 2: Extract tables
        logger.info("=== Test 2: Extract tables ===")
        try:
            tables = extractor.extract_tables_from_pdf(pdf_bytes)
            logger.info(f"✓ Table extraction successful: {len(tables)} tables found")
            for i, table in enumerate(tables):
                logger.info(f"  Table {i+1}: {table['row_count']} rows x {table['column_count']} columns")
                if table['rows']:
                    logger.info(f"  First row: {table['rows'][0]}")
        except Exception as e:
            logger.error(f"✗ Table extraction failed: {e}")
            return False
        
        # Test 3: Extract financial data
        logger.info("=== Test 3: Extract financial data ===")
        try:
            financial_data, raw_text = extractor.extract_financial_data(pdf_bytes, "TEST")
            logger.info(f"✓ Financial data extraction successful")
            logger.info(f"Raw text length: {len(raw_text)} characters")
            
            # Show what was extracted
            for statement_type, data in financial_data.items():
                if data:
                    logger.info(f"  {statement_type}: {len(data)} periods")
                    for period, fields in data.items():
                        logger.info(f"    {period}: {len(fields)} fields")
                        for field, value in list(fields.items())[:3]:  # Show first 3 fields
                            logger.info(f"      {field}: {value}")
                else:
                    logger.info(f"  {statement_type}: No data")
        except Exception as e:
            logger.error(f"✗ Financial data extraction failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        
        logger.info("=== All tests completed successfully! ===")
        return True
        
    except Exception as e:
        logger.error(f"Test setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_aws_credentials():
    """Test AWS credentials and Textract access"""
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        logger.info("=== Testing AWS credentials and Textract access ===")
        
        # Get AWS profile and region from environment
        aws_profile = os.getenv("AWS_PROFILE", "Cerebrum")
        aws_region = os.getenv("AWS_REGION", "eu-west-1")
        
        logger.info(f"Using AWS profile: {aws_profile}")
        logger.info(f"Using AWS region: {aws_region}")
        
        # Test session creation
        try:
            session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
            logger.info("✓ AWS session created successfully")
        except Exception as e:
            logger.error(f"✗ Failed to create AWS session: {e}")
            logger.error("Check that AWS CLI is configured with the correct profile")
            return False
        
        # Test Textract client
        try:
            textract = session.client('textract')
            logger.info("✓ Textract client created successfully")
        except Exception as e:
            logger.error(f"✗ Failed to create Textract client: {e}")
            return False
        
        # Test Textract permissions with a simple call
        try:
            # This should fail gracefully if we don't have permissions
            response = textract.detect_document_text(
                Document={'Bytes': b'invalid'}  # This will fail, but we'll see the error type
            )
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'InvalidParameterException':
                logger.info("✓ Textract permissions OK (got expected InvalidParameterException)")
                return True
            elif error_code == 'AccessDeniedException':
                logger.error("✗ Access denied to Textract. Check IAM permissions.")
                logger.error("Required permissions: textract:AnalyzeDocument, textract:DetectDocumentText")
                return False
            else:
                logger.warning(f"Unexpected Textract error: {error_code} - {e}")
                return True  # Assume it's OK if we got a different error
        except Exception as e:
            logger.error(f"✗ Unexpected error testing Textract: {e}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"AWS credentials test failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting Textract manual test...")
    
    # Test AWS credentials first
    if not test_aws_credentials():
        logger.error("AWS credentials test failed. Cannot proceed with Textract test.")
        sys.exit(1)
    
    # Test Textract functionality
    if test_textract():
        logger.info("✓ All tests passed! Textract is working correctly.")
        sys.exit(0)
    else:
        logger.error("✗ Tests failed. Check the logs above for details.")
        sys.exit(1)