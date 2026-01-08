"""
Financial Modeling Prep API Client
Free tier: 250 requests/day
Get API key at: https://financialmodelingprep.com/developer/docs/
"""
import requests
import logging
from typing import Dict, List, Optional, Any
import os

logger = logging.getLogger(__name__)


class FinancialModelingPrepClient:
    """Client for Financial Modeling Prep API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FMP_API_KEY")
        self.base_url = "https://financialmodelingprep.com/api/v3"

    def _make_request(self, endpoint: str) -> Optional[Dict]:
        """Make API request"""
        if not self.api_key:
            logger.debug("Financial Modeling Prep API key not set")
            return None

        try:
            url = f"{self.base_url}/{endpoint}?apikey={self.api_key}"
            response = requests.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                return data
            elif response.status_code == 429:
                logger.warning("Financial Modeling Prep rate limit exceeded")
                return None
            else:
                logger.warning(f"Financial Modeling Prep returned status {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error calling Financial Modeling Prep API: {e}")
            return None

    def get_income_statement(self, ticker: str, limit: int = 5) -> List[Dict]:
        """Get income statement"""
        endpoint = f"income-statement/{ticker}"
        data = self._make_request(endpoint)

        if data and isinstance(data, list):
            return data[:limit]
        return []

    def get_balance_sheet(self, ticker: str, limit: int = 5) -> List[Dict]:
        """Get balance sheet"""
        endpoint = f"balance-sheet-statement/{ticker}"
        data = self._make_request(endpoint)

        if data and isinstance(data, list):
            return data[:limit]
        return []

    def get_cashflow(self, ticker: str, limit: int = 5) -> List[Dict]:
        """Get cash flow statement"""
        endpoint = f"cash-flow-statement/{ticker}"
        data = self._make_request(endpoint)

        if data and isinstance(data, list):
            return data[:limit]
        return []

    def convert_income_statement(self, statements: List[Dict]) -> Dict[str, Dict[str, float]]:
        """Convert FMP format to our standard format"""
        result = {}

        for statement in statements:
            date = statement.get('date', '')
            if not date:
                continue

            result[date] = {
                'Total Revenue': statement.get('revenue', 0) or 0,
                'Net Income': statement.get('netIncome', 0) or 0,
                'Operating Income': statement.get('operatingIncome', 0) or 0,
                'EBIT': statement.get('ebit', 0) or statement.get('operatingIncome', 0) or 0,
                'Income Before Tax': statement.get('incomeBeforeTax', 0) or 0,
                'Tax Provision': abs(statement.get('incomeTaxExpense', 0) or 0),
                'Gross Profit': statement.get('grossProfit', 0) or 0,
                'Cost Of Revenue': statement.get('costOfRevenue', 0) or 0,
            }

        return result

    def convert_balance_sheet(self, statements: List[Dict]) -> Dict[str, Dict[str, float]]:
        """Convert FMP format to our standard format"""
        result = {}

        for statement in statements:
            date = statement.get('date', '')
            if not date:
                continue

            result[date] = {
                'Total Assets': statement.get('totalAssets', 0) or 0,
                'Total Current Assets': statement.get('totalCurrentAssets', 0) or 0,
                'Cash And Cash Equivalents': statement.get('cashAndCashEquivalents', 0) or 0,
                'Inventory': statement.get('inventory', 0) or 0,
                'Total Liabilities': statement.get('totalLiabilities', 0) or 0,
                'Total Current Liabilities': statement.get('totalCurrentLiabilities', 0) or 0,
                'Total Debt': statement.get('totalDebt', 0) or 0,
                'Long Term Debt': statement.get('longTermDebt', 0) or 0,
                'Total Stockholder Equity': statement.get('totalStockholdersEquity', 0) or 0,
            }

        return result

    def convert_cashflow(self, statements: List[Dict]) -> Dict[str, Dict[str, float]]:
        """Convert FMP format to our standard format"""
        result = {}

        for statement in statements:
            date = statement.get('date', '')
            if not date:
                continue

            operating_cf = statement.get('operatingCashFlow', 0) or 0
            capex = abs(statement.get('capitalExpenditure', 0) or 0)

            result[date] = {
                'Operating Cash Flow': operating_cf,
                'Total Cash From Operating Activities': operating_cf,
                'Capital Expenditures': capex,
                'Free Cash Flow': operating_cf - capex,
            }

        return result
