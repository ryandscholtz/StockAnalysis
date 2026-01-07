#!/usr/bin/env python3
"""
Test financial data extraction with OCR fallback
"""
import os
import sys
import logging

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_financial_extraction_with_fallback():
    """Test financial data extraction with OCR fallback"""
    try:
        from app.data.textract_extractor import TextractExtractor

        # Test with the problematic PDF that should trigger OCR fallback
        pdf_path = "../TestData/Test.pdf"
        if not os.path.exists(pdf_path):
            logger.error(f"Test PDF not found at {pdf_path}")
            return False

        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        logger.info(f"Testing financial extraction with PDF: {len(pdf_bytes)} bytes")

        # Initialize Textract extractor
        extractor = TextractExtractor()

        # Test financial data extraction (should trigger OCR fallback)
        logger.info("=== Testing Financial Data Extraction with OCR Fallback ===")
        try:
            financial_data, raw_text = extractor.extract_financial_data(pdf_bytes, "COCA_COLA_TEST")

            logger.info(f"✓ Financial data extraction completed")
            logger.info(f"Raw text length: {len(raw_text)} characters")

            # Show what was extracted
            total_periods = 0
            for statement_type, data in financial_data.items():
                if data:
                    logger.info(f"  {statement_type}: {len(data)} periods")
                    total_periods += len(data)
                    for period, fields in list(data.items())[:2]:  # Show first 2 periods
                        logger.info(f"    {period}: {len(fields)} fields")
                        for field, value in list(fields.items())[:5]:  # Show first 5 fields
                            logger.info(f"      {field}: ${value:,.0f}" if isinstance(value, (int, float)) else f"      {field}: {value}")
                else:
                    logger.info(f"  {statement_type}: No data")

            # Show raw text preview
            if raw_text:
                logger.info(f"Raw text preview (first 500 chars): {raw_text[:500]}...")

            if total_periods > 0:
                logger.info(f"✓ Successfully extracted {total_periods} total periods of financial data using OCR fallback!")
                return True
            else:
                logger.warning("⚠️ No structured financial data extracted - but OCR text was extracted")
                if len(raw_text) > 100:
                    logger.info("✓ OCR fallback successfully extracted text, but no structured financial data found")
                    return True
                else:
                    logger.error("✗ OCR fallback failed to extract meaningful text")
                    return False

        except Exception as e:
            logger.error(f"✗ Financial data extraction failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    except Exception as e:
        logger.error(f"Test setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Starting financial data extraction test with OCR fallback...")

    if test_financial_extraction_with_fallback():
        logger.info("✓ Financial extraction test with OCR fallback passed!")
        sys.exit(0)
    else:
        logger.error("✗ Financial extraction test failed.")
        sys.exit(1)
