#!/usr/bin/env python3
"""
Simple OCR test for problematic PDFs
"""
import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ocr_with_test_pdf():
    """Test OCR directly with Test.pdf"""
    try:
        # Import OCR libraries
        from pdf2image import convert_from_bytes
        import pytesseract
        from PIL import Image, ImageEnhance, ImageFilter

        # Configure Tesseract for Windows
        import platform
        if platform.system() == "Windows":
            tesseract_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
            for path in tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    logger.info(f"Using Tesseract at: {path}")
                    break

        # Load the problematic PDF
        pdf_path = "../TestData/Test.pdf"
        if not os.path.exists(pdf_path):
            logger.error(f"PDF not found: {pdf_path}")
            return False

        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()

        logger.info(f"Testing OCR with PDF: {len(pdf_bytes)} bytes")

        # Convert PDF to images
        logger.info("Converting PDF to images...")
        images = convert_from_bytes(pdf_bytes, dpi=300)
        logger.info(f"✓ Converted to {len(images)} images")

        if not images:
            logger.error("No images extracted from PDF")
            return False

        # Process each page with OCR
        total_text = ""
        successful_pages = 0

        for i, image in enumerate(images):
            try:
                logger.info(f"Processing page {i+1}/{len(images)} with OCR...")

                # Enhance image for better OCR
                if image.mode != 'L':
                    image = image.convert('L')

                # Enhance contrast
                enhancer = ImageEnhance.Contrast(image)
                image = enhancer.enhance(1.5)

                # Sharpen
                image = image.filter(ImageFilter.SHARPEN)

                # Perform OCR
                page_text = pytesseract.image_to_string(image, lang='eng')

                if page_text and len(page_text.strip()) > 10:
                    total_text += f"\n=== Page {i+1} ===\n{page_text}\n"
                    successful_pages += 1
                    logger.info(f"✓ OCR extracted {len(page_text)} characters from page {i+1}")

                    # Show preview of extracted text
                    preview = page_text.strip()[:200]
                    logger.info(f"Text preview: {preview}...")
                else:
                    logger.warning(f"⚠️ OCR found minimal text on page {i+1}")

            except Exception as e:
                logger.error(f"✗ OCR failed for page {i+1}: {e}")
                continue

        logger.info(f"=== OCR Results ===")
        logger.info(f"Successfully processed: {successful_pages}/{len(images)} pages")
        logger.info(f"Total text extracted: {len(total_text)} characters")

        if len(total_text) > 100:
            logger.info("✓ OCR successfully extracted meaningful text!")
            logger.info(f"Full text preview (first 500 chars):\n{total_text[:500]}...")
            return True
        else:
            logger.warning("⚠️ OCR extracted minimal text - PDF may be image-based or corrupted")
            return False

    except ImportError as e:
        logger.error(f"Missing OCR dependencies: {e}")
        logger.error("Install with: pip install pytesseract pdf2image Pillow")
        return False
    except Exception as e:
        logger.error(f"OCR test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("Starting simple OCR test with Test.pdf...")

    if test_ocr_with_test_pdf():
        logger.info("✓ OCR test successful!")
        sys.exit(0)
    else:
        logger.error("✗ OCR test failed.")
        sys.exit(1)
