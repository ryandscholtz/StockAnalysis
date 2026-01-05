#!/usr/bin/env python3
"""
Test PDF validity and format
"""
import os
import sys
import logging

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pdf_validity():
    """Test if the PDF is valid and readable"""
    pdf_path = "TestData/Amazon-2024-Annual-Report.pdf"
    
    if not os.path.exists(pdf_path):
        logger.error(f"PDF not found at {pdf_path}")
        return False
    
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()
    
    logger.info(f"PDF size: {len(pdf_bytes)} bytes")
    
    # Check PDF header
    if pdf_bytes.startswith(b'%PDF-'):
        version = pdf_bytes[:8].decode('ascii', errors='ignore')
        logger.info(f"✓ Valid PDF header: {version}")
    else:
        logger.error("✗ Invalid PDF header")
        return False
    
    # Try with PyPDF2
    try:
        import PyPDF2
        import io
        
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        logger.info(f"✓ PyPDF2 can read PDF: {len(pdf_reader.pages)} pages")
        
        # Try to extract text from first page
        if pdf_reader.pages:
            text = pdf_reader.pages[0].extract_text()
            logger.info(f"✓ PyPDF2 extracted {len(text)} characters from first page")
            if text:
                logger.info(f"Text preview: {text[:200]}...")
        
    except Exception as e:
        logger.error(f"✗ PyPDF2 failed: {e}")
    
    # Try with pdfplumber
    try:
        import pdfplumber
        
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            logger.info(f"✓ pdfplumber can read PDF: {len(pdf.pages)} pages")
            
            if pdf.pages:
                text = pdf.pages[0].extract_text()
                logger.info(f"✓ pdfplumber extracted {len(text) if text else 0} characters from first page")
                if text:
                    logger.info(f"Text preview: {text[:200]}...")
    
    except Exception as e:
        logger.error(f"✗ pdfplumber failed: {e}")
    
    # Check for common PDF issues
    logger.info("=== PDF Analysis ===")
    
    # Check if it's encrypted
    if b'/Encrypt' in pdf_bytes:
        logger.warning("⚠️ PDF appears to be encrypted")
    
    # Check if it has XRef table
    if b'xref' in pdf_bytes:
        logger.info("✓ PDF has xref table")
    else:
        logger.warning("⚠️ PDF missing xref table")
    
    # Check for trailer
    if b'trailer' in pdf_bytes:
        logger.info("✓ PDF has trailer")
    else:
        logger.warning("⚠️ PDF missing trailer")
    
    # Check for EOF marker
    if pdf_bytes.rstrip().endswith(b'%%EOF'):
        logger.info("✓ PDF has proper EOF marker")
    else:
        logger.warning("⚠️ PDF missing proper EOF marker")
    
    # Look for content streams
    stream_count = pdf_bytes.count(b'stream')
    logger.info(f"PDF contains {stream_count} content streams")
    
    return True

if __name__ == "__main__":
    test_pdf_validity()