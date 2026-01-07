"""
Enhanced AWS Textract integration with OCR fallback for image-based PDFs
"""
import os
import logging
import json
import boto3
from typing import Dict, List, Optional, Any, Tuple
from botocore.exceptions import ClientError
import io

logger = logging.getLogger(__name__)

# OCR imports (for fallback when Textract fails)
try:
    from pdf2image import convert_from_bytes
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR libraries not available. Install pytesseract, pdf2image, and Pillow for image-based PDF support.")


class EnhancedTextractExtractor:
    """Enhanced Textract extractor with OCR fallback for unsupported PDFs"""
    
    def __init__(self):
        self.aws_region = os.getenv("AWS_REGION", "eu-west-1")
        self.aws_profile = os.getenv("AWS_PROFILE", "Cerebrum")
        
        # Initialize boto3 session
        try:
            self.session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
            self.textract = self.session.client('textract')
            logger.info(f"EnhancedTextractExtractor initialized (region: {self.aws_region}, profile: {self.aws_profile})")
        except Exception as e:
            logger.error(f"Failed to initialize Textract client: {e}")
            raise
        
        # Configure Tesseract for Windows if needed
        self._configure_tesseract()
    
    def _configure_tesseract(self):
        """Configure Tesseract OCR for Windows"""
        if not OCR_AVAILABLE:
            return
        
        import platform
        if platform.system() == "Windows":
            tesseract_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                r"C:\Users\Admin\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
            ]
            for path in tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    logger.info(f"Using Tesseract at: {path}")
                    return
            
            logger.warning("Tesseract not found in standard Windows locations. OCR may not work.")
            logger.warning("Install Tesseract from: https://github.com/tesseract-ocr/tesseract")
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """
        Extract text from PDF using Textract with OCR fallback
        """
        # Try Textract first
        try:
            logger.info(f"Attempting Textract extraction (PDF size: {len(pdf_bytes)} bytes)")
            return self._extract_with_textract(pdf_bytes)
        except Exception as e:
            logger.warning(f"Textract failed: {e}")
            logger.info("Falling back to OCR extraction...")
            return self._extract_with_ocr(pdf_bytes)
    
    def _extract_with_textract(self, pdf_bytes: bytes) -> str:
        """Extract text using AWS Textract"""
        logger.info("✓ Using AWS Textract - processes PDF directly (no image conversion)")
        
        response = self.textract.analyze_document(
            Document={'Bytes': pdf_bytes},
            FeatureTypes=['TABLES', 'FORMS']
        )
        
        # Parse text from response
        text_blocks = []
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text_blocks.append(block.get('Text', ''))
        
        text = '\n'.join(text_blocks)
        logger.info(f"✓ Textract extracted {len(text)} characters")
        return text
    
    def _extract_with_ocr(self, pdf_bytes: bytes) -> str:
        """Extract text using OCR as fallback"""
        if not OCR_AVAILABLE:
            raise Exception(
                "OCR libraries not installed. Install with: pip install pytesseract pdf2image Pillow. "
                "Also install Tesseract OCR from https://github.com/tesseract-ocr/tesseract"
            )
        
        logger.info("⚠️ FALLBACK: Converting PDF to images for OCR processing...")
        logger.info("⚠️ NOTE: This is slower than Textract but works with image-based/scanned PDFs")
        
        try:
            # Convert PDF to images
            images = convert_from_bytes(pdf_bytes, dpi=300)  # High DPI for better OCR
            logger.info(f"✓ Converted PDF to {len(images)} images")
            
            if not images:
                raise Exception("No images could be extracted from PDF")
            
            # Process each page with OCR
            text_parts = []
            successful_pages = 0
            
            for i, image in enumerate(images):
                try:
                    logger.info(f"Processing page {i+1}/{len(images)} with OCR...")
                    
                    # Enhance image for better OCR
                    enhanced_image = self._enhance_image_for_ocr(image)
                    
                    # Perform OCR
                    page_text = pytesseract.image_to_string(enhanced_image, lang='eng')
                    
                    if page_text and len(page_text.strip()) > 10:
                        text_parts.append(f"=== Page {i+1} ===\n{page_text}")
                        successful_pages += 1
                        logger.info(f"✓ OCR extracted {len(page_text)} characters from page {i+1}")
                    else:
                        logger.warning(f"⚠️ OCR found minimal text on page {i+1}")
                        
                except Exception as e:
                    logger.error(f"✗ OCR failed for page {i+1}: {e}")
                    continue
            
            if not text_parts:
                raise Exception("OCR did not extract any text from PDF images")
            
            result = "\n\n".join(text_parts)
            logger.info(f"✓ OCR completed: {successful_pages}/{len(images)} pages, {len(result)} total characters")
            return result
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise
    
    def _enhance_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """Enhance image quality for better OCR results"""
        try:
            # Convert to grayscale for better OCR
            if image.mode != 'L':
                image = image.convert('L')
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)
            
            # Sharpen image
            image = image.filter(ImageFilter.SHARPEN)
            
            # Scale up for better OCR (if image is small)
            width, height = image.size
            if width < 1000 or height < 1000:
                scale_factor = max(1000 / width, 1000 / height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                logger.debug(f"Scaled image from {width}x{height} to {new_size[0]}x{new_size[1]}")
            
            return image
            
        except Exception as e:
            logger.warning(f"Image enhancement failed: {e}, using original image")
            return image
    
    def extract_financial_data(self, pdf_bytes: bytes, ticker: str) -> Tuple[Dict[str, Any], str]:
        """
        Extract financial data with enhanced fallback support
        """
        try:
            # Try Textract first
            logger.info(f"Extracting financial data for {ticker} using Textract...")
            return self._extract_financial_data_textract(pdf_bytes, ticker)
        except Exception as e:
            logger.warning(f"Textract financial extraction failed: {e}")
            logger.info("Falling back to OCR-based financial data extraction...")
            return self._extract_financial_data_ocr(pdf_bytes, ticker)
    
    def _extract_financial_data_textract(self, pdf_bytes: bytes, ticker: str) -> Tuple[Dict[str, Any], str]:
        """Extract financial data using Textract"""
        # Get both text and tables
        response = self.textract.analyze_document(
            Document={'Bytes': pdf_bytes},
            FeatureTypes=['TABLES', 'FORMS']
        )
        
        # Parse text
        text_blocks = []
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text_blocks.append(block.get('Text', ''))
        text = '\n'.join(text_blocks)
        
        # For now, return basic structure (you can enhance this with table parsing)
        structured_data = {
            "income_statement": {},
            "balance_sheet": {},
            "cashflow": {},
            "key_metrics": {}
        }
        
        return structured_data, text
    
    def _extract_financial_data_ocr(self, pdf_bytes: bytes, ticker: str) -> Tuple[Dict[str, Any], str]:
        """Extract financial data using OCR fallback"""
        if not OCR_AVAILABLE:
            raise Exception("OCR libraries not available for financial data extraction")
        
        # Extract text with OCR
        text = self._extract_with_ocr(pdf_bytes)
        
        # For now, return basic structure (you can enhance this with pattern matching)
        structured_data = {
            "income_statement": {},
            "balance_sheet": {},
            "cashflow": {},
            "key_metrics": {}
        }
        
        return structured_data, text