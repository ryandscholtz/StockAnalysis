#!/usr/bin/env python3
"""
Test OCR fallback functionality with problematic PDFs
"""
import os
import sys
import logging

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ocr_fallback():
    """Test OCR fallback with the problematic Test.pdf"""
    try:
        from enhanced_textract_extractor import EnhancedTextractExtractor

        # Test with the problematic PDF
        pdf_path = "TestData/Test.pdf"
        if not os.path.exists(pdf_path):
            logger.error(f"Test PDF not found at {pdf_path}")
            return False

        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        logger.info(f"Testing OCR fallback with PDF: {len(pdf_bytes)} bytes")

        # Initialize enhanced extractor
        extractor = EnhancedTextractExtractor()

        # Test 1: Text extraction with fallback
        logger.info("=== Test 1: Text extraction with OCR fallback ===")
        try:
            text = extractor.extract_text_from_pdf(pdf_bytes)
            logger.info(f"✓ Text extraction successful: {len(text)} characters")
            logger.info(f"Text preview (first 500 chars): {text[:500]}...")

            if len(text) > 100:
                logger.info("✓ OCR fallback extracted meaningful text!")
            else:
                logger.warning("⚠️ OCR extracted minimal text - PDF may be corrupted")

        except Exception as e:
            logger.error(f"✗ Text extraction failed: {e}")
            return False

        # Test 2: Table extraction with fallback
        logger.info("=== Test 2: Table extraction with OCR fallback ===")
        try:
            tables = extractor.extract_tables_from_pdf(pdf_bytes)
            logger.info(f"✓ Table extraction successful: {len(tables)} tables found")

            for i, table in enumerate(tables):
                logger.info(f"  Table {i+1}: {table['row_count']} rows x {table['column_count']} columns (source: {table.get('source', 'unknown')})")
                if table['rows'] and len(table['rows']) > 0:
                    logger.info(f"    First row: {table['rows'][0]}")

        except Exception as e:
            logger.error(f"✗ Table extraction failed: {e}")
            # Don't return False here - table extraction is optional

        # Test 3: Financial data extraction with fallback
        logger.info("=== Test 3: Financial data extraction with OCR fallback ===")
        try:
            financial_data, raw_text = extractor.extract_financial_data(pdf_bytes, "TEST")
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
                        for field, value in list(fields.items())[:3]:  # Show first 3 fields
                            logger.info(f"      {field}: {value}")
                else:
                    logger.info(f"  {statement_type}: No data")

            if total_periods > 0:
                logger.info(f"✓ Successfully extracted {total_periods} total periods of financial data!")
            else:
                logger.warning("⚠️ No structured financial data extracted - PDF may not contain standard financial statements")

        except Exception as e:
            logger.error(f"✗ Financial data extraction failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

        logger.info("=== OCR fallback tests completed! ===")
        return True

    except Exception as e:
        logger.error(f"Test setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def check_ocr_dependencies():
    """Check if OCR dependencies are installed"""
    logger.info("=== Checking OCR dependencies ===")

    try:
        import pytesseract
        logger.info("✓ pytesseract installed")
    except ImportError:
        logger.error("✗ pytesseract not installed. Run: pip install pytesseract")
        return False

    try:
        from pdf2image import convert_from_bytes
        logger.info("✓ pdf2image installed")
    except ImportError:
        logger.error("✗ pdf2image not installed. Run: pip install pdf2image")
        return False

    try:
        from PIL import Image, ImageEnhance, ImageFilter
        logger.info("✓ Pillow installed")
    except ImportError:
        logger.error("✗ Pillow not installed. Run: pip install Pillow")
        return False

    # Check Tesseract executable
    import platform
    if platform.system() == "Windows":
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        tesseract_found = False
        for path in tesseract_paths:
            if os.path.exists(path):
                logger.info(f"✓ Tesseract found at: {path}")
                tesseract_found = True
                break

        if not tesseract_found:
            logger.error("✗ Tesseract executable not found")
            logger.error("Install from: https://github.com/tesseract-ocr/tesseract")
            logger.error("Or use: winget install UB-Mannheim.TesseractOCR")
            return False

    # Check Poppler (for pdf2image)
    try:
        # Try to convert a small test
        test_pdf = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n178\n%%EOF'
        images = convert_from_bytes(test_pdf, dpi=150)
        logger.info("✓ Poppler working (pdf2image can convert PDFs)")
    except Exception as e:
        logger.error(f"✗ Poppler not working: {e}")
        logger.error("Install Poppler:")
        logger.error("  Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/")
        logger.error("  Or use: winget install poppler")
        return False

    logger.info("✓ All OCR dependencies are installed and working!")
    return True

if __name__ == "__main__":
    logger.info("Starting OCR fallback test...")

    # Check dependencies first
    if not check_ocr_dependencies():
        logger.error("OCR dependencies missing. Please install them first.")
        sys.exit(1)

    # Test OCR fallback
    if test_ocr_fallback():
        logger.info("✓ OCR fallback test passed!")
        sys.exit(0)
    else:
        logger.error("✗ OCR fallback test failed.")
        sys.exit(1)
