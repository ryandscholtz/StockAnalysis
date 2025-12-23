"""
PDF extraction service using LLM to extract financial data
"""
import os
import logging
from typing import Dict, List, Optional, Any
import PyPDF2
import pdfplumber
import io

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract text from PDF files"""
    
    def __init__(self):
        self.llm_provider = os.getenv("LLM_PROVIDER", "openai")  # "openai" or "anthropic"
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text content from PDF bytes"""
        try:
            # Try pdfplumber first (better for tables)
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                text_parts = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                    # Also try to extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            table_text = "\n".join(["\t".join([str(cell) if cell else "" for cell in row]) for row in table])
                            text_parts.append(f"\n[Table]\n{table_text}\n")
                return "\n\n".join(text_parts)
        except Exception as e:
            logger.warning(f"pdfplumber failed, trying PyPDF2: {e}")
            try:
                # Fallback to PyPDF2
                pdf_file = io.BytesIO(pdf_bytes)
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text_parts = []
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
                return "\n\n".join(text_parts)
            except Exception as e2:
                logger.error(f"Both PDF extraction methods failed: {e2}")
                raise Exception(f"Failed to extract text from PDF: {e2}")
    
    def extract_financial_data_with_llm(self, pdf_text: str, ticker: str) -> Dict[str, Any]:
        """
        Use LLM to extract financial data from PDF text
        Returns structured financial data
        """
        if not pdf_text or len(pdf_text.strip()) < 100:
            raise ValueError("PDF text is too short or empty")
        
        # Truncate text if too long (LLM context limits)
        max_chars = 100000  # ~100k chars for most LLMs
        if len(pdf_text) > max_chars:
            logger.warning(f"PDF text too long ({len(pdf_text)} chars), truncating to {max_chars}")
            pdf_text = pdf_text[:max_chars] + "\n\n[... content truncated ...]"
        
        prompt = self._create_extraction_prompt(pdf_text, ticker)
        
        try:
            if self.llm_provider == "anthropic" and self.anthropic_api_key:
                return self._extract_with_anthropic(prompt)
            elif self.openai_api_key:
                return self._extract_with_openai(prompt)
            else:
                # Fallback to rule-based extraction if no API keys
                logger.warning("No LLM API keys found, using rule-based extraction")
                return self._extract_with_rules(pdf_text)
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}, falling back to rule-based")
            return self._extract_with_rules(pdf_text)
    
    def _create_extraction_prompt(self, pdf_text: str, ticker: str) -> str:
        """Create prompt for LLM to extract financial data"""
        return f"""You are a financial data extraction expert. Extract financial statement data from the following PDF text for ticker {ticker}.

Extract the following information and return it as a JSON object:

1. Income Statement data (for the most recent periods available):
   - Total Revenue
   - Net Income
   - Operating Income
   - EBIT (Earnings Before Interest and Taxes)
   - Income Before Tax

2. Balance Sheet data (for the most recent periods available):
   - Total Assets
   - Total Liabilities
   - Total Stockholder Equity
   - Cash And Cash Equivalents
   - Total Debt

3. Cash Flow Statement data (for the most recent periods available):
   - Operating Cash Flow
   - Capital Expenditures
   - Free Cash Flow
   - Cash From Financing Activities

4. Key Metrics:
   - Shares Outstanding
   - Market Cap (if available)

For each financial statement, extract data for multiple periods if available (e.g., 2024, 2023, 2022). Use dates as keys in the format "YYYY-MM-DD" or "YYYY-12-31".

Return ONLY valid JSON in this format:
{{
  "income_statement": {{
    "2024-12-31": {{
      "Total Revenue": 1000000,
      "Net Income": 100000,
      ...
    }},
    "2023-12-31": {{
      ...
    }}
  }},
  "balance_sheet": {{
    "2024-12-31": {{
      "Total Assets": 5000000,
      ...
    }}
  }},
  "cashflow": {{
    "2024-12-31": {{
      "Operating Cash Flow": 200000,
      ...
    }}
  }},
  "key_metrics": {{
    "Shares Outstanding": 1000000,
    "Market Cap": 50000000
  }}
}}

PDF Text:
{pdf_text[:50000]}
"""
    
    def _extract_with_openai(self, prompt: str) -> Dict[str, Any]:
        """Extract using OpenAI API"""
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
                max_tokens=4000
            )
            
            content = response.choices[0].message.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            import json
            return json.loads(content)
        except Exception as e:
            logger.error(f"OpenAI extraction failed: {e}")
            raise
    
    def _extract_with_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Extract using Anthropic API"""
        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=self.anthropic_api_key)
            
            response = client.messages.create(
                model="claude-3-haiku-20240307",  # Use cheaper model
                max_tokens=4000,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.content[0].text.strip()
            # Remove markdown code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            import json
            return json.loads(content)
        except Exception as e:
            logger.error(f"Anthropic extraction failed: {e}")
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

