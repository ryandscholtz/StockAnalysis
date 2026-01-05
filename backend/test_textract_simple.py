#!/usr/bin/env python3
"""
Simple Textract test with minimal PDF
"""
import os
import sys
import logging
import boto3
from botocore.exceptions import ClientError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_textract_simple():
    """Test Textract with a simple approach"""
    try:
        # Initialize AWS session
        aws_profile = os.getenv("AWS_PROFILE", "Cerebrum")
        aws_region = os.getenv("AWS_REGION", "eu-west-1")
        
        session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
        textract = session.client('textract')
        
        logger.info(f"Using AWS profile: {aws_profile}, region: {aws_region}")
        
        # Test with the problematic PDF (should trigger OCR fallback)
        pdf_path = "../TestData/Test.pdf"
        
        if not os.path.exists(pdf_path):
            logger.error(f"PDF not found: {pdf_path}")
            return False
        
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        logger.info(f"PDF size: {len(pdf_bytes)} bytes")
        
        # Check PDF size limit (Textract has a 10MB limit for synchronous calls)
        if len(pdf_bytes) > 10 * 1024 * 1024:
            logger.error(f"PDF too large for Textract synchronous API: {len(pdf_bytes)} bytes (max 10MB)")
            logger.info("For large PDFs, you need to use Textract's asynchronous API with S3")
            return False
        
        # Try DetectDocumentText first (simpler API)
        logger.info("Testing DetectDocumentText...")
        try:
            response = textract.detect_document_text(
                Document={'Bytes': pdf_bytes}
            )
            
            # Extract text
            text_blocks = []
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    text_blocks.append(block.get('Text', ''))
            
            text = '\n'.join(text_blocks)
            logger.info(f"✓ DetectDocumentText successful: {len(text)} characters extracted")
            logger.info(f"Text preview: {text[:500]}...")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"✗ DetectDocumentText failed: {error_code} - {e}")
            
            if error_code == 'UnsupportedDocumentException':
                logger.error("This means the PDF format is not supported by Textract")
                logger.error("Possible causes:")
                logger.error("  1. PDF is password protected/encrypted")
                logger.error("  2. PDF has unsupported features (e.g., certain compression)")
                logger.error("  3. PDF is corrupted")
                logger.error("  4. PDF version is too old or too new")
                return False
            elif error_code == 'InvalidParameterException':
                logger.error("Invalid parameters - check PDF format")
                return False
            else:
                logger.error(f"Unexpected error: {error_code}")
                return False
        
        # Try AnalyzeDocument with TABLES
        logger.info("Testing AnalyzeDocument with TABLES...")
        try:
            response = textract.analyze_document(
                Document={'Bytes': pdf_bytes},
                FeatureTypes=['TABLES']
            )
            
            # Count blocks
            blocks = response.get('Blocks', [])
            table_count = sum(1 for block in blocks if block['BlockType'] == 'TABLE')
            cell_count = sum(1 for block in blocks if block['BlockType'] == 'CELL')
            
            logger.info(f"✓ AnalyzeDocument successful: {len(blocks)} blocks, {table_count} tables, {cell_count} cells")
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"✗ AnalyzeDocument failed: {error_code} - {e}")
            return False
        
        logger.info("✓ All Textract tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    test_textract_simple()