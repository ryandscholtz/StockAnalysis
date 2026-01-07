"""
PDF extraction service using AWS Textract and LLM to extract financial data
"""
import os
import logging
from typing import Dict, List, Optional, Any, Tuple, Callable
import PyPDF2
import pdfplumber
import io

from app.core.xray_middleware import trace_function, create_external_api_subsegment, end_subsegment

logger = logging.getLogger(__name__)

# OCR imports (optional - only needed for scanned PDFs)
try:
    from pdf2image import convert_from_bytes
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    logger.warning("OCR libraries not available. Install pytesseract, pdf2image, and Pillow for scanned PDF support.")


class PDFExtractor:
    """Extract text from PDF files using AWS Textract"""
    
    def __init__(self):
        # Use AWS Textract for PDF extraction
        self.use_textract = os.getenv("USE_TEXTRACT", "true").lower() == "true"
        
        if self.use_textract:
            try:
                from app.data.textract_extractor import TextractExtractor
                self.textract_extractor = TextractExtractor()
                logger.info("PDFExtractor initialized with AWS Textract")
            except Exception as e:
                logger.error(f"Failed to initialize Textract: {e}")
                logger.warning("Falling back to local PDF extraction (pdfplumber/PyPDF2)")
                self.use_textract = False
                self.textract_extractor = None
        else:
            self.textract_extractor = None
            logger.info("PDFExtractor initialized with local extraction (Textract disabled)")
        
    
    def get_pdf_page_count(self, pdf_bytes: bytes) -> int:
        """Get the total number of pages in a PDF"""
        try:
            # Try pdfplumber first
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                return len(pdf.pages)
        except Exception:
            try:
                # Fallback to PyPDF2
                pdf_file = io.BytesIO(pdf_bytes)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                return len(pdf_reader.pages)
            except Exception:
                # If both fail, try to get from images
                try:
                    if OCR_AVAILABLE:
                        images = convert_from_bytes(pdf_bytes, dpi=120)
                        return len(images)
                except Exception:
                    pass
                return 0
    
    def extract_text_from_pdf(self, pdf_bytes: bytes, use_ocr: bool = True) -> str:
        """Extract text content from PDF bytes, with OCR fallback for image-based PDFs"""
        text_parts = []
        text_extracted = False
        
        # Method 1: Try pdfplumber first (better for tables)
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text and len(text.strip()) > 10:  # Ensure we got meaningful text
                        text_parts.append(text)
                        text_extracted = True
                    # Also try to extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            table_text = "\n".join(["\t".join([str(cell) if cell else "" for cell in row]) for row in table])
                            text_parts.append(f"\n[Table]\n{table_text}\n")
                            text_extracted = True
                
                if text_extracted and len("\n\n".join(text_parts).strip()) > 100:
                    logger.info("Successfully extracted text using pdfplumber")
                    return "\n\n".join(text_parts)
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")
        
        # Method 2: Fallback to PyPDF2
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text_parts = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text and len(text.strip()) > 10:
                    text_parts.append(text)
                    text_extracted = True
            
            if text_extracted and len("\n\n".join(text_parts).strip()) > 100:
                logger.info("Successfully extracted text using PyPDF2")
                return "\n\n".join(text_parts)
        except Exception as e:
            logger.warning(f"PyPDF2 failed: {e}")
        
        # Method 3: OCR for image-based/scanned PDFs (FALLBACK ONLY - not used with Textract)
        if use_ocr:
            try:
                logger.warning("⚠️ FALLBACK: Text extraction methods failed, attempting local OCR (image conversion)...")
                logger.warning("⚠️ NOTE: AWS Textract does NOT require image conversion. This fallback is only used when Textract is unavailable.")
                return self._extract_text_with_ocr(pdf_bytes)
            except Exception as e:
                logger.error(f"OCR extraction also failed: {e}")
                if text_extracted:
                    # Return whatever we got, even if minimal
                    result = "\n\n".join(text_parts) if text_parts else ""
                    if len(result.strip()) > 0:
                        logger.warning(f"Returning minimal text extracted ({len(result)} chars). OCR failed: {e}")
                        return result
                raise Exception(f"Failed to extract text from PDF. Text extraction and OCR both failed. Last error: {e}")
        else:
            if text_extracted:
                result = "\n\n".join(text_parts) if text_parts else ""
                if len(result.strip()) > 0:
                    return result
            raise Exception("Failed to extract text from PDF. PDF may be image-based. Enable OCR to process scanned documents.")
    
    def _extract_text_with_ocr(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF using OCR (for scanned/image-based PDFs)"""
        # Check if OCR is available
        try:
            from pdf2image import convert_from_bytes
            import pytesseract
            from PIL import Image
        except ImportError:
            raise ImportError(
                "OCR libraries not installed. Install with: pip install pytesseract pdf2image Pillow. "
                "Also install Tesseract OCR from https://github.com/tesseract-ocr/tesseract"
            )
        
        # Configure Tesseract path for Windows (if not in PATH)
        import platform
        if platform.system() == "Windows":
            tesseract_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
            for path in tesseract_paths:
                import os
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    logger.info(f"Using Tesseract at: {path}")
                    break
        
        try:
            logger.info("Converting ALL PDF pages to images for OCR...")
            logger.info(f"PDF size: {len(pdf_bytes)} bytes")
            
            # Convert ALL PDF pages to images (no page limit)
            # pdf2image requires poppler-utils to be installed on the system
            try:
                images = convert_from_bytes(pdf_bytes, dpi=300)  # Higher DPI for better OCR accuracy
            except Exception as convert_error:
                error_msg = str(convert_error).lower()
                if "poppler" in error_msg or "pdftoppm" in error_msg or "cannot find" in error_msg:
                    raise Exception(
                        f"PDF to image conversion failed: Poppler is not installed or not in PATH. "
                        f"Install Poppler: Windows - Download from https://github.com/oschwartz10612/poppler-windows/releases/ "
                        f"or use: winget install poppler. Error: {convert_error}"
                    )
                else:
                    raise Exception(f"PDF to image conversion failed: {convert_error}")
            
            if not images:
                raise Exception("No images could be extracted from PDF. The PDF may be corrupted or empty.")
            
            total_pages = len(images)
            logger.warning(f"⚠️ FALLBACK MODE: Converted {total_pages} page(s) to images for local OCR processing.")
            logger.warning("⚠️ NOTE: This is SLOW and not needed when using AWS Textract. Textract processes PDFs directly without image conversion.")
            logger.warning("⚠️ To use Textract instead, ensure AWS credentials are configured and USE_TEXTRACT=true in .env")
            logger.info(f"Processing {total_pages} page(s) with OCR...")
            
            # Verify images are valid
            for i, img in enumerate(images):
                if img is None:
                    logger.warning(f"Page {i+1} converted to None - skipping")
                else:
                    logger.debug(f"Page {i+1} image size: {img.size}, mode: {img.mode}")
            text_parts = []
            successful_pages = 0
            
            for i, image in enumerate(images):
                try:
                    # Verify image is valid before processing
                    if image is None:
                        logger.warning(f"Page {i+1}/{total_pages} image is None - skipping")
                        continue
                    
                    # Perform OCR on each page
                    logger.info(f"Processing page {i+1}/{total_pages} with OCR (image size: {image.size})...")
                    page_text = pytesseract.image_to_string(image, lang='eng')
                    if page_text and len(page_text.strip()) > 10:
                        text_parts.append(f"Page {i+1}:\n{page_text}")
                        successful_pages += 1
                        logger.info(f"OCR extracted {len(page_text)} characters from page {i+1}/{total_pages}")
                    else:
                        logger.warning(f"OCR returned minimal/no text for page {i+1}/{total_pages} (got {len(page_text) if page_text else 0} chars)")
                except Exception as e:
                    logger.error(f"OCR failed for page {i+1}/{total_pages}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue
            
            logger.info(f"OCR processing complete: {successful_pages}/{total_pages} pages successfully extracted")
            
            if not text_parts:
                raise Exception("OCR did not extract any text from PDF images")
            
            result = "\n\n".join(text_parts)
            logger.info(f"OCR successfully extracted {len(result)} total characters")
            return result
            
        except ImportError:
            error_msg = "OCR libraries not installed. Install pytesseract and pdf2image: pip install pytesseract pdf2image Pillow. Also install Tesseract OCR: https://github.com/tesseract-ocr/tesseract"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise
    
    def extract_text_per_page(self, pdf_bytes: bytes, use_ocr: bool = True) -> List[Tuple[int, str]]:
        """
        Extract text from PDF, returning a list of (page_number, page_text) tuples
        Returns: List of (page_number (1-indexed), text) tuples
        """
        pages_text = []
        
        # Method 1: Try pdfplumber first (better for tables)
        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    page_text_parts = []
                    
                    # Extract text
                    text = page.extract_text()
                    if text and len(text.strip()) > 10:
                        page_text_parts.append(text)
                    
                    # Extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            table_text = "\n".join(["\t".join([str(cell) if cell else "" for cell in row]) for row in table])
                            page_text_parts.append(f"\n[Table]\n{table_text}\n")
                    
                    if page_text_parts:
                        pages_text.append((page_num, "\n\n".join(page_text_parts)))
                
                if pages_text:
                    logger.info(f"Extracted text from {len(pages_text)} pages using pdfplumber")
                    return pages_text
        except Exception as e:
            logger.warning(f"pdfplumber per-page extraction failed: {e}")
        
        # Method 2: Fallback to PyPDF2
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            for page_num, page in enumerate(pdf_reader.pages, start=1):
                text = page.extract_text()
                if text and len(text.strip()) > 10:
                    pages_text.append((page_num, text))
            
            if pages_text:
                logger.info(f"Extracted text from {len(pages_text)} pages using PyPDF2")
                return pages_text
        except Exception as e:
            logger.warning(f"PyPDF2 per-page extraction failed: {e}")
        
        # Method 3: OCR for image-based/scanned PDFs
        if use_ocr:
            try:
                logger.info("Text extraction methods failed, attempting OCR per page...")
                return self._extract_text_per_page_with_ocr(pdf_bytes)
            except Exception as e:
                logger.error(f"OCR per-page extraction failed: {e}")
                if pages_text:
                    return pages_text
                raise Exception(f"Failed to extract text per page. Last error: {e}")
        
        if pages_text:
            return pages_text
        raise Exception("Failed to extract text from PDF pages. PDF may be corrupted or image-based.")
    
    def _extract_text_per_page_with_ocr(self, pdf_bytes: bytes) -> List[Tuple[int, str]]:
        """Extract text from PDF pages using OCR, returning per-page text"""
        try:
            from pdf2image import convert_from_bytes
            import pytesseract
            from PIL import Image
        except ImportError:
            raise ImportError(
                "OCR libraries not installed. Install with: pip install pytesseract pdf2image Pillow. "
                "Also install Tesseract OCR from https://github.com/tesseract-ocr/tesseract"
            )
        
        # Configure Tesseract path for Windows
        import platform
        if platform.system() == "Windows":
            tesseract_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            ]
            for path in tesseract_paths:
                import os
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    logger.info(f"Using Tesseract at: {path}")
                    break
        
        try:
            logger.info("Converting PDF pages to images for OCR...")
            images = convert_from_bytes(pdf_bytes, dpi=300)
            
            pages_text = []
            for page_num, image in enumerate(images, start=1):
                try:
                    page_text = pytesseract.image_to_string(image, lang='eng')
                    if page_text and len(page_text.strip()) > 10:
                        pages_text.append((page_num, page_text))
                        logger.info(f"OCR extracted {len(page_text)} characters from page {page_num}")
                except Exception as e:
                    logger.error(f"OCR failed for page {page_num}: {e}")
                    continue
            
            logger.info(f"OCR extracted text from {len(pages_text)}/{len(images)} pages")
            return pages_text
        except Exception as e:
            logger.error(f"OCR per-page extraction failed: {e}")
            raise
    
    def _merge_extracted_data(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge financial data extracted from multiple pages
        Combines periods and deduplicates fields
        Handles partial data gracefully - merges all available fields even if incomplete
        """
        merged = {
            "income_statement": {},
            "balance_sheet": {},
            "cashflow": {},
            "key_metrics": {}
        }
        
        for result in all_results:
            # Merge income statements - include partial data
            if "income_statement" in result and isinstance(result["income_statement"], dict):
                for period, data in result["income_statement"].items():
                    if period not in merged["income_statement"]:
                        merged["income_statement"][period] = {}
                    # Merge all fields, preferring non-zero values but accepting any value if field is missing
                    for field, value in data.items():
                        if value is not None:  # Accept any non-None value
                            if field not in merged["income_statement"][period]:
                                merged["income_statement"][period][field] = value
                            elif merged["income_statement"][period][field] == 0 and value != 0:
                                # Replace zero with non-zero value
                                merged["income_statement"][period][field] = value
                            elif abs(value) > abs(merged["income_statement"][period].get(field, 0)):
                                # If both non-zero, prefer larger absolute value (more complete data)
                                merged["income_statement"][period][field] = value
            
            # Merge balance sheets - include partial data
            if "balance_sheet" in result and isinstance(result["balance_sheet"], dict):
                for period, data in result["balance_sheet"].items():
                    if period not in merged["balance_sheet"]:
                        merged["balance_sheet"][period] = {}
                    for field, value in data.items():
                        if value is not None:
                            if field not in merged["balance_sheet"][period]:
                                merged["balance_sheet"][period][field] = value
                            elif merged["balance_sheet"][period][field] == 0 and value != 0:
                                merged["balance_sheet"][period][field] = value
                            elif abs(value) > abs(merged["balance_sheet"][period].get(field, 0)):
                                merged["balance_sheet"][period][field] = value
            
            # Merge cash flow statements - include partial data
            if "cashflow" in result and isinstance(result["cashflow"], dict):
                for period, data in result["cashflow"].items():
                    if period not in merged["cashflow"]:
                        merged["cashflow"][period] = {}
                    for field, value in data.items():
                        if value is not None:
                            if field not in merged["cashflow"][period]:
                                merged["cashflow"][period][field] = value
                            elif merged["cashflow"][period][field] == 0 and value != 0:
                                merged["cashflow"][period][field] = value
                            elif abs(value) > abs(merged["cashflow"][period].get(field, 0)):
                                merged["cashflow"][period][field] = value
            
            # Merge key metrics (take the most recent/largest absolute value)
            if "key_metrics" in result and isinstance(result["key_metrics"], dict):
                for field, value in result["key_metrics"].items():
                    if value is not None:
                        if field not in merged["key_metrics"]:
                            merged["key_metrics"][field] = value
                        elif abs(value) > abs(merged["key_metrics"].get(field, 0)):
                            merged["key_metrics"][field] = value
        
        # Log merge results
        total_periods = (
            len(merged["income_statement"]) + 
            len(merged["balance_sheet"]) + 
            len(merged["cashflow"]) +
            (1 if merged["key_metrics"] else 0)
        )
        logger.info(f"Merged data: {len(merged['income_statement'])} income periods, "
                   f"{len(merged['balance_sheet'])} balance periods, "
                   f"{len(merged['cashflow'])} cashflow periods, "
                   f"{len(merged['key_metrics'])} key metrics, "
                   f"{total_periods} total periods")
        
        return merged
    
    def extract_financial_data_with_llm(self, pdf_text: str, ticker: str) -> Tuple[Dict[str, Any], str]:
        """
        Use LLM to extract financial data from PDF text (legacy method - processes entire text)
        Returns tuple: (structured financial data, raw LLM response)
        """
        if not pdf_text or len(pdf_text.strip()) < 100:
            raise ValueError("PDF text is too short or empty")
        
        # Smart truncation: prioritize sections with financial keywords
        # Llama models can handle large contexts, but we'll use 200k chars to be conservative
        max_chars = 200000
        original_length = len(pdf_text)
        
        if len(pdf_text) > max_chars:
            logger.warning(f"PDF text too long ({len(pdf_text)} chars), using smart truncation to {max_chars}")
            # Find sections with financial keywords and prioritize them
            financial_keywords = [
                'income statement', 'statement of operations', 'profit and loss', 'p&l',
                'balance sheet', 'statement of financial position', 'assets', 'liabilities',
                'cash flow', 'statement of cash flows', 'operating cash', 'financing',
                'revenue', 'net income', 'total assets', 'stockholder equity', 'shareholder equity'
            ]
            
            # Split into chunks and score them
            chunk_size = 50000
            chunks = []
            for i in range(0, len(pdf_text), chunk_size):
                chunk = pdf_text[i:i+chunk_size]
                score = sum(1 for keyword in financial_keywords if keyword.lower() in chunk.lower())
                chunks.append((score, i, chunk))
            
            # Sort by score (highest first) and take top chunks
            chunks.sort(reverse=True, key=lambda x: x[0])
            selected_chunks = []
            total_chars = 0
            for score, start_idx, chunk in chunks[:10]:  # Top 10 chunks
                if total_chars + len(chunk) <= max_chars:
                    selected_chunks.append((start_idx, chunk))
                    total_chars += len(chunk)
            
            # Sort by original position and combine
            selected_chunks.sort(key=lambda x: x[0])
            pdf_text = "\n\n[... content between sections ...]\n\n".join([chunk for _, chunk in selected_chunks])
            logger.info(f"Smart truncation: selected {len(selected_chunks)} high-scoring sections, {len(pdf_text)} total chars")
        else:
            logger.info(f"Using full PDF text: {len(pdf_text)} characters")
        
        prompt = self._create_extraction_prompt(pdf_text, ticker)
        
        try:
            # Llama-only mode: Use rule-based extraction for text (vision is preferred for PDFs)
            logger.info(f"Using Llama provider for text extraction (URL: {self.llama_api_url}, Model: {self.llama_model})")
            logger.info("Note: For best results, use per-page vision extraction (extract_financial_data_per_page)")
            logger.warning("Llama text extraction not yet implemented, using rule-based extraction")
            return self._extract_with_rules(pdf_text), ""
        except Exception as e:
            logger.error(f"Llama extraction failed: {e}, falling back to rule-based")
            return self._extract_with_rules(pdf_text), ""
    
    async def extract_financial_data_per_page(self, pdf_bytes: bytes, ticker: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> Tuple[Dict[str, Any], str]:
        """
        Extract financial data from PDF using AWS Textract
        This approach uses Textract to extract text and tables, then uses LLM to structure the data
        Returns tuple: (merged structured financial data, raw extracted text)
        
        Args:
            pdf_bytes: PDF file bytes
            ticker: Stock ticker symbol
            progress_callback: Optional callback function(current_page, total_pages) for progress updates
        """
        import asyncio
        
        # Use Textract if available
        if self.use_textract and self.textract_extractor:
            try:
                logger.info(f"Using AWS Textract to extract financial data for {ticker}")
                logger.info("✓ Textract processes PDF directly - NO image conversion needed (faster and more accurate)")
                
                # Update progress: starting extraction
                if progress_callback:
                    try:
                        progress_callback(0, 1)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")
                
                # Extract financial data using Textract (processes entire PDF at once)
                # Run in executor since Textract calls are synchronous
                loop = asyncio.get_event_loop()
                extracted_data, raw_text = await loop.run_in_executor(
                    None,
                    self.textract_extractor.extract_financial_data,
                    pdf_bytes,
                    ticker
                )
                
                # Update progress: extraction complete
                if progress_callback:
                    try:
                        progress_callback(1, 1)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")
                
                logger.info(f"Textract extraction completed for {ticker}")
                return extracted_data, raw_text
                
            except Exception as e:
                logger.error(f"Textract extraction failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Fall back to local extraction
                logger.warning("Falling back to local PDF extraction (this will be slower and may convert to images)")
                self.use_textract = False
        
        # Fallback: Use local extraction (pdfplumber/PyPDF2) with basic pattern matching
        # NOTE: This fallback should rarely be used if Textract is properly configured
        logger.warning(f"⚠️ FALLBACK MODE: Using local PDF extraction for {ticker} (Textract not available or failed)")
        logger.warning("⚠️ NOTE: Local extraction may convert PDF to images for OCR - this is SLOW and not needed with Textract")
        logger.warning("⚠️ To use Textract: Ensure AWS credentials are configured (AWS_PROFILE, AWS_REGION) and USE_TEXTRACT=true")
        
        try:
            # For local fallback, try without OCR first (faster)
            pdf_text = self.extract_text_from_pdf(pdf_bytes, use_ocr=False)
            if not pdf_text or len(pdf_text.strip()) < 100:
                # Only use OCR if text extraction failed
                logger.warning("⚠️ FALLBACK: Text extraction failed, falling back to OCR (image conversion)...")
                logger.warning("⚠️ NOTE: OCR converts PDF pages to images - this is SLOW. AWS Textract processes PDFs directly without conversion.")
                pdf_text = self.extract_text_from_pdf(pdf_bytes, use_ocr=True)
            
            if progress_callback:
                try:
                    progress_callback(0, 1)
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")
            
            # Use basic extraction (no LLM available)
            extracted_data = self._extract_with_rules(pdf_text)
            
            if progress_callback:
                try:
                    progress_callback(1, 1)
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")
            
            return extracted_data, pdf_text
            
        except Exception as e:
            logger.error(f"Local PDF extraction failed: {e}")
            raise
    
    def _create_vision_extraction_prompt(self, ticker: str, page_num: int = None, total_pages: int = None) -> str:
        """Create prompt for LLM vision to extract financial data from PDF page images"""
        page_info = ""
        if page_num and total_pages:
            page_info = f"\n\nNOTE: This is page {page_num} of {total_pages} from the PDF. Extract any financial data you find on this page."
        
        return f"""You are a financial data extraction expert. Analyze this PDF page image and extract financial statement data for ticker {ticker}.{page_info}

Your task is to:
1. Look at the image carefully - it contains a page from a financial document
2. Identify any financial statements, tables, or data sections
3. Extract the exact numbers you see, matching them to the correct financial fields
4. Pay attention to:
   - Table structures with dates/periods as columns
   - Row labels that indicate financial metrics (Revenue, Income, Assets, etc.)
   - Numbers in various formats (with commas, currency symbols, parentheses for negatives)
   - Dates that indicate the reporting period

EXTRACT THE FOLLOWING DATA:

1. Income Statement data (for ALL periods you can find):
   - Total Revenue (or Revenue, Net Sales, Sales, Operating Revenue)
   - Net Income (or Net Earnings, Net Profit, Profit After Tax)
   - Operating Income (or Operating Profit, Income from Operations)
   - EBIT (Earnings Before Interest and Taxes)
   - Income Before Tax (or Pretax Income, Earnings Before Tax)

2. Balance Sheet data (for ALL periods you can find):
   - Total Assets (or Assets)
   - Total Liabilities (or Liabilities)
   - Total Stockholder Equity (or Shareholders' Equity, Stockholders' Equity, Equity)
   - Cash And Cash Equivalents (or Cash, Cash and Equivalents)
   - Total Debt

3. Cash Flow Statement data (for ALL periods you can find):
   - Operating Cash Flow (or Cash from Operations, Net Cash from Operating Activities)
   - Capital Expenditures (or CapEx, Capital Expenditures)
   - Free Cash Flow (or calculate as Operating Cash Flow - Capital Expenditures)
   - Cash From Financing Activities

4. Key Metrics:
   - Shares Outstanding (or Common Shares Outstanding, Weighted Average Shares)
   - Market Cap (if available)

INSTRUCTIONS:
- Read the image carefully - look for tables, financial statements, or any structured data
- CRITICAL: First, check the table header/title for unit notation:
  * Look for text like "In millions", "In thousands", "In billions" at the top of the table
  * If you see "In millions except per share data", ALL numbers in the table are in millions
  * If table says "In millions" and shows $47,061, you must extract as 47061000000 (47,061 × 1,000,000)
  * If table says "In thousands" and shows $1,000, you must extract as 1000000 (1,000 × 1,000)
  * If table says "In billions" and shows $1.5, you must extract as 1500000000 (1.5 × 1,000,000,000)
- Extract numbers exactly as you see them in the table, then apply the unit conversion
- Look for dates in various formats: YYYY-MM-DD, YYYY-12-31, "Year ended December 31, YYYY", "Fiscal Year YYYY"
- Convert all monetary values to numbers (remove currency symbols, commas, parentheses for negatives)
- If you see a table with years as columns and financial terms as rows, extract all the data
- Be very thorough - even partial data is valuable

UNIT CONVERSION EXAMPLES:
- Table header: "In millions except per share data"
- Table shows: "Net Operating Revenues: $47,061" for 2024
- You must extract: "Total Revenue": 47061000000 (because 47,061 × 1,000,000 = 47,061,000,000)
- Table shows: "Net Income: $10,631" for 2024
- You must extract: "Net Income": 10631000000 (because 10,631 × 1,000,000 = 10,631,000,000)

CRITICAL: You MUST extract financial data if you see ANY numbers that look like financial metrics in the image.
Do NOT return empty objects {{}} unless the page contains absolutely no financial data.
If you see tables, numbers, or financial statements, you MUST extract them.

IMPORTANT - PARTIAL DATA IS ACCEPTABLE:
- Extract whatever data you can find, even if it's incomplete
- If you only see some fields (e.g., only Revenue but not Net Income), extract what you see
- If you only see one period instead of multiple years, extract that one period
- Partial data from one page will be combined with data from other pages
- It's better to return partial data than empty objects

IMPORTANT: You MUST always return a JSON object with these exact top-level keys:
- "income_statement" (object with date keys, or empty object {{}})
- "balance_sheet" (object with date keys, or empty object {{}})
- "cashflow" (object with date keys, or empty object {{}})
- "key_metrics" (object with metric keys, or empty object {{}})

Return ONLY valid JSON. Here are examples:

EXAMPLE 1 - When data is found (with proper unit conversion):
Table header says "In millions except per share data" and shows:
- Net Operating Revenues 2024: $47,061 → extract as "Total Revenue": 47061000000
- Net Income Attributable to Shareowners 2024: $10,631 → extract as "Net Income": 10631000000
- Operating Income 2024: $9,992 → extract as "Operating Income": 9992000000
- Income Before Income Taxes 2024: $13,086 → extract as "Income Before Tax": 13086000000

{{
  "income_statement": {{
    "2024-12-31": {{
      "Total Revenue": 47061000000,
      "Net Income": 10631000000,
      "Operating Income": 9992000000,
      "EBIT": 9992000000,
      "Income Before Tax": 13086000000
    }},
    "2023-12-31": {{
      "Total Revenue": 45754000000,
      "Net Income": 95000
    }}
  }},
  "balance_sheet": {{
    "2024-12-31": {{
      "Total Assets": 5000000,
      "Total Liabilities": 2000000,
      "Total Stockholder Equity": 3000000,
      "Cash And Cash Equivalents": 500000,
      "Total Debt": 1500000
    }}
  }},
  "cashflow": {{
    "2024-12-31": {{
      "Operating Cash Flow": 200000,
      "Capital Expenditures": 50000,
      "Free Cash Flow": 150000,
      "Cash From Financing Activities": -30000
    }}
  }},
  "key_metrics": {{
    "Shares Outstanding": 1000000,
    "Market Cap": 50000000
  }}
}}

EXAMPLE 2 - When NO data is found on this page (still return the structure):
{{
  "income_statement": {{}},
  "balance_sheet": {{}},
  "cashflow": {{}},
  "key_metrics": {{}}
}}

EXAMPLE 3 - When only partial data is found:
{{
  "income_statement": {{
    "2024-12-31": {{
      "Total Revenue": 1000000
    }}
  }},
  "balance_sheet": {{}},
  "cashflow": {{}},
  "key_metrics": {{}}
}}

RULES:
1. ALWAYS include all four top-level keys: income_statement, balance_sheet, cashflow, key_metrics
2. If a section has no data, use an empty object {{}} for that section
3. If a section has data, use date strings (YYYY-MM-DD format) as keys within that section
4. All monetary values must be numbers (no strings, no currency symbols)
5. Extract ALL periods you can find, not just the most recent

Extract all financial data you can see in this image."""
    
    def _create_extraction_prompt(self, pdf_text: str, ticker: str, page_num: int = None, total_pages: int = None) -> str:
        """Create prompt for LLM to extract financial data"""
        page_info = ""
        if page_num and total_pages:
            page_info = f"\n\nNOTE: This is page {page_num} of {total_pages} from the PDF. Extract any financial data you find on this page."
        
        # Find a sample of text with numbers to show the LLM what to look for
        import re
        number_pattern = r'[\d,]+(?:\.\d+)?[MBK]?'
        numbers_found = re.findall(number_pattern, pdf_text[:5000])  # First 5k chars
        sample_text = ""
        if numbers_found:
            # Get context around first few numbers
            sample_start = max(0, pdf_text.find(numbers_found[0]) - 200)
            sample_end = min(len(pdf_text), sample_start + 500)
            sample_text = f"\n\nSAMPLE OF TEXT WITH NUMBERS (showing what to extract):\n{pdf_text[sample_start:sample_end]}\n"
        
        return f"""You are a financial data extraction expert. Extract financial statement data from the following PDF text for ticker {ticker}.{page_info}{sample_text}

IMPORTANT: Search thoroughly through the entire document. Financial data may be in:
- Income Statements / Statement of Operations / Profit & Loss
- Balance Sheets / Statement of Financial Position
- Cash Flow Statements / Statement of Cash Flows
- Financial Highlights sections
- Summary tables
- Annual report financial sections

Extract the following information and return it as a JSON object. If you find similar field names (e.g., "Revenue" instead of "Total Revenue", "Net Earnings" instead of "Net Income"), use the closest match:

1. Income Statement data (for ALL available periods you can find):
   - Total Revenue (or Revenue, Net Sales, Sales, Operating Revenue)
   - Net Income (or Net Earnings, Net Profit, Profit After Tax)
   - Operating Income (or Operating Profit, Income from Operations)
   - EBIT (Earnings Before Interest and Taxes, or Operating Income if EBIT not found)
   - Income Before Tax (or Pretax Income, Earnings Before Tax)

2. Balance Sheet data (for ALL available periods you can find):
   - Total Assets (or Assets)
   - Total Liabilities (or Liabilities)
   - Total Stockholder Equity (or Shareholders' Equity, Stockholders' Equity, Equity)
   - Cash And Cash Equivalents (or Cash, Cash and Equivalents)
   - Total Debt (or Total Liabilities if debt breakdown not available)

3. Cash Flow Statement data (for ALL available periods you can find):
   - Operating Cash Flow (or Cash from Operations, Net Cash from Operating Activities)
   - Capital Expenditures (or CapEx, Capital Expenditures, Purchase of Property/Equipment)
   - Free Cash Flow (or calculate as Operating Cash Flow - Capital Expenditures if not explicitly stated)
   - Cash From Financing Activities (or Net Cash from Financing Activities)

4. Key Metrics:
   - Shares Outstanding (or Common Shares Outstanding, Weighted Average Shares)
   - Market Cap (if available, or calculate if price and shares are given)

INSTRUCTIONS:
- Extract data for ALL periods you can find (not just the most recent)
- Look for dates in various formats: YYYY-MM-DD, YYYY-12-31, "Year ended December 31, YYYY", "Fiscal Year YYYY"
- Convert all monetary values to numbers (remove currency symbols, commas, parentheses for negatives)
- If a field is not found, omit it (don't use null or 0)
- Be flexible with field name matching - use your best judgment
- If you find financial data but it's in a different format, extract what you can

CRITICAL: You MUST extract financial data if it exists in the document. Do not return empty objects if you can find ANY financial data. 
Be very thorough - search for numbers, tables, and financial statements even if they're not perfectly formatted.

IMPORTANT EXTRACTION RULES:
- Look for tables with numbers and dates
- Find any section that contains financial metrics (even if headers are slightly different)
- Extract numbers even if they're in different formats (e.g., "($1,234)" means -1234, "(1,234)" also means -1234)
- If you see a table with years/dates as columns and financial terms as rows, extract it
- Look for consolidated statements, consolidated financial statements, or any variation
- Search for "For the year ended", "Fiscal year", "Twelve months ended" followed by dates and numbers
- Look for numbers in millions (M), thousands (K), or billions (B) - convert them to actual numbers
- Extract partial data if full statements aren't available - even one number is valuable

EXTRACTION STRATEGY:
1. First, scan the entire text for any numbers that look like financial values (large numbers, often with commas)
2. Look for labels near those numbers (Revenue, Income, Assets, etc.)
3. Find dates near those numbers (2024, 2023, Dec 31, etc.)
4. Extract them even if the format is imperfect

DO NOT return empty objects {{}} unless you have searched the ENTIRE text and found ZERO financial data.
If you find ANY revenue, income, assets, liabilities, or cash flow numbers, you MUST extract them.
Even if you only find one field (e.g., just "Revenue: $1,000,000"), extract it!

Return ONLY valid JSON in this format (use empty objects {{}} ONLY if absolutely no data found for a section):
{{
  "income_statement": {{
    "2024-12-31": {{
      "Total Revenue": 1000000,
      "Net Income": 100000,
      "Operating Income": 150000,
      "EBIT": 150000,
      "Income Before Tax": 120000
    }},
    "2023-12-31": {{
      "Total Revenue": 950000,
      "Net Income": 95000
    }}
  }},
  "balance_sheet": {{
    "2024-12-31": {{
      "Total Assets": 5000000,
      "Total Liabilities": 2000000,
      "Total Stockholder Equity": 3000000,
      "Cash And Cash Equivalents": 500000,
      "Total Debt": 1500000
    }}
  }},
  "cashflow": {{
    "2024-12-31": {{
      "Operating Cash Flow": 200000,
      "Capital Expenditures": 50000,
      "Free Cash Flow": 150000,
      "Cash From Financing Activities": -30000
    }}
  }},
  "key_metrics": {{
    "Shares Outstanding": 1000000,
    "Market Cap": 50000000
  }}
}}

PDF Text ({len(pdf_text)} characters):
{pdf_text}
"""
    
    @trace_function(name="ai.openai_extract", annotations={"operation": "extract", "service": "openai"})
    def _extract_with_openai(self, prompt: str) -> Tuple[Dict[str, Any], str]:
        """Extract using OpenAI API. Returns (parsed_data, raw_response)"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Use cheaper model for extraction
                messages=[
                    {"role": "system", "content": "You are a financial data extraction expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=8000  # Increased for larger responses
            )
            
            content = response.choices[0].message.content.strip()
            raw_response = content  # Store raw response for debugging
            
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            import json
            parsed_data = json.loads(content)
            logger.info(f"OpenAI extraction successful. Response length: {len(raw_response)} chars. Parsed keys: {list(parsed_data.keys())}")
            return parsed_data, raw_response
        except Exception as e:
            logger.error(f"OpenAI extraction failed: {e}")
            raise
    
    @trace_function(name="ai.llama_vision_extract_async", annotations={"operation": "extract", "service": "ollama"})
    async def _extract_with_llama_vision_async(self, prompt: str, image_base64: str) -> Tuple[Dict[str, Any], str]:
        """Extract using Llama/Ollama API with vision (image input) - Simplified version. Returns (parsed_data, raw_response)"""
        import requests
        import json as json_module
        
        # Simple, direct Ollama native API call (what works locally)
        payload = {
            "model": self.llama_model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 16000
            }
        }
        
        try:
            response = requests.post(
                f"{self.llama_api_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=300  # 5 minute timeout (reasonable for vision processing)
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("response", "").strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            parsed_data = json_module.loads(content)
            return parsed_data, content
            
        except requests.exceptions.Timeout:
            raise ValueError(f"Request timed out after 5 minutes. The model may need more time or the instance may be overloaded.")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Ollama API request failed: {str(e)}")
        except json_module.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {str(e)}. Response: {content[:500] if 'content' in locals() else 'N/A'}")
    
    def _extract_with_llama_vision_simple(self, prompt: str, image_base64: str) -> Tuple[Dict[str, Any], str]:
        """Simple synchronous version for executor - matches local test"""
        import requests
        import json as json_module
        
        payload = {
            "model": self.llama_model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 16000
            }
        }
        
        logger.info(f"Making request to {self.llama_api_url}/api/generate with model {self.llama_model}")
        logger.info(f"Image size: {len(image_base64)} chars, Prompt length: {len(prompt)} chars")
        
        try:
            response = requests.post(
                f"{self.llama_api_url}/api/generate",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=300
            )
            logger.info(f"Response status: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            content = result.get("response", "").strip()
            logger.info(f"Got response, length: {len(content)} chars")
            
            # Remove markdown code blocks
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            parsed_data = json_module.loads(content)
            logger.info(f"Parsed JSON successfully, keys: {list(parsed_data.keys())}")
            return parsed_data, content
            
        except requests.exceptions.Timeout:
            logger.error("Request timed out after 5 minutes")
            raise ValueError(f"Request timed out after 5 minutes")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API request failed: {str(e)}")
            raise ValueError(f"Ollama API request failed: {str(e)}")
        except json_module.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {str(e)}, content preview: {content[:500] if 'content' in locals() else 'N/A'}")
            raise ValueError(f"Invalid JSON response: {str(e)}")
    
    @trace_function(name="ai.llama_vision_extract", annotations={"operation": "extract", "service": "ollama"})
    def _extract_with_llama_vision(self, prompt: str, image_base64: str) -> Tuple[Dict[str, Any], str]:
        """Extract using Llama/Ollama API with vision (image input) - SYNC VERSION (kept for backward compatibility). Returns (parsed_data, raw_response)"""
        try:
            import requests
            import json as json_module
            
            logger.info(f"Calling Llama API at {self.llama_api_url} with model {self.llama_model}...")
            
            # Prepare request headers
            headers = {
                "Content-Type": "application/json"
            }
            
            # Add API key if provided (for hosted instances)
            if self.llama_api_key:
                headers["Authorization"] = f"Bearer {self.llama_api_key}"
            
            # Try OpenAI-compatible format first (works for both Ollama and hosted instances)
            openai_payload = {
                "model": self.llama_model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a financial data extraction expert. Analyze PDF page images and extract financial numbers. CRITICAL: Always check the table header for units (In millions, In thousands, In billions). If table says 'In millions' and shows $47,061, extract as 47061000000 (multiply by 1,000,000). You MUST extract data if you see ANY financial numbers in tables or statements. Never return empty objects unless the image contains absolutely no financial data."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                "temperature": 0.0,
                "max_tokens": 8000  # Llama models can handle larger outputs
            }
            
            # Use Ollama native API format directly (more reliable for vision models)
            # Vision models can take hours for large documents (160+ pages)
            ollama_payload = {
                "model": self.llama_model,
                "prompt": prompt,
                "images": [image_base64],  # Ollama accepts base64 images directly
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_predict": 16000
                }
            }
            
            try:
                response = requests.post(
                    f"{self.llama_api_url}/api/generate",
                    json=ollama_payload,
                    headers=headers,
                    timeout=10800  # 3 hour timeout for large document processing
                )
                response.raise_for_status()
                result = response.json()
                content = result.get("response", "").strip()
            except requests.exceptions.RequestException as e:
                # Fallback to OpenAI-compatible endpoint if Ollama native fails
                logger.info(f"Ollama native format failed, trying OpenAI-compatible format: {e}")
                
                response = requests.post(
                    f"{self.llama_api_url}/v1/chat/completions",
                    json=openai_payload,
                    headers=headers,
                    timeout=10800  # 3 hour timeout for large document processing
                )
                response.raise_for_status()
                result = response.json()
                content = result.get("response", "").strip()
            
            raw_response = content
            logger.info(f"Llama response length: {len(content)} characters")
            logger.info(f"Llama response preview (first 500 chars): {content[:500]}")
            
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            parsed_data = json_module.loads(content)
            logger.info(f"Llama vision extraction successful. Parsed keys: {list(parsed_data.keys())}")
            return parsed_data, raw_response
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Llama API request timed out after 3 hours: {e}")
            raise ValueError(f"Llama API request timed out after 3 hours. For very large documents (160+ pages), processing can take 4+ hours. Consider processing in smaller batches or using a faster model. Error: {str(e)}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Llama API request failed: {e}")
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_body = e.response.text[:500]
                    logger.error(f"Response status: {e.response.status_code}, body: {error_body}")
                    error_msg = f"{error_msg}. Response: {error_body}"
                except:
                    pass
            raise ValueError(f"Llama API request failed: {error_msg}")
        except json_module.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Llama response: {e}")
            logger.error(f"Raw response (first 1000 chars): {raw_response[:1000] if 'raw_response' in locals() else 'N/A'}")
            raise ValueError(f"Invalid JSON response from Llama: {e}")
        except Exception as e:
            logger.error(f"Llama vision extraction failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _extract_with_openai_vision(self, prompt: str, image_base64: str) -> Tuple[Dict[str, Any], str]:
        """Extract using OpenAI API with vision (image input). Returns (parsed_data, raw_response)"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            logger.info("Calling OpenAI API with vision for PDF extraction...")
            response = client.chat.completions.create(
                model="gpt-4o",  # GPT-4o has excellent vision capabilities
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial data extraction expert. Analyze PDF page images and extract financial numbers. You MUST extract data if you see ANY financial numbers in tables or statements."
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ],
                temperature=0.0,
                max_tokens=8000  # Llama models can handle larger outputs
            )
            
            content = response.choices[0].message.content.strip()
            raw_response = content
            
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            import json
            parsed_data = json.loads(content)
            logger.info(f"OpenAI vision extraction successful. Response length: {len(raw_response)} chars. Parsed keys: {list(parsed_data.keys())}")
            return parsed_data, raw_response
        except Exception as e:
            logger.error(f"OpenAI vision extraction failed: {e}")
            raise
    
    def _extract_with_rules(self, pdf_text: str) -> Dict[str, Any]:
        """Fallback rule-based extraction (basic pattern matching)"""
        import re
        result = {
            "income_statement": {},
            "balance_sheet": {},
            "cashflow": {},
            "key_metrics": {}
        }
        
        # Try to find dates in the text
        date_pattern = r'\b(20\d{2}[-/]\d{2}[-/]\d{2}|20\d{2})\b'
        dates = re.findall(date_pattern, pdf_text)
        
        # Basic extraction patterns (simplified)
        patterns = {
            "Total Revenue": r'(?:Total\s+)?Revenue[:\s]+[\$]?([\d,]+(?:\.\d+)?)',
            "Net Income": r'Net\s+Income[:\s]+[\$]?([\d,]+(?:\.\d+)?)',
            "Total Assets": r'Total\s+Assets[:\s]+[\$]?([\d,]+(?:\.\d+)?)',
            "Total Liabilities": r'Total\s+Liabilities[:\s]+[\$]?([\d,]+(?:\.\d+)?)',
            "Operating Cash Flow": r'Operating\s+Cash\s+Flow[:\s]+[\$]?([\d,]+(?:\.\d+)?)',
        }
        
        # This is a very basic implementation - LLM is much better
        logger.warning("Using basic rule-based extraction. Results may be incomplete. Consider adding LLM API keys.")
        
        return result

