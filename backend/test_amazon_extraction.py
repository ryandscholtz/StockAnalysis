#!/usr/bin/env python3
"""
Test financial data extraction with Amazon PDF (another unsupported format)
"""
import os
import sys
import logging

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_amazon_extraction():
    """Test financial data extraction with Amazon PDF"""
    try:
        from app.data.textract_extractor import TextractExtractor
        
        # Test with Amazon PDF
        pdf_path = "../TestData/Amazon-2024-Annual-Report.pdf"
        if not os.path.exists(pdf_path):
            logger.error(f"Amazon PDF not found at {pdf_path}")
            return False
        
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
        
        logger.info(f"Testing Amazon PDF extraction: {len(pdf_bytes)} bytes")
        
        # Initialize Textract extractor
        extractor = TextractExtractor()
        
        # Test financial data extraction (should trigger OCR fallback)
        logger.info("=== Testing Amazon PDF Financial Data Extraction ===")
        try:
            financial_data, raw_text = extractor.extract_financial_data(pdf_bytes, "AMZN")
            
            logger.info(f"✓ Amazon PDF extraction completed")
            logger.info(f"Raw text length: {len(raw_text)} characters")
            
            # Show what was extracted
            total_periods = 0
            for statement_type, data in financial_data.items():
                if data:
                    logger.info(f"  {statement_type}: {len(data)} periods")
                    total_periods += len(data)
                    for period, fields in list(data.items())[:1]:  # Show first period
                        logger.info(f"    {period}: {len(fields)} fields")
                        for field, value in list(fields.items())[:3]:  # Show first 3 fields
                            logger.info(f"      {field}: ${value:,.0f}" if isinstance(value, (int, float)) else f"      {field}: {value}")
                else:
                    logger.info(f"  {statement_type}: No data")
            
            # Show raw text preview
            if raw_text:
                logger.info(f"Raw text preview (first 300 chars): {raw_text[:300]}...")
            
            if total_periods > 0:
                logger.info(f"✓ Successfully extracted {total_periods} total periods from Amazon PDF!")
                return True
            else:
                logger.warning("⚠️ No structured financial data extracted from Amazon PDF")
                if len(raw_text) > 100:
                    logger.info("✓ OCR fallback extracted text, but no structured financial data patterns found")
                    return True
                else:
                    logger.error("✗ OCR fallback failed to extract meaningful text from Amazon PDF")
                    return False
                
        except Exception as e:
            logger.error(f"✗ Amazon PDF extraction failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
        
    except Exception as e:
        logger.error(f"Test setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Starting Amazon PDF extraction test...")
    
    if test_amazon_extraction():
        logger.info("✓ Amazon PDF extraction test passed!")
        sys.exit(0)
    else:
        logger.error("✗ Amazon PDF extraction test failed.")
        sys.exit(1)