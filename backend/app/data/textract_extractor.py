"""
AWS Textract integration for PDF financial data extraction
Replaces Ollama/EC2-based extraction with serverless AWS Textract
"""
import os
import logging
import json
import boto3
from typing import Dict, List, Optional, Any, Tuple
from botocore.exceptions import ClientError
import io

logger = logging.getLogger(__name__)


class TextractExtractor:
    """Extract text and tables from PDFs using AWS Textract"""
    
    def __init__(self):
        self.aws_region = os.getenv("AWS_REGION", "eu-west-1")
        self.aws_profile = os.getenv("AWS_PROFILE", "Cerebrum")
        
        # Initialize boto3 session
        try:
            self.session = boto3.Session(profile_name=self.aws_profile, region_name=self.aws_region)
            self.textract = self.session.client('textract')
            logger.info(f"TextractExtractor initialized (region: {self.aws_region}, profile: {self.aws_profile})")
        except Exception as e:
            logger.error(f"Failed to initialize Textract client: {e}")
            raise
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """
        Extract text from PDF using Textract AnalyzeDocument API
        Returns extracted text as a string
        
        NOTE: Textract works directly with PDF bytes - NO image conversion needed!
        """
        try:
            logger.info(f"Extracting text from PDF using Textract (size: {len(pdf_bytes)} bytes)")
            logger.info("✓ Textract processes PDF directly - NO image conversion needed (faster and more accurate)")
            
            # Textract AnalyzeDocument API - works directly with PDF bytes
            response = self.textract.analyze_document(
                Document={'Bytes': pdf_bytes},
                FeatureTypes=['TABLES', 'FORMS']  # Extract tables and forms for financial data
            )
            
            # Parse Textract response
            text_blocks = []
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    text_blocks.append(block.get('Text', ''))
            
            extracted_text = '\n'.join(text_blocks)
            logger.info(f"Textract extracted {len(extracted_text)} characters from PDF")
            
            return extracted_text
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'InvalidParameterException':
                logger.error(f"Textract error: Invalid PDF format - {e}")
                raise ValueError(f"Invalid PDF format: {str(e)}")
            elif error_code == 'AccessDeniedException':
                logger.error(f"Textract error: Access denied - {e}")
                raise ValueError(f"AWS Textract access denied. Check IAM permissions: {str(e)}")
            else:
                logger.error(f"Textract error: {e}")
                raise ValueError(f"AWS Textract error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error extracting text with Textract: {e}")
            raise
    
    def extract_tables_from_pdf(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Extract tables from PDF using Textract
        Returns list of tables, each as a dictionary with rows and columns
        
        NOTE: Textract works directly with PDF bytes - NO image conversion needed!
        """
        try:
            logger.info(f"Extracting tables from PDF using Textract (size: {len(pdf_bytes)} bytes)")
            logger.info("✓ Textract processes PDF directly - NO image conversion needed (faster and more accurate)")
            
            response = self.textract.analyze_document(
                Document={'Bytes': pdf_bytes},
                FeatureTypes=['TABLES']
            )
            
            # Parse tables from Textract response
            tables = self._parse_textract_tables(response)
            logger.info(f"Textract extracted {len(tables)} tables from PDF")
            
            return tables
            
        except Exception as e:
            logger.error(f"Error extracting tables with Textract: {e}")
            raise
    
    def _parse_textract_tables(self, response: Dict) -> List[Dict[str, Any]]:
        """
        Parse Textract response to extract structured table data
        """
        blocks = {block['Id']: block for block in response.get('Blocks', [])}
        tables = []
        
        # Find all table blocks
        for block_id, block in blocks.items():
            if block['BlockType'] == 'TABLE':
                table = self._parse_table_block(block, blocks)
                if table:
                    tables.append(table)
        
        return tables
    
    def _parse_table_block(self, table_block: Dict, all_blocks: Dict) -> Optional[Dict[str, Any]]:
        """
        Parse a single table block from Textract response
        """
        try:
            relationships = table_block.get('Relationships', [])
            cells = []
            
            # Get all cells in this table
            for relationship in relationships:
                if relationship['Type'] == 'CHILD':
                    for cell_id in relationship.get('Ids', []):
                        if cell_id in all_blocks:
                            cell_block = all_blocks[cell_id]
                            if cell_block['BlockType'] == 'CELL':
                                cells.append(cell_block)
            
            # Organize cells into rows and columns
            if not cells:
                return None
            
            # Get row and column indices
            rows = {}
            for cell in cells:
                row_idx = cell.get('RowIndex', 0)
                col_idx = cell.get('ColumnIndex', 0)
                
                if row_idx not in rows:
                    rows[row_idx] = {}
                
                # Extract text from cell
                cell_text = self._extract_cell_text(cell, all_blocks)
                rows[row_idx][col_idx] = cell_text
            
            # Convert to list of lists
            max_row = max(rows.keys()) if rows else 0
            max_col = max(max(rows[r].keys()) for r in rows) if rows else 0
            
            table_data = []
            for r in range(1, max_row + 1):
                row = []
                for c in range(1, max_col + 1):
                    row.append(rows.get(r, {}).get(c, ''))
                table_data.append(row)
            
            return {
                'rows': table_data,
                'row_count': len(table_data),
                'column_count': max_col if table_data else 0
            }
            
        except Exception as e:
            logger.warning(f"Error parsing table block: {e}")
            return None
    
    def _extract_cell_text(self, cell_block: Dict, all_blocks: Dict) -> str:
        """Extract text content from a cell block"""
        relationships = cell_block.get('Relationships', [])
        text_parts = []
        
        for relationship in relationships:
            if relationship['Type'] == 'CHILD':
                for entity_id in relationship.get('Ids', []):
                    if entity_id in all_blocks:
                        entity = all_blocks[entity_id]
                        if entity['BlockType'] == 'WORD':
                            text_parts.append(entity.get('Text', ''))
        
        return ' '.join(text_parts)
    
    def extract_financial_data(self, pdf_bytes: bytes, ticker: str) -> Tuple[Dict[str, Any], str]:
        """
        Extract financial data from PDF using Textract with OCR fallback
        This method:
        1. Tries Textract first (fast, accurate for supported PDFs)
        2. Falls back to OCR if Textract fails (slower but works with image-based PDFs)
        
        Returns: (structured_data, raw_text)
        """
        try:
            # Step 1: Try Textract first
            logger.info(f"Extracting financial data from PDF for {ticker} using AWS Textract...")
            logger.info("✓ Textract processes the entire PDF at once - NO per-page processing or image conversion needed")
            
            # Get both text and tables in one call for efficiency
            response = self.textract.analyze_document(
                Document={'Bytes': pdf_bytes},
                FeatureTypes=['TABLES', 'FORMS']  # Extract tables and forms for financial data
            )
            
            # Parse text from response
            text_blocks = []
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    text_blocks.append(block.get('Text', ''))
            text = '\n'.join(text_blocks)
            
            # Parse tables from response
            tables = self._parse_textract_tables(response)
            
            logger.info(f"Textract extracted {len(text)} characters of text and {len(tables)} tables")
            
            # Step 2: Parse structured tables directly to extract financial data
            logger.info(f"Parsing {len(tables)} tables to extract financial data for {ticker}...")
            structured_data = self._extract_financial_data_from_tables(tables, text, ticker)
            
            logger.info(f"Textract extraction complete. Found {len(structured_data.get('income_statement', {}))} income periods, "
                      f"{len(structured_data.get('balance_sheet', {}))} balance periods, "
                      f"{len(structured_data.get('cashflow', {}))} cashflow periods")
            
            return structured_data, text
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UnsupportedDocumentException':
                logger.warning(f"Textract failed with UnsupportedDocumentException: {e}")
                logger.info("⚠️ FALLBACK: PDF format not supported by Textract, falling back to OCR...")
                return self._extract_financial_data_with_ocr(pdf_bytes, ticker)
            else:
                logger.error(f"Textract error: {e}")
                logger.info("⚠️ FALLBACK: Textract error, falling back to OCR...")
                return self._extract_financial_data_with_ocr(pdf_bytes, ticker)
        except Exception as e:
            logger.error(f"Error extracting financial data with Textract: {e}")
            logger.info("⚠️ FALLBACK: Textract failed, falling back to OCR...")
            return self._extract_financial_data_with_ocr(pdf_bytes, ticker)
    
    def _extract_financial_data_with_ocr(self, pdf_bytes: bytes, ticker: str) -> Tuple[Dict[str, Any], str]:
        """
        Extract financial data using OCR fallback for image-based or unsupported PDFs
        """
        try:
            # Check if OCR is available
            from pdf2image import convert_from_bytes
            import pytesseract
            from PIL import Image, ImageEnhance, ImageFilter
        except ImportError:
            logger.error("OCR libraries not available. Install with: pip install pytesseract pdf2image Pillow")
            logger.error("Also install Tesseract OCR from: https://github.com/tesseract-ocr/tesseract")
            # Return empty data
            return {
                "income_statement": {},
                "balance_sheet": {},
                "cashflow": {},
                "key_metrics": {}
            }, ""
        
        logger.info(f"⚠️ FALLBACK MODE: Using OCR to extract financial data for {ticker}")
        logger.info("⚠️ NOTE: OCR converts PDF pages to images - this is SLOW but works with image-based/scanned PDFs")
        
        # Configure Tesseract for Windows
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
            # Convert PDF to images
            logger.info("Converting PDF to images for OCR...")
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
                    
                    # Perform OCR
                    page_text = pytesseract.image_to_string(image, lang='eng')
                    
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
                logger.error("OCR did not extract any text from PDF images")
                return {
                    "income_statement": {},
                    "balance_sheet": {},
                    "cashflow": {},
                    "key_metrics": {}
                }, ""
            
            full_text = "\n\n".join(text_parts)
            logger.info(f"✓ OCR completed: {successful_pages}/{len(images)} pages, {len(full_text)} total characters")
            
            # Extract financial data from OCR text using pattern matching
            structured_data = self._extract_financial_data_from_ocr_text(full_text, ticker)
            
            return structured_data, full_text
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            # Return empty data
            return {
                "income_statement": {},
                "balance_sheet": {},
                "cashflow": {},
                "key_metrics": {}
            }, ""
    
    def _extract_financial_data_from_tables(self, tables: List[Dict[str, Any]], text: str, ticker: str) -> Dict[str, Any]:
        """
        Extract financial data directly from Textract's structured tables
        Parses tables to find financial statements and extract periods/values
        """
        import re
        from datetime import datetime
        
        result = {
            "income_statement": {},
            "balance_sheet": {},
            "cashflow": {},
            "key_metrics": {}
        }
        
        # Financial field mappings (flexible matching)
        income_fields = {
            'total revenue': ['total revenue', 'revenue', 'net sales', 'sales', 'operating revenue', 'net revenues'],
            'net income': ['net income', 'net earnings', 'net profit', 'profit after tax', 'net income (loss)'],
            'operating income': ['operating income', 'operating profit', 'income from operations', 'operating earnings'],
            'ebit': ['ebit', 'earnings before interest and taxes', 'operating income'],
            'income before tax': ['income before tax', 'pretax income', 'earnings before tax', 'income before income taxes']
        }
        
        balance_fields = {
            'total assets': ['total assets', 'assets'],
            'total liabilities': ['total liabilities', 'liabilities'],
            'total stockholder equity': ['total stockholder equity', 'total shareholders equity', 'shareholders equity', 'stockholders equity', 'equity', 'total equity'],
            'cash and cash equivalents': ['cash and cash equivalents', 'cash', 'cash and equivalents', 'cash and short-term investments'],
            'total debt': ['total debt', 'debt', 'total long-term debt', 'long-term debt']
        }
        
        cashflow_fields = {
            'operating cash flow': ['operating cash flow', 'cash from operations', 'net cash from operating activities', 'cash provided by operating activities'],
            'capital expenditures': ['capital expenditures', 'capex', 'purchase of property and equipment', 'capital spending'],
            'free cash flow': ['free cash flow', 'fcf'],
            'cash from financing activities': ['cash from financing activities', 'net cash from financing activities', 'cash provided by financing activities']
        }
        
        # Find dates in text (for period identification)
        date_patterns = [
            r'\b(20\d{2})\b',  # Years like 2024, 2023
            r'\b(20\d{2})-12-31\b',  # Year-end dates
            r'year ended\s+december\s+31[,\s]+(20\d{2})',  # "Year ended December 31, 2024"
            r'fiscal year\s+(20\d{2})',  # "Fiscal Year 2024"
        ]
        
        def extract_dates(text: str) -> List[str]:
            """Extract potential year dates from text"""
            dates = set()
            for pattern in date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    year = match if isinstance(match, str) else match[0] if match else None
                    if year and len(year) == 4:
                        dates.add(f"{year}-12-31")  # Standardize to year-end format
            return sorted(list(dates), reverse=True)  # Most recent first
        
        # Extract dates from text
        periods = extract_dates(text)
        if not periods:
            # Fallback: use current year and previous 2 years
            current_year = datetime.now().year
            periods = [f"{current_year - i}-12-31" for i in range(3)]
        
        logger.info(f"Identified potential periods: {periods}")
        
        # Parse each table
        for table_idx, table in enumerate(tables):
            rows = table.get('rows', [])
            if not rows or len(rows) < 2:
                continue
            
            logger.debug(f"Processing table {table_idx + 1} with {len(rows)} rows")
            
            # Try to identify table type and find header row
            header_row_idx = None
            for i, row in enumerate(rows[:3]):  # Check first 3 rows for headers
                row_text = ' '.join(str(cell).lower() for cell in row if cell)
                if any(keyword in row_text for keyword in ['revenue', 'income', 'assets', 'liabilities', 'cash flow', 'balance sheet']):
                    header_row_idx = i
                    break
            
            if header_row_idx is None:
                header_row_idx = 0  # Assume first row is header
            
            # Extract header to find period columns
            header = rows[header_row_idx] if header_row_idx < len(rows) else []
            
            # Find period columns (columns with dates/years)
            period_columns = {}
            for col_idx, header_cell in enumerate(header):
                cell_text = str(header_cell).strip()
                # Check if this column header contains a date/year
                for period in periods:
                    year = period.split('-')[0]
                    if year in cell_text or any(re.findall(r'\b' + year + r'\b', cell_text, re.IGNORECASE)):
                        period_columns[col_idx] = period
                        break
            
            if not period_columns:
                # If no period columns found, assume first data column is most recent period
                if len(header) > 1:
                    period_columns[1] = periods[0] if periods else "latest"
            
            logger.debug(f"Table {table_idx + 1}: Found {len(period_columns)} period columns: {period_columns}")
            
            # Process data rows
            for row_idx in range(header_row_idx + 1, len(rows)):
                row = rows[row_idx]
                if not row or len(row) == 0:
                    continue
                
                # Get row label (first column)
                row_label = str(row[0]).strip().lower() if len(row) > 0 else ""
                if not row_label:
                    continue
                
                # Determine statement type and field
                field_name = None
                statement_type = None
                
                # Check income statement fields
                for field, aliases in income_fields.items():
                    if any(alias in row_label for alias in aliases):
                        field_name = field.title()
                        statement_type = 'income_statement'
                        break
                
                # Check balance sheet fields
                if not statement_type:
                    for field, aliases in balance_fields.items():
                        if any(alias in row_label for alias in aliases):
                            field_name = field.title()
                            statement_type = 'balance_sheet'
                            break
                
                # Check cash flow fields
                if not statement_type:
                    for field, aliases in cashflow_fields.items():
                        if any(alias in row_label for alias in aliases):
                            field_name = field.title()
                            statement_type = 'cashflow'
                            break
                
                if not statement_type or not field_name:
                    continue
                
                # Extract values for each period column
                for col_idx, period in period_columns.items():
                    if col_idx < len(row):
                        cell_value = str(row[col_idx]).strip()
                        # Parse numeric value (remove currency symbols, commas, parentheses)
                        numeric_value = self._parse_numeric_value(cell_value)
                        
                        if numeric_value is not None:
                            if period not in result[statement_type]:
                                result[statement_type][period] = {}
                            result[statement_type][period][field_name] = numeric_value
                            logger.debug(f"Extracted {statement_type}[{period}][{field_name}] = {numeric_value}")
        
        # Also search text for key metrics
        shares_match = re.search(r'shares?\s+outstanding[:\s]+([\d,]+)', text, re.IGNORECASE)
        if shares_match:
            shares = self._parse_numeric_value(shares_match.group(1))
            if shares:
                result['key_metrics']['Shares Outstanding'] = shares
        
        return result
    
    def _parse_numeric_value(self, value_str: str) -> Optional[float]:
        """Parse a numeric value from a string, handling currency symbols, commas, and parentheses"""
        import re
        if not value_str:
            return None
        
        # Remove currency symbols and common prefixes
        value_str = re.sub(r'[$€£¥]', '', value_str)
        
        # Handle parentheses (negative values)
        is_negative = '(' in value_str or value_str.strip().startswith('-')
        value_str = re.sub(r'[()]', '', value_str)
        
        # Remove commas and other non-numeric characters except decimal point and minus
        value_str = re.sub(r'[^\d.\-]', '', value_str)
        
        try:
            value = float(value_str)
            return -value if is_negative else value
        except (ValueError, TypeError):
            return None

    
    def _extract_financial_data_from_ocr_text(self, text: str, ticker: str) -> Dict[str, Any]:
        """
        Extract financial data from OCR text using pattern matching
        This method looks for financial statement patterns in the OCR-extracted text
        """
        import re
        from datetime import datetime
        
        result = {
            "income_statement": {},
            "balance_sheet": {},
            "cashflow": {},
            "key_metrics": {}
        }
        
        logger.info(f"Extracting financial data from {len(text)} characters of OCR text for {ticker}")
        
        # Financial field patterns (more flexible for OCR text)
        income_patterns = {
            'Total Revenue': [
                r'(?:net\s+operating\s+revenues?|total\s+revenues?|net\s+sales|revenues?|sales)\s*[\$]?\s*([\d,]+(?:\.\d+)?)',
                r'revenues?\s*[\$]?\s*([\d,]+(?:\.\d+)?)'
            ],
            'Net Income': [
                r'(?:net\s+income|net\s+earnings|consolidated\s+net\s+income)\s*[\$]?\s*([\d,]+(?:\.\d+)?)',
                r'net\s+income.*?[\$]?\s*([\d,]+(?:\.\d+)?)'
            ],
            'Operating Income': [
                r'operating\s+income\s*[\$]?\s*([\d,]+(?:\.\d+)?)',
                r'income\s+from\s+operations\s*[\$]?\s*([\d,]+(?:\.\d+)?)'
            ],
            'Gross Profit': [
                r'gross\s+profit\s*[\$]?\s*([\d,]+(?:\.\d+)?)'
            ]
        }
        
        balance_patterns = {
            'Total Assets': [
                r'total\s+assets\s*[\$]?\s*([\d,]+(?:\.\d+)?)'
            ],
            'Total Stockholder Equity': [
                r'(?:total\s+)?(?:stockholders?|shareholders?)\s+equity\s*[\$]?\s*([\d,]+(?:\.\d+)?)',
                r'equity\s*[\$]?\s*([\d,]+(?:\.\d+)?)'
            ]
        }
        
        # Extract years from text
        years = re.findall(r'\b(20\d{2})\b', text)
        unique_years = sorted(list(set(years)), reverse=True)[:5]  # Get up to 5 most recent years
        
        if unique_years:
            logger.info(f"Found years in OCR text: {unique_years}")
        else:
            # Default to current year if no years found
            current_year = datetime.now().year
            unique_years = [str(current_year)]
            logger.warning(f"No years found in OCR text, using current year: {current_year}")
        
        # Look for financial data patterns
        text_lower = text.lower()
        
        # Extract income statement data
        for field_name, patterns in income_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
                if matches:
                    # Use the most recent year as the period
                    period = f"{unique_years[0]}-12-31" if unique_years else "latest"
                    if period not in result['income_statement']:
                        result['income_statement'][period] = {}
                    
                    # Parse the first numeric match
                    value = self._parse_numeric_value(matches[0])
                    if value is not None:
                        result['income_statement'][period][field_name] = value
                        logger.info(f"Extracted {field_name}: ${value:,.0f} for {period}")
                    break
        
        # Extract balance sheet data
        for field_name, patterns in balance_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
                if matches:
                    period = f"{unique_years[0]}-12-31" if unique_years else "latest"
                    if period not in result['balance_sheet']:
                        result['balance_sheet'][period] = {}
                    
                    value = self._parse_numeric_value(matches[0])
                    if value is not None:
                        result['balance_sheet'][period][field_name] = value
                        logger.info(f"Extracted {field_name}: ${value:,.0f} for {period}")
                    break
        
        # Look for shares outstanding
        shares_patterns = [
            r'shares?\s+outstanding[:\s]*([\d,]+(?:\.\d+)?)',
            r'weighted\s+average\s+shares?\s+outstanding[:\s]*([\d,]+(?:\.\d+)?)'
        ]
        
        for pattern in shares_patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                shares = self._parse_numeric_value(matches[0])
                if shares is not None:
                    result['key_metrics']['Shares Outstanding'] = shares
                    logger.info(f"Extracted Shares Outstanding: {shares:,.0f}")
                break
        
        # Summary
        total_periods = (
            len(result['income_statement']) + 
            len(result['balance_sheet']) + 
            len(result['cashflow']) +
            (1 if result['key_metrics'] else 0)
        )
        
        logger.info(f"OCR extraction summary for {ticker}: {total_periods} total data points extracted")
        logger.info(f"  Income statement: {len(result['income_statement'])} periods")
        logger.info(f"  Balance sheet: {len(result['balance_sheet'])} periods") 
        logger.info(f"  Cash flow: {len(result['cashflow'])} periods")
        logger.info(f"  Key metrics: {len(result['key_metrics'])} items")
        
        return result