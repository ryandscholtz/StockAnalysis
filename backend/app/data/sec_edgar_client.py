"""
SEC EDGAR API client for official financial filings
"""
import requests
import re
import os
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET


class SECEdgarClient:
    """Client for SEC EDGAR database (free, no API key required)"""
    
    def __init__(self):
        self.base_url = "https://data.sec.gov"
        self.user_agent = "StockAnalysisTool/1.0 (contact@example.com)"  # SEC requires user agent
    
    def get_cik_from_ticker(self, ticker: str) -> Optional[str]:
        """Get CIK (Central Index Key) from ticker symbol"""
        try:
            # SEC company tickers JSON
            url = "https://www.sec.gov/files/company_tickers.json"
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                ticker_upper = ticker.upper()
                for entry in data.values():
                    if entry.get('ticker', '').upper() == ticker_upper:
                        cik = str(entry.get('cik_str', ''))
                        # Pad CIK to 10 digits
                        return cik.zfill(10)
            return None
        except Exception as e:
            print(f"Error getting CIK for {ticker}: {e}")
            return None
    
    def get_company_filings(self, cik: str, form_type: str = "10-K", count: int = 5) -> List[Dict]:
        """Get recent filings for a company"""
        try:
            url = f"{self.base_url}/submissions/CIK{cik}.json"
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                filings = []
                
                recent_filings = data.get('filings', {}).get('recent', {})
                forms = recent_filings.get('form', [])
                filing_dates = recent_filings.get('filingDate', [])
                accession_numbers = recent_filings.get('accessionNumber', [])
                
                for i, form in enumerate(forms):
                    if form == form_type and len(filings) < count:
                        if i < len(filing_dates) and i < len(accession_numbers):
                            filings.append({
                                'form': form,
                                'date': filing_dates[i],
                                'accessionNumber': accession_numbers[i]
                            })
                
                return filings
            return []
        except Exception as e:
            print(f"Error getting filings: {e}")
            return []
    
    def get_financial_data_from_filing(self, cik: str, accession_number: str) -> Optional[Dict]:
        """
        Extract financial data from SEC filing
        This is a simplified version - full XBRL parsing would be more complex
        """
        try:
            # Convert accession number format (e.g., 0000320193-21-000077 -> 0000320193-21-000077)
            acc_no_dashes = accession_number.replace('-', '')
            url = f"{self.base_url}/files/{acc_no_dashes}/{accession_number}.txt"
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # This is a simplified extraction - real implementation would parse XBRL
                # For now, we'll return that we found the filing
                return {
                    'filing_found': True,
                    'accession_number': accession_number,
                    'note': 'Full XBRL parsing not implemented - using yfinance data'
                }
            return None
        except Exception as e:
            print(f"Error getting filing data: {e}")
            return None


class AlphaVantageClient:
    """Client for Alpha Vantage API (free tier available)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        self.base_url = "https://www.alphavantage.co/query"
    
    def get_income_statement(self, symbol: str) -> Optional[Dict]:
        """Get annual income statements"""
        if not self.api_key:
            return None
        
        try:
            params = {
                'function': 'INCOME_STATEMENT',
                'symbol': symbol,
                'apikey': self.api_key
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'annualReports' in data:
                    return data
            return None
        except Exception as e:
            print(f"Error getting Alpha Vantage income statement: {e}")
            return None
    
    def get_balance_sheet(self, symbol: str) -> Optional[Dict]:
        """Get annual balance sheets"""
        if not self.api_key:
            return None
        
        try:
            params = {
                'function': 'BALANCE_SHEET',
                'symbol': symbol,
                'apikey': self.api_key
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'annualReports' in data:
                    return data
            return None
        except Exception as e:
            print(f"Error getting Alpha Vantage balance sheet: {e}")
            return None
    
    def get_cash_flow(self, symbol: str) -> Optional[Dict]:
        """Get annual cash flow statements"""
        if not self.api_key:
            return None
        
        try:
            params = {
                'function': 'CASH_FLOW',
                'symbol': symbol,
                'apikey': self.api_key
            }
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'annualReports' in data:
                    return data
            return None
        except Exception as e:
            print(f"Error getting Alpha Vantage cash flow: {e}")
            return None

