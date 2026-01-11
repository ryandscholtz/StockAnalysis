"""
AI-powered PDF processor for financial statement extraction
Uses AWS Textract for text extraction and Claude/OpenAI for intelligent parsing
"""

import json
import logging
import boto3
import time
import re
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)

class AIPDFProcessor:
    """
    AI-powered PDF processor that extracts financial data from annual reports
    """
    
    def __init__(self):
        self.textract = boto3.client('textract')
        self.bedrock = None
        
        # Try to initialize Bedrock for Claude
        try:
            self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
            logger.info("Bedrock client initialized for Claude AI")
        except Exception as e:
            logger.warning(f"Bedrock not available: {e}")
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF using AWS Textract with PDF-to-image fallback"""
        try:
            # First attempt: Direct PDF processing with Textract
            response = self.textract.analyze_document(
                Document={'Bytes': pdf_bytes},
                FeatureTypes=['TABLES', 'FORMS']
            )
            
            # Extract text from all blocks
            text_blocks = []
            for block in response.get('Blocks', []):
                if block['BlockType'] == 'LINE':
                    text_blocks.append(block.get('Text', ''))
            
            extracted_text = '\n'.join(text_blocks)
            logger.info(f"Extracted {len(extracted_text)} characters from PDF using direct Textract")
            return extracted_text
            
        except Exception as e:
            if 'UnsupportedDocumentException' in str(e):
                logger.warning(f"Direct Textract failed with unsupported format, trying PDF-to-image fallback: {e}")
                return self._extract_text_via_images(pdf_bytes)
            else:
                logger.error(f"Textract extraction failed: {e}")
                return ""
    
    def _extract_text_via_images(self, pdf_bytes: bytes) -> str:
        """
        Fallback method: Convert PDF to images and use Textract on images
        This handles PDFs that Textract can't process directly
        """
        try:
            import fitz  # PyMuPDF
            import io
            from PIL import Image
            
            logger.info("Converting PDF to images for Textract processing")
            
            # Open PDF with PyMuPDF
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            all_text = []
            
            # Process each page (limit to first 20 pages to avoid Lambda timeout)
            max_pages = min(20, len(pdf_document))
            logger.info(f"Processing {max_pages} pages via image conversion")
            
            for page_num in range(max_pages):
                try:
                    # Get page
                    page = pdf_document[page_num]
                    
                    # Convert page to image (300 DPI for good OCR quality)
                    mat = fitz.Matrix(300/72, 300/72)  # 300 DPI scaling
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Convert to PIL Image
                    img_data = pix.tobytes("png")
                    
                    # Use Textract on the image
                    response = self.textract.analyze_document(
                        Document={'Bytes': img_data},
                        FeatureTypes=['TABLES', 'FORMS']
                    )
                    
                    # Extract text from this page
                    page_text = []
                    for block in response.get('Blocks', []):
                        if block['BlockType'] == 'LINE':
                            page_text.append(block.get('Text', ''))
                    
                    if page_text:
                        all_text.append(f"--- Page {page_num + 1} ---")
                        all_text.extend(page_text)
                        all_text.append("")  # Empty line between pages
                    
                    logger.info(f"Processed page {page_num + 1}/{max_pages} via image conversion")
                    
                except Exception as page_error:
                    logger.warning(f"Failed to process page {page_num + 1}: {page_error}")
                    continue
            
            pdf_document.close()
            
            extracted_text = '\n'.join(all_text)
            logger.info(f"Extracted {len(extracted_text)} characters via PDF-to-image conversion")
            return extracted_text
            
        except ImportError as e:
            logger.error(f"PDF-to-image conversion requires PyMuPDF and PIL: {e}")
            return ""
        except Exception as e:
            logger.error(f"PDF-to-image conversion failed: {e}")
            return ""
    
    def parse_financial_data_with_ai(self, text: str, ticker: str) -> Dict[str, Any]:
        """Use AI to parse extracted text into structured financial data"""
        
        # Define the target structure based on manual data entry fields
        target_structure = {
            "income_statement": {
                "fields": ["revenue", "gross_profit", "operating_income", "earnings_before_tax", 
                          "net_income", "earnings_per_share", "diluted_eps"],
                "periods": ["2023-12-31", "2022-12-31", "2021-12-31"]
            },
            "balance_sheet": {
                "fields": ["total_assets", "current_assets", "cash_and_equivalents", 
                          "total_liabilities", "current_liabilities", "long_term_debt",
                          "shareholders_equity", "retained_earnings"],
                "periods": ["2023-12-31", "2022-12-31", "2021-12-31"]
            },
            "cashflow": {
                "fields": ["operating_cash_flow", "investing_cash_flow", "financing_cash_flow",
                          "free_cash_flow", "capital_expenditures", "dividends_paid"],
                "periods": ["2023-12-31", "2022-12-31", "2021-12-31"]
            },
            "key_metrics": {
                "fields": ["shares_outstanding", "market_cap", "pe_ratio", "pb_ratio",
                          "debt_to_equity", "current_ratio", "roe", "roa", "book_value_per_share"],
                "periods": ["latest"]
            }
        }
        
        if self.bedrock:
            return self._parse_with_claude(text, ticker, target_structure)
        else:
            return self._parse_with_patterns(text, ticker, target_structure)
    
    def _parse_with_claude(self, text: str, ticker: str, target_structure: Dict) -> Dict[str, Any]:
        """Use Claude AI to parse financial data"""
        try:
            # Truncate text if too long (Claude has context limits)
            max_chars = 100000  # ~100k characters
            if len(text) > max_chars:
                # Try to find financial statement sections
                sections = self._find_financial_sections(text)
                if sections:
                    text = sections
                else:
                    text = text[:max_chars]
            
            prompt = f"""
You are a financial analyst expert at extracting data from annual reports. 
Extract ONLY the financial data that is explicitly present in the provided text below.

CRITICAL RULES:
1. ONLY extract numerical values that are explicitly stated in the text
2. DO NOT use your knowledge about {ticker} to fill in missing data
3. DO NOT generate or estimate any values not found in the text
4. If a financial metric is not explicitly mentioned with a number, DO NOT include it
5. If no financial data is found in the text, return empty objects for all sections
6. Convert monetary values to numbers (remove commas, dollar signs)
7. Use YYYY-MM-DD format for periods (typically 12-31 for year-end)

Target structure (only populate if data is found in text):
{json.dumps(target_structure, indent=2)}

Text to analyze:
{text}

If the text contains actual financial statements with numbers, extract them. 
If the text only contains titles, headers, or no numerical financial data, return empty objects.

Return only valid JSON with the extracted financial data (empty if no data found):
"""

            # Call Claude via Bedrock
            response = self.bedrock.invoke_model(
                modelId='anthropic.claude-3-sonnet-20240229-v1:0',
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 4000,
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ]
                })
            )
            
            response_body = json.loads(response['body'].read())
            ai_response = response_body['content'][0]['text']
            
            # Extract JSON from AI response
            try:
                # Find JSON in the response
                json_start = ai_response.find('{')
                json_end = ai_response.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = ai_response[json_start:json_end]
                    parsed_data = json.loads(json_str)
                    
                    logger.info(f"Claude successfully parsed financial data for {ticker}")
                    return parsed_data
                else:
                    logger.warning("No valid JSON found in Claude response")
                    return self._parse_with_patterns(text, ticker, target_structure)
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse Claude JSON response: {e}")
                return self._parse_with_patterns(text, ticker, target_structure)
                
        except Exception as e:
            logger.error(f"Claude AI parsing failed: {e}")
            return self._parse_with_patterns(text, ticker, target_structure)
    
    def _parse_with_patterns(self, text: str, ticker: str, target_structure: Dict) -> Dict[str, Any]:
        """Fallback pattern-based parsing when AI is not available"""
        
        structured_data = {
            "income_statement": {},
            "balance_sheet": {},
            "cashflow": {},
            "key_metrics": {}
        }
        
        # Basic pattern matching for common financial terms
        text_lower = text.lower()
        
        # Look for revenue figures (in millions or billions)
        revenue_patterns = [
            r'total revenue[:\s]+\$?([0-9,]+(?:\.[0-9]+)?)\s*(?:million|billion)?',
            r'net revenue[:\s]+\$?([0-9,]+(?:\.[0-9]+)?)\s*(?:million|billion)?',
            r'revenue[:\s]+\$?([0-9,]+(?:\.[0-9]+)?)\s*(?:million|billion)?'
        ]
        
        # Look for net income
        income_patterns = [
            r'net income[:\s]+\$?([0-9,]+(?:\.[0-9]+)?)\s*(?:million|billion)?',
            r'net earnings[:\s]+\$?([0-9,]+(?:\.[0-9]+)?)\s*(?:million|billion)?'
        ]
        
        # Extract basic financial data if patterns match
        current_year = "2023-12-31"  # Default to most recent year
        
        for pattern in revenue_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    value = float(match.group(1).replace(',', ''))
                    # Assume values are in millions if under 1000, billions if over
                    if value < 1000:
                        value *= 1000000  # Convert millions to actual value
                    else:
                        value *= 1000000000  # Convert billions to actual value
                    
                    if current_year not in structured_data["income_statement"]:
                        structured_data["income_statement"][current_year] = {}
                    structured_data["income_statement"][current_year]["revenue"] = value
                    break
                except ValueError:
                    continue
        
        for pattern in income_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    value = float(match.group(1).replace(',', ''))
                    if value < 1000:
                        value *= 1000000
                    else:
                        value *= 1000000000
                    
                    if current_year not in structured_data["income_statement"]:
                        structured_data["income_statement"][current_year] = {}
                    structured_data["income_statement"][current_year]["net_income"] = value
                    break
                except ValueError:
                    continue
        
        logger.info(f"Pattern-based parsing completed for {ticker}")
        return structured_data
    
    def _find_financial_sections(self, text: str) -> str:
        """Find and extract financial statement sections from the full text"""
        
        # Look for common financial statement headers
        section_markers = [
            'consolidated statements of operations',
            'consolidated statements of income',
            'consolidated balance sheets',
            'consolidated statements of cash flows',
            'consolidated statements of financial position',
            'income statement',
            'balance sheet',
            'cash flow statement',
            'statement of operations',
            'statement of financial position'
        ]
        
        text_lower = text.lower()
        sections = []
        
        for marker in section_markers:
            start_pos = text_lower.find(marker)
            if start_pos >= 0:
                # Extract a reasonable chunk around the financial statement
                section_start = max(0, start_pos - 1000)
                section_end = min(len(text), start_pos + 10000)
                sections.append(text[section_start:section_end])
        
        if sections:
            return '\n\n'.join(sections)
        else:
            # If no specific sections found, return first portion of text
            return text[:50000]
    
    def process_pdf(self, pdf_bytes: bytes, ticker: str) -> Tuple[Dict[str, Any], str]:
        """
        Main processing function that extracts and parses PDF financial data
        """
        try:
            # Step 1: Extract text using Textract
            logger.info(f"Starting PDF processing for {ticker}")
            extracted_text = self.extract_text_from_pdf(pdf_bytes)
            
            if not extracted_text:
                # Create structure with appropriate metadata for empty text
                structured_data = {
                    "income_statement": {},
                    "balance_sheet": {},
                    "cashflow": {},
                    "key_metrics": {},
                    "extraction_metadata": {
                        "ticker": ticker,
                        "extracted_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        "extraction_method": "text_extraction_empty",
                        "text_length": 0,
                        "ai_model": "claude-3-sonnet" if self.bedrock else "pattern_matching",
                        "note": "PDF processed successfully but no text was extracted - may be image-only or encrypted PDF"
                    }
                }
                return structured_data, "PDF processed but no text extracted - manual data entry recommended"
            
            # Step 2: Parse financial data with AI
            logger.info(f"Parsing financial data with AI for {ticker}")
            structured_data = self.parse_financial_data_with_ai(extracted_text, ticker)
            
            # Step 3: Add metadata
            structured_data["extraction_metadata"] = {
                "ticker": ticker,
                "extracted_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                "extraction_method": "ai_powered_textract",
                "text_length": len(extracted_text),
                "ai_model": "claude-3-sonnet" if self.bedrock else "pattern_matching",
                "note": "Financial data extracted using AI - review for accuracy"
            }
            
            # Count extracted periods
            total_periods = 0
            for section in ['income_statement', 'balance_sheet', 'cashflow']:
                if section in structured_data:
                    total_periods += len(structured_data[section])
            
            summary = f"AI extraction completed: {len(extracted_text)} chars processed, {total_periods} periods extracted"
            
            logger.info(f"PDF processing completed for {ticker}: {total_periods} periods extracted")
            return structured_data, summary
            
        except Exception as e:
            logger.error(f"PDF processing failed for {ticker}: {e}")
            return self._create_empty_structure(ticker), f"PDF processing failed: {str(e)}"
    
    def _create_empty_structure(self, ticker: str) -> Dict[str, Any]:
        """Create empty structure when processing fails due to exceptions"""
        return {
            "income_statement": {},
            "balance_sheet": {},
            "cashflow": {},
            "key_metrics": {},
            "extraction_metadata": {
                "ticker": ticker,
                "extracted_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                "extraction_method": "processing_exception",
                "note": "PDF processing encountered an exception - manual data entry required"
            }
        }