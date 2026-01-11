"""
Simplified PDF Processing for Lambda Environment
Handles PDF text extraction and basic financial data structuring
"""
import os
import logging
import json
import time
from typing import Dict, List, Optional, Any, Tuple, Callable
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SimplePDFProcessor:
    """
    Simplified PDF processor for Lambda environment
    Features:
    - AWS Textract integration for text extraction
    - Basic financial data structuring
    - Progress tracking for large documents
    """

    def __init__(self):
        self.aws_region = os.getenv("AWS_REGION", "eu-west-1")
        
        # Initialize AWS clients
        try:
            self.textract = boto3.client('textract', region_name=self.aws_region)
            self.s3 = boto3.client('s3', region_name=self.aws_region)
            logger.info(f"SimplePDFProcessor initialized (region: {self.aws_region})")
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            raise

        # Processing limits
        self.MAX_SYNC_PAGES = 10  # Use sync Textract for small docs
        self.MAX_LAMBDA_SIZE = 50 * 1024 * 1024  # 50MB Lambda limit

    def process_pdf_sync(
        self, 
        pdf_bytes: bytes, 
        ticker: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Synchronous version of PDF processing for Lambda
        """
        try:
            # Step 1: Analyze PDF size
            pdf_size_mb = len(pdf_bytes) / (1024 * 1024)
            
            logger.info(f"Processing PDF for {ticker}: {pdf_size_mb:.1f} MB")
            
            if progress_callback:
                progress_callback(1, 8, f"Analyzing PDF: {pdf_size_mb:.1f} MB")
            
            # Step 2: Extract text using Textract
            if progress_callback:
                progress_callback(2, 8, "Extracting text with AWS Textract")
            
            # Use sync Textract for Lambda (simpler and faster)
            try:
                response = self.textract.analyze_document(
                    Document={'Bytes': pdf_bytes},
                    FeatureTypes=['TABLES', 'FORMS']
                )
                
                # Extract text and tables
                text = self._extract_text_from_response(response)
                tables = self._extract_tables_from_response(response)
                
                if progress_callback:
                    progress_callback(5, 8, f"Extracted {len(text)} chars, {len(tables)} tables")
                
            except Exception as e:
                logger.error(f"Textract failed: {e}")
                if progress_callback:
                    progress_callback(5, 8, f"Textract failed: {str(e)}")
                
                # Fallback to basic text extraction
                text = "PDF text extraction failed - manual data entry required"
                tables = []
            
            # Step 3: Structure data with basic pattern matching
            if progress_callback:
                progress_callback(6, 8, "Structuring financial data")
            
            structured_data = self._structure_data_basic(text, tables, ticker)
            
            if progress_callback:
                progress_callback(8, 8, "Processing complete")
            
            summary = f"PDF processed: {len(text)} chars extracted, {len(tables)} tables, basic structuring applied"
            return structured_data, summary
                
        except Exception as e:
            logger.error(f"Error processing PDF for {ticker}: {e}")
            if progress_callback:
                progress_callback(8, 8, f"Error: {str(e)}")
            raise

    async def process_pdf(
        self, 
        pdf_bytes: bytes, 
        ticker: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        Async wrapper for sync processing
        """
        return self.process_pdf_sync(pdf_bytes, ticker, progress_callback)

    def _extract_text_from_response(self, response: Dict) -> str:
        """Extract text from Textract response"""
        text_blocks = []
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'LINE':
                text_blocks.append(block.get('Text', ''))
        return '\n'.join(text_blocks)

    def _extract_tables_from_response(self, response: Dict) -> List[Dict]:
        """Extract tables from Textract response (basic implementation)"""
        tables = []
        
        # Group blocks by type
        blocks_by_id = {block['Id']: block for block in response.get('Blocks', [])}
        
        # Find table blocks
        for block in response.get('Blocks', []):
            if block['BlockType'] == 'TABLE':
                table_data = {
                    'id': block['Id'],
                    'rows': [],
                    'confidence': block.get('Confidence', 0)
                }
                
                # Extract table relationships (simplified)
                if 'Relationships' in block:
                    for relationship in block['Relationships']:
                        if relationship['Type'] == 'CHILD':
                            # This would contain cell IDs - simplified for now
                            pass
                
                tables.append(table_data)
        
        return tables

    def _structure_data_basic(self, text: str, tables: List[Dict], ticker: str) -> Dict[str, Any]:
        """
        Basic financial data structuring using pattern matching
        This is a simplified version - in production you'd use LLM for better extraction
        """
        
        # Initialize structure
        structured_data = {
            "income_statement": {},
            "balance_sheet": {},
            "cashflow": {},
            "key_metrics": {}
        }
        
        # Basic pattern matching for common financial terms
        text_lower = text.lower()
        
        # Look for revenue/sales figures
        revenue_patterns = [
            'total revenue', 'net revenue', 'total sales', 'net sales',
            'revenue from operations', 'operating revenue'
        ]
        
        # Look for earnings figures
        earnings_patterns = [
            'net income', 'net earnings', 'profit after tax',
            'earnings per share', 'diluted eps'
        ]
        
        # Extract basic metrics if found
        current_year = str(time.gmtime().tm_year)
        previous_year = str(time.gmtime().tm_year - 1)
        
        # This is a very basic implementation
        # In production, you'd use sophisticated NLP/LLM to extract actual values
        if any(pattern in text_lower for pattern in revenue_patterns):
            structured_data["income_statement"][current_year] = {
                "revenue": None,  # Would extract actual numbers
                "note": "Revenue data detected but requires manual extraction"
            }
        
        if any(pattern in text_lower for pattern in earnings_patterns):
            if current_year not in structured_data["income_statement"]:
                structured_data["income_statement"][current_year] = {}
            structured_data["income_statement"][current_year].update({
                "net_income": None,  # Would extract actual numbers
                "note": "Earnings data detected but requires manual extraction"
            })
        
        # Add metadata
        structured_data["extraction_metadata"] = {
            "ticker": ticker,
            "extracted_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            "text_length": len(text),
            "tables_found": len(tables),
            "extraction_method": "basic_pattern_matching",
            "note": "This is basic extraction - manual review and data entry recommended for accuracy"
        }
        
        logger.info(f"Basic structuring complete for {ticker}: {len(structured_data)} sections")
        return structured_data