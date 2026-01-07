"""
Yahoo Finance Web Scraper
Scrapes financial data from Yahoo Finance HTML pages when API data is incomplete
"""
import requests
from bs4 import BeautifulSoup
import re
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class YahooFinanceScraper:
    """Scrape financial data from Yahoo Finance web pages"""

    def __init__(self):
        self.base_url = "https://finance.yahoo.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }

    def _normalize_ticker(self, ticker: str) -> str:
        """Normalize ticker for Yahoo Finance URL"""
        # BRK.B -> BRK-B, BRK-B -> BRK-B
        return ticker.replace('.', '-')

    def _extract_json_data(self, html_content: str) -> Optional[Dict]:
        """Extract JSON data embedded in Yahoo Finance HTML"""
        try:
            # Yahoo Finance embeds data in script tags with specific patterns
            # Pattern 1: root.App.main = {...}
            pattern1 = r'root\.App\.main\s*=\s*({.+?});'
            match = re.search(pattern1, html_content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

            # Pattern 2: window.__PRELOADED_STATE__ = {...}
            pattern2 = r'window\.__PRELOADED_STATE__\s*=\s*({.+?});'
            match = re.search(pattern2, html_content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

            # Pattern 3: Look for data-react-helmet or similar
            # This is a more general approach
            pattern3 = r'"QuoteSummaryStore":\s*({.+?}),\s*"'
            match = re.search(pattern3, html_content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

            return None
        except Exception as e:
            logger.debug(f"Error extracting JSON data: {e}")
            return None

    def _parse_financial_table(self, soup: BeautifulSoup, table_type: str) -> Dict[str, Dict[str, float]]:
        """Parse financial data from HTML tables"""
        result = {}

        try:
            # Yahoo Finance uses specific data attributes
            # Look for the main financial table
            table = soup.find('div', {'data-test': 'fin-row'})
            if not table:
                # Try alternative selectors
                table = soup.find('table', class_=re.compile(r'financials|data'))

            if not table:
                logger.warning(f"Could not find financial table for {table_type}")
                return result

            # Find all rows
            rows = table.find_all('div', {'data-test': 'fin-row'}) or table.find_all('tr')

            for row in rows:
                # Extract row label (e.g., "Total Revenue")
                label_elem = row.find('span', {'data-test': 'fin-col-label'}) or row.find('td', class_=re.compile(r'label|name'))
                if not label_elem:
                    continue

                label = label_elem.get_text(strip=True)
                if not label:
                    continue

                # Extract values for different periods
                value_cells = row.find_all('span', {'data-test': re.compile(r'fin-col')}) or row.find_all('td', class_=re.compile(r'value|data'))

                period_values = {}
                for i, cell in enumerate(value_cells):
                    if i == 0:  # Skip label column
                        continue

                    value_text = cell.get_text(strip=True)
                    if value_text and value_text != '-':
                        # Remove commas and parse
                        try:
                            # Handle negative values in parentheses
                            if '(' in value_text and ')' in value_text:
                                value_text = '-' + value_text.replace('(', '').replace(')', '')

                            value = float(value_text.replace(',', '').replace('(', '-').replace(')', ''))
                            # Use index as period identifier (we'll need to map to actual dates)
                            period_key = f"period_{i}"
                            period_values[period_key] = value
                        except ValueError:
                            continue

                if period_values:
                    result[label] = period_values

            return result

        except Exception as e:
            logger.error(f"Error parsing financial table: {e}")
            return result

    def fetch_income_statement(self, ticker: str) -> Dict[str, Dict[str, float]]:
        """Fetch income statement from Yahoo Finance web page"""
        try:
            url_ticker = self._normalize_ticker(ticker)
            url = f"{self.base_url}/quote/{url_ticker}/financials"

            logger.info(f"Fetching income statement from: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)

            if response.status_code != 200:
                logger.warning(f"Yahoo Finance returned status {response.status_code} for {ticker}")
                return {}

            soup = BeautifulSoup(response.content, 'html.parser')

            # Try to extract JSON data first
            json_data = self._extract_json_data(response.text)
            if json_data:
                # Navigate through the JSON structure to find income statement
                # This structure varies, so we'll need to explore it
                logger.info("Found JSON data structure, attempting to parse...")
                # TODO: Parse JSON structure for income statement

            # Fallback to HTML table parsing
            income_data = self._parse_financial_table(soup, 'income_statement')

            if income_data:
                logger.info(f"Successfully scraped {len(income_data)} income statement line items")

            return income_data

        except Exception as e:
            logger.error(f"Error fetching income statement from Yahoo Finance web: {e}")
            return {}

    def fetch_balance_sheet(self, ticker: str) -> Dict[str, Dict[str, float]]:
        """Fetch balance sheet from Yahoo Finance web page"""
        try:
            url_ticker = self._normalize_ticker(ticker)
            url = f"{self.base_url}/quote/{url_ticker}/balance-sheet"

            logger.info(f"Fetching balance sheet from: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)

            if response.status_code != 200:
                logger.warning(f"Yahoo Finance returned status {response.status_code} for {ticker}")
                return {}

            soup = BeautifulSoup(response.content, 'html.parser')
            balance_data = self._parse_financial_table(soup, 'balance_sheet')

            if balance_data:
                logger.info(f"Successfully scraped {len(balance_data)} balance sheet line items")

            return balance_data

        except Exception as e:
            logger.error(f"Error fetching balance sheet from Yahoo Finance web: {e}")
            return {}

    def fetch_cashflow(self, ticker: str) -> Dict[str, Dict[str, float]]:
        """Fetch cash flow statement from Yahoo Finance web page"""
        try:
            url_ticker = self._normalize_ticker(ticker)
            url = f"{self.base_url}/quote/{url_ticker}/cash-flow"

            logger.info(f"Fetching cash flow from: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)

            if response.status_code != 200:
                logger.warning(f"Yahoo Finance returned status {response.status_code} for {ticker}")
                return {}

            soup = BeautifulSoup(response.content, 'html.parser')
            cashflow_data = self._parse_financial_table(soup, 'cashflow')

            if cashflow_data:
                logger.info(f"Successfully scraped {len(cashflow_data)} cash flow line items")

            return cashflow_data

        except Exception as e:
            logger.error(f"Error fetching cash flow from Yahoo Finance web: {e}")
            return {}

    def convert_to_standard_format(self, scraped_data: Dict[str, Dict[str, float]],
                                   statement_type: str) -> Dict[str, Dict[str, float]]:
        """
        Convert scraped data to our standard format: {date: {line_item: value}}
        """
        # Map Yahoo Finance labels to our standard labels
        label_mapping = {
            'income_statement': {
                'Total Revenue': ['Total Revenue', 'Revenue', 'Net Revenue'],
                'Net Income': ['Net Income', 'Net Income Common Stockholders'],
                'Operating Income': ['Operating Income', 'Income from Operations'],
                'EBIT': ['EBIT', 'Earnings Before Interest and Taxes'],
                'Income Before Tax': ['Income Before Tax', 'Pretax Income'],
            },
            'balance_sheet': {
                'Total Assets': ['Total Assets'],
                'Total Liabilities': ['Total Liabilities'],
                'Total Stockholder Equity': ['Total Stockholder Equity', 'Stockholders Equity'],
                'Cash And Cash Equivalents': ['Cash And Cash Equivalents', 'Cash'],
            },
            'cashflow': {
                'Operating Cash Flow': ['Operating Cash Flow', 'Cash from Operating Activities'],
                'Capital Expenditures': ['Capital Expenditures', 'Capital Expenditure'],
            }
        }

        mapping = label_mapping.get(statement_type, {})
        result = {}

        # Group by period (we'll need to map period indices to actual dates)
        # For now, create a simple structure
        for label, period_values in scraped_data.items():
            # Find matching standard label
            standard_label = None
            for std_label, variations in mapping.items():
                if any(var.lower() in label.lower() for var in variations):
                    standard_label = std_label
                    break

            if not standard_label:
                # Use original label if no mapping found
                standard_label = label

            # Add to result for each period
            for period_key, value in period_values.items():
                if period_key not in result:
                    result[period_key] = {}
                result[period_key][standard_label] = value

        return result
