"""
AI Agent for fetching missing financial data
Uses intelligent search and data extraction to supplement incomplete financial statements
"""
import os
import logging
from typing import Dict, List, Optional, Any
import requests
from bs4 import BeautifulSoup
import re
from app.data.yahoo_finance_scraper import YahooFinanceScraper
from app.data.financial_modeling_prep_client import FinancialModelingPrepClient
from app.data.marketwatch_scraper import MarketWatchScraper

logger = logging.getLogger(__name__)


class FinancialDataAgent:
    """
    AI-powered agent that intelligently fetches missing financial data
    from multiple sources when primary data sources are incomplete
    """

    def __init__(self):
        self.sec_base_url = "https://www.sec.gov"
        self.user_agent = os.getenv("SEC_USER_AGENT", "Stock Analysis Tool (contact@example.com)")
        self.yahoo_scraper = YahooFinanceScraper()
        self.fmp_client = FinancialModelingPrepClient()
        self.marketwatch_scraper = MarketWatchScraper()

    def identify_missing_data(self, company_data: Any) -> Dict[str, List[str]]:
        """
        Identify what financial data is missing or incomplete
        Returns a dict with missing data categories and specific items
        """
        missing = {
            'income_statement': [],
            'balance_sheet': [],
            'cashflow': [],
            'key_metrics': []
        }

        # Check income statement
        if not company_data.income_statement or len(company_data.income_statement) < 3:
            missing['income_statement'].append('insufficient_periods')

        if company_data.income_statement:
            # Check for key line items
            sample_period = next(iter(company_data.income_statement.values()))
            if isinstance(sample_period, dict):
                required_items = ['Net Income', 'Total Revenue', 'Operating Income', 'EBIT']
                for item in required_items:
                    found = False
                    for key in sample_period.keys():
                        if item.lower() in str(key).lower():
                            found = True
                            break
                    if not found:
                        missing['income_statement'].append(item)

        # Check balance sheet
        if not company_data.balance_sheet or len(company_data.balance_sheet) < 3:
            missing['balance_sheet'].append('insufficient_periods')

        # Check cashflow
        if not company_data.cashflow or len(company_data.cashflow) < 3:
            missing['cashflow'].append('insufficient_periods')

        # Check key metrics - use is None to allow 0 values
        if company_data.shares_outstanding is None:
            missing['key_metrics'].append('shares_outstanding')
        if company_data.market_cap is None:
            # Only mark as missing if it can't be calculated from price * shares
            if not (company_data.current_price and company_data.shares_outstanding):
                missing['key_metrics'].append('market_cap')

        return missing

    def fetch_from_sec_edgar(self, ticker: str, cik: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch financial data from SEC EDGAR
        """
        try:
            # Get CIK if not provided
            if not cik:
                cik = self._get_cik_from_ticker(ticker)

            if not cik:
                logger.warning(f"Could not find CIK for {ticker}")
                return {}

            # Get recent 10-K filings
            filings = self._get_recent_filings(cik, form_type="10-K", count=1)

            if not filings:
                return {}

            # Extract financial data from most recent 10-K
            # Note: Full XBRL parsing would require additional libraries
            # For now, we'll extract basic info and provide URLs
            latest_filing = filings[0]

            return {
                'filing_url': latest_filing.get('url'),
                'filing_date': latest_filing.get('filingDate'),
                'cik': cik,
                'note': 'Full financial extraction from XBRL requires additional parsing libraries'
            }

        except Exception as e:
            logger.error(f"Error fetching from SEC EDGAR: {e}")
            return {}

    def fetch_from_company_website(self, company_name: str, ticker: str) -> Dict[str, Any]:
        """
        Attempt to find and extract investor relations data from company website
        """
        try:
            # Common investor relations URL patterns
            ir_urls = [
                f"https://investor.{company_name.lower().replace(' ', '').replace('.', '')}.com",
                f"https://ir.{company_name.lower().replace(' ', '').replace('.', '')}.com",
                f"https://www.{company_name.lower().replace(' ', '').replace('.', '')}.com/investors",
                f"https://www.{company_name.lower().replace(' ', '').replace('.', '')}.com/investor-relations",
            ]

            for url in ir_urls:
                try:
                    response = requests.get(url, timeout=5, headers={'User-Agent': self.user_agent})
                    if response.status_code == 200:
                        # Look for financial reports or annual reports links
                        soup = BeautifulSoup(response.content, 'html.parser')
                        # Find links to annual reports, 10-K, financial statements
                        financial_links = []
                        for link in soup.find_all('a', href=True):
                            href = link.get('href', '').lower()
                            text = link.get_text().lower()
                            if any(term in href or term in text for term in ['annual', '10-k', 'financial', 'report', 'sec']):
                                financial_links.append(link.get('href'))

                        if financial_links:
                            return {
                                'ir_url': url,
                                'financial_links': financial_links[:5]  # Top 5 links
                            }
                except:
                    continue

            return {}

        except Exception as e:
            logger.error(f"Error fetching from company website: {e}")
            return {}

    def fetch_from_yahoo_finance_web(self, ticker: str) -> Dict[str, Any]:
        """
        Scrape financial data from Yahoo Finance HTML pages
        This is a fallback when the yfinance API doesn't have complete data
        """
        try:
            # Normalize ticker for URL (BRK-B -> BRK-B, BRK.B -> BRK-B)
            url_ticker = ticker.replace('.', '-')

            # Fetch income statement page
            income_url = f"https://finance.yahoo.com/quote/{url_ticker}/financials"
            logger.info(f"Fetching income statement from: {income_url}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(income_url, headers=headers, timeout=15)

            if response.status_code != 200:
                logger.warning(f"Yahoo Finance web page returned status {response.status_code}")
                return {}

            soup = BeautifulSoup(response.content, 'html.parser')

            # Yahoo Finance stores financial data in JSON within script tags
            # Look for the data-react-helmet or data-module attributes
            financial_data = {}

            # Try to find the JSON data in script tags
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'root.App.main' in script.string:
                    # Extract JSON data from the script
                    try:
                        # Yahoo Finance embeds data in a specific format
                        # This is a simplified parser - may need refinement
                        import re
                        json_match = re.search(r'root\.App\.main\s*=\s*({.+?});', script.string, re.DOTALL)
                        if json_match:
                            import json
                            data = json.loads(json_match.group(1))
                            # Navigate through the nested structure to find financials
                            # This structure may vary, so we'll try multiple paths
                            logger.info("Found Yahoo Finance JSON data structure")
                    except Exception as e:
                        logger.debug(f"Error parsing Yahoo Finance JSON: {e}")

            # Alternative: Parse the HTML table directly
            # Yahoo Finance displays financials in tables
            income_tables = soup.find_all('div', {'data-test': 'fin-row'})
            if income_tables:
                logger.info(f"Found {len(income_tables)} financial rows in HTML")
                # Parse table structure
                # This would require more detailed HTML parsing

            # For now, return empty - we'll implement full parsing next
            return {}

        except Exception as e:
            logger.error(f"Error fetching from Yahoo Finance web: {e}")
            return {}

    def fetch_from_alpha_vantage(self, ticker: str) -> Dict[str, Any]:
        """
        Fetch financial data from Alpha Vantage as a backup
        """
        try:
            api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
            if not api_key:
                return {}

            # Fetch income statement
            income_url = f"https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={ticker}&apikey={api_key}"
            response = requests.get(income_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'annualReports' in data:
                    return {
                        'income_statement': data.get('annualReports', []),
                        'source': 'alpha_vantage'
                    }

            return {}

        except Exception as e:
            logger.error(f"Error fetching from Alpha Vantage: {e}")
            return {}

    def supplement_missing_data(self, company_data: Any, missing: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Intelligently supplement missing data from multiple sources
        """
        supplemented = {}

        # If income statement is missing key items or periods
        if missing.get('income_statement'):
            logger.info(f"Attempting to supplement income statement data for {company_data.ticker}")

            # Try Yahoo Finance web scraper first (most reliable for missing data)
            yahoo_data = self.yahoo_scraper.fetch_income_statement(company_data.ticker)
            if yahoo_data:
                # Convert to standard format
                converted = self.yahoo_scraper.convert_to_standard_format(yahoo_data, 'income_statement')
                if converted:
                    supplemented['income_statement'] = converted
                    logger.info(f"Found income statement data from Yahoo Finance web scraper")

            # Try Alpha Vantage if Yahoo scraper didn't work
            if not supplemented.get('income_statement'):
                av_data = self.fetch_from_alpha_vantage(company_data.ticker)
                if av_data:
                    supplemented['income_statement'] = av_data.get('income_statement', [])
                    logger.info(f"Found {len(supplemented['income_statement'])} income statement periods from Alpha Vantage")

            # Try SEC EDGAR as last resort
            if not supplemented.get('income_statement'):
                sec_data = self.fetch_from_sec_edgar(company_data.ticker)
                if sec_data.get('filing_url'):
                    supplemented['sec_filing_url'] = sec_data['filing_url']
                    logger.info(f"Found SEC filing URL: {sec_data['filing_url']}")

        # If balance sheet is missing
        if missing.get('balance_sheet'):
            logger.info(f"Attempting to supplement balance sheet data for {company_data.ticker}")

            # Try Financial Modeling Prep API first
            if self.fmp_client.api_key:
                fmp_statements = self.fmp_client.get_balance_sheet(company_data.ticker)
                if fmp_statements:
                    converted = self.fmp_client.convert_balance_sheet(fmp_statements)
                    if converted:
                        supplemented['balance_sheet'] = converted
                        logger.info(f"Found {len(converted)} balance sheet periods from Financial Modeling Prep")

            # Try Yahoo Finance web scraper if FMP didn't work
            if not supplemented.get('balance_sheet'):
                yahoo_data = self.yahoo_scraper.fetch_balance_sheet(company_data.ticker)
                if yahoo_data:
                    converted = self.yahoo_scraper.convert_to_standard_format(yahoo_data, 'balance_sheet')
                    if converted:
                        supplemented['balance_sheet'] = converted
                        logger.info(f"Found balance sheet data from Yahoo Finance web scraper")

            # Try Alpha Vantage if previous sources didn't work
            if not supplemented.get('balance_sheet'):
                balance_url = f"https://www.alphavantage.co/query?function=BALANCE_SHEET&symbol={company_data.ticker}&apikey={os.getenv('ALPHA_VANTAGE_API_KEY')}"
                try:
                    response = requests.get(balance_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if 'annualReports' in data:
                            supplemented['balance_sheet'] = data.get('annualReports', [])
                except:
                    pass

        # If cashflow is missing
        if missing.get('cashflow'):
            logger.info(f"Attempting to supplement cashflow data for {company_data.ticker}")

            # Try Financial Modeling Prep API first
            if self.fmp_client.api_key:
                fmp_statements = self.fmp_client.get_cashflow(company_data.ticker)
                if fmp_statements:
                    converted = self.fmp_client.convert_cashflow(fmp_statements)
                    if converted:
                        supplemented['cashflow'] = converted
                        logger.info(f"Found {len(converted)} cashflow periods from Financial Modeling Prep")

            # Try Yahoo Finance web scraper if FMP didn't work
            if not supplemented.get('cashflow'):
                yahoo_data = self.yahoo_scraper.fetch_cashflow(company_data.ticker)
                if yahoo_data:
                    converted = self.yahoo_scraper.convert_to_standard_format(yahoo_data, 'cashflow')
                    if converted:
                        supplemented['cashflow'] = converted
                        logger.info(f"Found cashflow data from Yahoo Finance web scraper")

            # Try Alpha Vantage if previous sources didn't work
            if not supplemented.get('cashflow'):
                cashflow_url = f"https://www.alphavantage.co/query?function=CASH_FLOW&symbol={company_data.ticker}&apikey={os.getenv('ALPHA_VANTAGE_API_KEY')}"
                try:
                    response = requests.get(cashflow_url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if 'annualReports' in data:
                            supplemented['cashflow'] = data.get('annualReports', [])
                except:
                    pass

        return supplemented

    def _get_cik_from_ticker(self, ticker: str) -> Optional[str]:
        """Get CIK (Central Index Key) from ticker symbol"""
        try:
            # Use SEC company tickers JSON
            url = "https://www.sec.gov/files/company_tickers.json"
            response = requests.get(url, headers={'User-Agent': self.user_agent}, timeout=10)

            if response.status_code == 200:
                data = response.json()
                for entry in data.values():
                    if entry.get('ticker', '').upper() == ticker.upper():
                        cik = str(entry.get('cik_str', ''))
                        return cik.zfill(10)  # CIK should be 10 digits

            return None

        except Exception as e:
            logger.error(f"Error getting CIK: {e}")
            return None

    def _get_recent_filings(self, cik: str, form_type: str = "10-K", count: int = 5) -> List[Dict]:
        """Get recent SEC filings for a company"""
        try:
            # Use SEC EDGAR API
            url = f"{self.sec_base_url}/cgi-bin/browse-edgar"
            params = {
                'action': 'getcompany',
                'CIK': cik,
                'type': form_type,
                'count': count
            }

            response = requests.get(url, params=params, headers={'User-Agent': self.user_agent}, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                filings = []

                # Parse filing table (simplified - would need more robust parsing)
                for row in soup.find_all('tr')[1:]:  # Skip header
                    cells = row.find_all('td')
                    if len(cells) >= 4:
                        filings.append({
                            'filingDate': cells[3].get_text().strip(),
                            'url': f"{self.sec_base_url}{cells[1].find('a')['href'] if cells[1].find('a') else ''}"
                        })

                return filings[:count]

            return []

        except Exception as e:
            logger.error(f"Error getting filings: {e}")
            return []
