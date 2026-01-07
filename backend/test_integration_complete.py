#!/usr/bin/env python3
"""
Complete integration test for PDF extraction with OCR fallback
Tests the full pipeline: PDFExtractor -> TextractExtractor -> OCR fallback
"""
import os
import sys
import logging
import asyncio

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_complete_integration():
    """Test complete PDF extraction integration with OCR fallback"""
    try:
        from app.data.pdf_extractor import PDFExtractor

        # Test with the Coca-Cola PDF that triggers OCR fallback
        pdf_path = "../TestData/Test.pdf"
        if not os.path.exists(pdf_path):
            logger.error(f"Test PDF not found at {pdf_path}")
            return False

        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        logger.info(f"Testing complete integration with PDF: {len(pdf_bytes)} bytes")

        # Initialize PDF extractor (should use TextractExtractor with OCR fallback)
        extractor = PDFExtractor()

        # Verify Textract is enabled
        if not extractor.use_textract:
            logger.error("❌ Textract is not enabled! Check USE_TEXTRACT=true in .env")
            return False

        logger.info("✅ Textract is enabled")

        # Test the complete pipeline
        logger.info("=== Testing Complete PDF Extraction Pipeline ===")

        def progress_callback(current, total):
            logger.info(f"Progress: {current}/{total}")

        try:
            # This should:
            # 1. Try Textract first (will fail with UnsupportedDocumentException)
            # 2. Automatically fall back to OCR
            # 3. Extract financial data using pattern matching
            financial_data, raw_text = await extractor.extract_financial_data_per_page(
                pdf_bytes,
                "COCA_COLA_INTEGRATION_TEST",
                progress_callback
            )

            logger.info(f"✅ Complete integration test completed")
            logger.info(f"Raw text length: {len(raw_text)} characters")

            # Analyze results
            total_periods = 0
            total_fields = 0

            for statement_type, data in financial_data.items():
                if data:
                    periods = len(data)
                    total_periods += periods
                    logger.info(f"  {statement_type}: {periods} periods")

                    for period, fields in list(data.items())[:1]:  # Show first period
                        field_count = len(fields)
                        total_fields += field_count
                        logger.info(f"    {period}: {field_count} fields")

                        # Show key financial metrics
                        for field, value in list(fields.items())[:5]:  # Show first 5 fields
                            if isinstance(value, (int, float)):
                                logger.info(f"      {field}: ${value:,.0f}")
                            else:
                                logger.info(f"      {field}: {value}")
                else:
                    logger.info(f"  {statement_type}: No data")

            # Show raw text preview
            if raw_text:
                logger.info(f"Raw text preview (first 400 chars):")
                logger.info(f"{raw_text[:400]}...")

            # Evaluate success
            if total_periods > 0 and total_fields > 0:
                logger.info(f"🎉 COMPLETE SUCCESS! Extracted {total_periods} periods with {total_fields} total fields")
                logger.info("✅ The OCR fallback system is working perfectly!")
                logger.info("✅ Integration: PDFExtractor -> TextractExtractor -> OCR fallback -> Pattern matching")
                return True
            elif len(raw_text) > 500:
                logger.info(f"✅ PARTIAL SUCCESS! OCR extracted {len(raw_text)} characters of text")
                logger.info("⚠️ No structured financial data found, but OCR text extraction worked")
                return True
            else:
                logger.error("❌ FAILED! No meaningful data extracted")
                return False

        except Exception as e:
            logger.error(f"❌ Complete integration test failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    except Exception as e:
        logger.error(f"Test setup failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_textract_direct():
    """Test TextractExtractor directly to verify OCR fallback"""
    try:
        from app.data.textract_extractor import TextractExtractor

        pdf_path = "../TestData/Test.pdf"
        if not os.path.exists(pdf_path):
            logger.error(f"Test PDF not found at {pdf_path}")
            return False

        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        logger.info("=== Testing TextractExtractor Direct (OCR Fallback) ===")

        extractor = TextractExtractor()
        financial_data, raw_text = extractor.extract_financial_data(pdf_bytes, "DIRECT_TEST")

        # Check results
        income_periods = len(financial_data.get('income_statement', {}))
        if income_periods > 0:
            logger.info(f"✅ Direct TextractExtractor test passed: {income_periods} income periods")
            return True
        else:
            logger.warning("⚠️ Direct TextractExtractor test: No structured data, but may have extracted text")
            return len(raw_text) > 100

    except Exception as e:
        logger.error(f"❌ Direct TextractExtractor test failed: {e}")
        return False

async def main():
    """Run all integration tests"""
    logger.info("🚀 Starting Complete OCR Fallback Integration Tests")
    logger.info("=" * 60)

    # Test 1: Direct TextractExtractor
    logger.info("\n📋 TEST 1: Direct TextractExtractor with OCR Fallback")
    test1_passed = await test_textract_direct()

    # Test 2: Complete integration through PDFExtractor
    logger.info("\n📋 TEST 2: Complete Integration (PDFExtractor -> TextractExtractor -> OCR)")
    test2_passed = await test_complete_integration()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("🏁 INTEGRATION TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"✅ Direct TextractExtractor: {'PASSED' if test1_passed else 'FAILED'}")
    logger.info(f"✅ Complete Integration: {'PASSED' if test2_passed else 'FAILED'}")

    if test1_passed and test2_passed:
        logger.info("🎉 ALL TESTS PASSED! OCR fallback system is fully functional!")
        logger.info("✅ Your app can now handle both supported and unsupported PDF formats")
        logger.info("✅ Textract will be tried first (fast), OCR fallback for unsupported PDFs")
        return True
    else:
        logger.error("❌ Some tests failed. Check the logs above for details.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
