"""
Backup data source clients for when primary sources (Yahoo Finance) hit rate limits
"""
import requests
import logging
from typing import Optional, Dict, List, Any
import os
from datetime import datetime, timedelta
import re
import json

logger = logging.getLogger(__name__)


class IEXCloudClient:
    """
    IEX Cloud API client - DEPRECATED

    IEX Cloud was retired on August 31, 2024. This class is kept for backward compatibility
    but is no longer used in the backup fetcher. Please use Alpha Vantage or other alternatives.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("IEX_CLOUD_API_KEY")
        self.base_url = "https://cloud.iexapis.com/stable"
        self.sandbox_url = "https://sandbox.iexapis.com/stable"
        self.use_sandbox = os.getenv("IEX_USE_SANDBOX", "false").lower() == "true"

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request"""
        if not self.api_key:
            return None

        try:
            url = f"{self.sandbox_url if self.use_sandbox else self.base_url}/{endpoint}"
            request_params = {"token": self.api_key}
            if params:
                request_params.update(params)

            response = requests.get(url, params=request_params, timeout=10)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning("IEX Cloud rate limit exceeded")
                return None
            else:
                logger.debug(f"IEX Cloud returned status {response.status_code}")
                return None
        except Exception as e:
            logger.debug(f"Error calling IEX Cloud API: {e}")
            return None

    def get_quote(self, ticker: str) -> Optional[Dict]:
        """Get current quote"""
        data = self._make_request(f"stock/{ticker}/quote")
        if data:
            return {
                'price': data.get('latestPrice'),
                'market_cap': data.get('marketCap'),
                'company_name': data.get('companyName'),
                'currency': 'USD'
            }
        return None

    def get_company_info(self, ticker: str) -> Optional[Dict]:
        """Get company information"""
        data = self._make_request(f"stock/{ticker}/company")
        if data:
            return {
                'companyName': data.get('companyName'),
                'sector': data.get('sector'),
                'industry': data.get('industry'),
                'website': data.get('website')
            }
        return None


class MarketStackClient:
    """MarketStack API client - Free tier: 1,000 requests/month"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MARKETSTACK_API_KEY")
        self.base_url = "http://api.marketstack.com/v1"

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make API request"""
        if not self.api_key:
            return None

        try:
            url = f"{self.base_url}/{endpoint}"
            request_params = {"access_key": self.api_key}
            if params:
                request_params.update(params)

            response = requests.get(url, params=request_params, timeout=10)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                logger.warning("MarketStack rate limit exceeded")
                return None
            else:
                logger.debug(f"MarketStack returned status {response.status_code}")
                return None
        except Exception as e:
            logger.debug(f"Error calling MarketStack API: {e}")
            return None

    def get_intraday(self, ticker: str) -> Optional[Dict]:
        """Get latest intraday data"""
        data = self._make_request("intraday/latest", {"symbols": ticker})
        if data and data.get('data'):
            latest = data['data'][0] if isinstance(data['data'], list) else data['data']
            return {
                'price': latest.get('last'),
                'volume': latest.get('volume'),
                'timestamp': latest.get('date')
            }
        return None


class GoogleFinanceClient:
    """Google Finance client - scrapes Google Finance website for stock data"""

    def __init__(self):
        self.base_url = "https://www.google.com/finance"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

    def _normalize_ticker(self, ticker: str) -> str:
        """Normalize ticker for Google Finance URL"""
        # Google Finance uses exchange:ticker format
        # For international tickers like PPE.JO, convert to JSE:PPE
        # For US tickers, use NASDAQ: or NYSE: prefix if needed

        ticker_upper = ticker.upper()

        # Map exchange suffixes to Google Finance exchange codes
        exchange_map = {
            '.JO': 'JSE',  # Johannesburg Stock Exchange
            '.L': 'LON',   # London Stock Exchange
            '.TO': 'TSE',  # Toronto Stock Exchange
            '.PA': 'EPA',  # Euronext Paris
            '.DE': 'ETR',  # Xetra (Germany)
            '.HK': 'HKG',  # Hong Kong Stock Exchange
            '.SS': 'SHA',  # Shanghai Stock Exchange
            '.SZ': 'SHE',  # Shenzhen Stock Exchange
            '.T': 'TYO',   # Tokyo Stock Exchange
            '.AS': 'AMS',  # Amsterdam Stock Exchange
            '.BR': 'BVMF', # B3 (Brazil)
            '.MX': 'MEX',  # Mexican Stock Exchange
            '.SA': 'SAU',  # Saudi Stock Exchange
            '.SW': 'SWX',  # SIX Swiss Exchange
            '.VI': 'VIE',  # Vienna Stock Exchange
            '.ST': 'STO',  # Stockholm Stock Exchange
            '.OL': 'OSL',  # Oslo Stock Exchange
            '.CO': 'CPH',  # Copenhagen Stock Exchange
            '.HE': 'HEL',  # Helsinki Stock Exchange
            '.IC': 'ICE',  # Iceland Stock Exchange
            '.LS': 'LIS',  # Lisbon Stock Exchange
            '.MC': 'MAD',  # Madrid Stock Exchange
            '.MI': 'MIL',  # Milan Stock Exchange
            '.NX': 'NSE',  # National Stock Exchange of India
            '.TA': 'TLV',  # Tel Aviv Stock Exchange
            '.TW': 'TPE',  # Taiwan Stock Exchange
            '.V': 'VAN',   # TSX Venture Exchange
            '.WA': 'WAR',  # Warsaw Stock Exchange
        }

        # Check if ticker has an exchange suffix
        for suffix, exchange_code in exchange_map.items():
            if ticker_upper.endswith(suffix):
                base_ticker = ticker_upper[:-len(suffix)]
                return f"{exchange_code}:{base_ticker}"

        # For US tickers, try to determine exchange (default to NASDAQ)
        # Google Finance will handle this automatically, but we can try NASDAQ: or NYSE:
        return ticker_upper

    def _make_request(self, ticker: str) -> Optional[Dict]:
        """Make request to Google Finance"""
        try:
            normalized_ticker = self._normalize_ticker(ticker)
            url = f"{self.base_url}/quote/{normalized_ticker}"

            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return {'html': response.text, 'ticker': normalized_ticker}
            elif response.status_code == 404:
                logger.debug(f"Google Finance returned 404 for {ticker}")
                return None
            else:
                logger.debug(f"Google Finance returned status {response.status_code} for {ticker}")
                return None
        except Exception as e:
            logger.debug(f"Error calling Google Finance for {ticker}: {e}")
            return None

    def _parse_quote_data(self, html_content: str) -> Optional[Dict]:
        """Parse quote data from Google Finance HTML"""
        try:
            # Google Finance embeds data in JSON-LD or script tags
            # Look for JSON data in script tags
            json_pattern = r'<script[^>]*>.*?({.*?"price":.*?})</script>'
            matches = re.findall(json_pattern, html_content, re.DOTALL | re.IGNORECASE)

            # Also try to find price in various formats
            price_patterns = [
                r'"price"\s*:\s*"?([0-9,]+\.?[0-9]*)"?',
                r'data-price="([0-9,]+\.?[0-9]*)"',
                r'class="[^"]*price[^"]*"[^>]*>([0-9,]+\.?[0-9]*)',
            ]

            price = None
            for pattern in price_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    try:
                        price_str = match.group(1).replace(',', '')
                        price = float(price_str)
                        break
                    except:
                        continue

            # Try to extract company name
            name_patterns = [
                r'<title>([^<]+)</title>',
                r'"name"\s*:\s*"([^"]+)"',
                r'<h1[^>]*>([^<]+)</h1>',
            ]

            company_name = None
            for pattern in name_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    company_name = match.group(1).strip()
                    # Clean up title format
                    if ' - Google Finance' in company_name:
                        company_name = company_name.replace(' - Google Finance', '').strip()
                    break

            # Try to extract market cap
            market_cap = None
            market_cap_patterns = [
                r'"marketCap"\s*:\s*"?([0-9,]+\.?[0-9]*)"?',
                r'Market cap[^:]*:\s*([0-9,]+\.?[0-9]*)\s*([A-Z]{3})?',
            ]

            for pattern in market_cap_patterns:
                match = re.search(pattern, html_content, re.IGNORECASE)
                if match:
                    try:
                        cap_str = match.group(1).replace(',', '')
                        market_cap = float(cap_str)
                        # Handle billions/millions if present
                        if len(match.groups()) > 1 and match.group(2):
                            unit = match.group(2).upper()
                            if 'B' in unit or 'BILLION' in unit.upper():
                                market_cap *= 1e9
                            elif 'M' in unit or 'MILLION' in unit.upper():
                                market_cap *= 1e6
                        break
                    except:
                        continue

            if price:
                return {
                    'price': price,
                    'company_name': company_name or 'Unknown',
                    'market_cap': market_cap,
                    'currency': 'USD'  # Default, may need to detect from page
                }

            return None
        except Exception as e:
            logger.debug(f"Error parsing Google Finance data: {e}")
            return None

    def get_quote(self, ticker: str) -> Optional[Dict]:
        """Get current quote from Google Finance"""
        response_data = self._make_request(ticker)
        if not response_data:
            return None

        quote_data = self._parse_quote_data(response_data['html'])
        return quote_data

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get current price from Google Finance"""
        quote = self.get_quote(ticker)
        if quote and quote.get('price'):
            return float(quote['price'])
        return None

    def get_company_info(self, ticker: str) -> Optional[Dict]:
        """Get company information from Google Finance"""
        response_data = self._make_request(ticker)
        if not response_data:
            return None

        html_content = response_data['html']

        # Try to extract company name
        name_patterns = [
            r'<title>([^<]+)</title>',
            r'"name"\s*:\s*"([^"]+)"',
            r'<h1[^>]*>([^<]+)</h1>',
        ]

        company_name = None
        for pattern in name_patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                company_name = match.group(1).strip()
                if ' - Google Finance' in company_name:
                    company_name = company_name.replace(' - Google Finance', '').strip()
                break

        # Try to extract sector/industry (may not always be available)
        sector = None
        industry = None

        sector_patterns = [
            r'Sector[^:]*:\s*([^<\n]+)',
            r'"sector"\s*:\s*"([^"]+)"',
        ]

        for pattern in sector_patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                sector = match.group(1).strip()
                break

        if company_name:
            return {
                'companyName': company_name,
                'sector': sector,
                'industry': industry
            }

        return None


class FinancialModelingPrepBackupClient:
    """Financial Modeling Prep API client for backup price data (separate from main FMP client)"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("FMP_API_KEY")
        self.base_url = "https://financialmodelingprep.com/api/v3"

    def _make_request(self, endpoint: str) -> Optional[Any]:
        """Make API request"""
        if not self.api_key:
            return None

        try:
            url = f"{self.base_url}/{endpoint}?apikey={self.api_key}"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data
            elif response.status_code == 429:
                logger.warning("Financial Modeling Prep rate limit exceeded")
                return None
            else:
                logger.debug(f"Financial Modeling Prep returned status {response.status_code}")
                return None
        except Exception as e:
            logger.debug(f"Error calling Financial Modeling Prep API: {e}")
            return None

    def get_quote(self, ticker: str) -> Optional[Dict]:
        """Get current quote"""
        data = self._make_request(f"quote/{ticker}")
        if data and isinstance(data, list) and len(data) > 0:
            quote = data[0]
            return {
                'price': quote.get('price'),
                'market_cap': quote.get('marketCap'),
                'company_name': quote.get('name'),
                'currency': 'USD'
            }
        return None

    def get_profile(self, ticker: str) -> Optional[Dict]:
        """Get company profile"""
        data = self._make_request(f"profile/{ticker}")
        if data and isinstance(data, list) and len(data) > 0:
            profile = data[0]
            return {
                'companyName': profile.get('companyName'),
                'sector': profile.get('sector'),
                'industry': profile.get('industry'),
                'website': profile.get('website')
            }
        return None


class BackupDataFetcher:
    """Fetches data from backup sources when primary source fails"""

    def __init__(self):
        # IEX Cloud was retired on August 31, 2024 - removed from backup sources
        # self.iex_client = IEXCloudClient()  # DEPRECATED - IEX Cloud retired
        self.marketstack_client = MarketStackClient()
        self.fmp_client = FinancialModelingPrepBackupClient()
        self.google_finance_client = GoogleFinanceClient()  # No API key needed - web scraping
        # Alpha Vantage (free tier available - 5 API calls per minute, 500 per day)
        # Import here to avoid circular dependencies
        try:
            from app.data.sec_edgar_client import AlphaVantageClient
            # Pass API key explicitly to ensure it's loaded
            api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
            self.alpha_vantage_client = AlphaVantageClient(api_key=api_key) if api_key else None
            if self.alpha_vantage_client and api_key:
                logger.info("Alpha Vantage client initialized with API key")
            elif not api_key:
                logger.debug("Alpha Vantage API key not found in environment")
        except ImportError:
            self.alpha_vantage_client = None
            logger.warning("AlphaVantageClient could not be imported")

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Try to get current price from backup sources - MarketStack prioritized"""
        sources_tried = []

        # Try MarketStack FIRST (prioritized - free tier: 1,000 requests/month)
        if self.marketstack_client.api_key:
            sources_tried.append("MarketStack")
            intraday = self.marketstack_client.get_intraday(ticker)
            if intraday and intraday.get('price'):
                logger.info(f"Got price from MarketStack: {intraday['price']}")
                return float(intraday['price'])
            else:
                logger.debug(f"MarketStack returned no price for {ticker}")
        else:
            logger.debug("MarketStack API key not configured")

        # Try Alpha Vantage second (free tier - 5 calls/min, 500/day)
        if self.alpha_vantage_client and self.alpha_vantage_client.api_key:
            sources_tried.append("Alpha Vantage")
            quote = self.alpha_vantage_client.get_quote(ticker)
            if quote and quote.get('price'):
                logger.info(f"Got price from Alpha Vantage: {quote['price']}")
                return float(quote['price'])
            else:
                logger.debug(f"Alpha Vantage returned no price for {ticker}")
        else:
            logger.debug("Alpha Vantage API key not configured")

        # Try Financial Modeling Prep third
        if self.fmp_client.api_key:
            sources_tried.append("Financial Modeling Prep")
            quote = self.fmp_client.get_quote(ticker)
            if quote and quote.get('price'):
                logger.info(f"Got price from Financial Modeling Prep: {quote['price']}")
                return float(quote['price'])
            else:
                logger.debug(f"Financial Modeling Prep returned no price for {ticker}")
        else:
            logger.debug("Financial Modeling Prep API key not configured")

        # Try Google Finance last (no API key needed - web scraping)
        sources_tried.append("Google Finance")
        try:
            price = self.google_finance_client.get_current_price(ticker)
            if price:
                logger.info(f"Got price from Google Finance: {price}")
                return float(price)
            else:
                logger.debug(f"Google Finance returned no price for {ticker}")
        except Exception as e:
            logger.debug(f"Error getting price from Google Finance: {e}")

        if sources_tried:
            logger.warning(f"Tried backup sources {', '.join(sources_tried)} for {ticker} but none returned a price")
        else:
            logger.warning(f"No backup sources configured for {ticker} (no API keys set). Consider setting ALPHA_VANTAGE_API_KEY, FMP_API_KEY, or MARKETSTACK_API_KEY")

        return None

    def get_quote_with_metrics(self, ticker: str) -> Optional[Dict]:
        """Try to get quote with price and market cap from backup sources - MarketStack prioritized"""
        sources_tried = []

        # Try MarketStack first (prioritized)
        if self.marketstack_client.api_key:
            sources_tried.append("MarketStack")
            intraday = self.marketstack_client.get_intraday(ticker)
            if intraday and intraday.get('price'):
                # Convert MarketStack response to standard quote format
                quote = {
                    'price': intraday['price'],
                    'symbol': ticker,
                    'source': 'MarketStack'
                }
                logger.info(f"Got quote from MarketStack")
                return quote
            else:
                logger.debug(f"MarketStack returned no quote for {ticker}")
        else:
            logger.debug("MarketStack API key not configured")

        # Try Alpha Vantage second
        if self.alpha_vantage_client and self.alpha_vantage_client.api_key:
            sources_tried.append("Alpha Vantage")
            quote = self.alpha_vantage_client.get_quote(ticker)
            if quote and quote.get('price'):
                logger.info(f"Got quote from Alpha Vantage")
                return quote
            else:
                logger.debug(f"Alpha Vantage returned no quote for {ticker}")
        else:
            logger.debug("Alpha Vantage API key not configured")

        # Try Financial Modeling Prep third
        if self.fmp_client.api_key:
            sources_tried.append("Financial Modeling Prep")
            quote = self.fmp_client.get_quote(ticker)
            if quote and quote.get('price'):
                logger.info(f"Got quote from Financial Modeling Prep")
                return quote
            else:
                logger.debug(f"Financial Modeling Prep returned no quote for {ticker}")
        else:
            logger.debug("Financial Modeling Prep API key not configured")

        # Try Google Finance last (no API key needed)
        sources_tried.append("Google Finance")
        try:
            quote = self.google_finance_client.get_quote(ticker)
            if quote and quote.get('price'):
                logger.info(f"Got quote from Google Finance")
                return quote
            else:
                logger.debug(f"Google Finance returned no quote for {ticker}")
        except Exception as e:
            logger.debug(f"Error getting quote from Google Finance: {e}")

        if sources_tried:
            logger.warning(f"Tried backup sources {', '.join(sources_tried)} for {ticker} but none returned a quote")
        else:
            logger.warning(f"No backup sources configured for {ticker} (no API keys set)")

        return None

    def get_company_info(self, ticker: str) -> Optional[Dict]:
        """Try to get company info from backup sources"""
        # Try Alpha Vantage first
        if self.alpha_vantage_client and self.alpha_vantage_client.api_key:
            overview = self.alpha_vantage_client.get_company_overview(ticker)
            if overview:
                logger.info(f"Got company info from Alpha Vantage")
                return overview

        # Try Financial Modeling Prep
        if self.fmp_client.api_key:
            profile = self.fmp_client.get_profile(ticker)
            if profile:
                logger.info(f"Got company info from Financial Modeling Prep")
                return profile

        # Try Google Finance (no API key needed)
        try:
            company_info = self.google_finance_client.get_company_info(ticker)
            if company_info:
                logger.info(f"Got company info from Google Finance")
                return company_info
        except Exception as e:
            logger.debug(f"Error getting company info from Google Finance: {e}")

        return None
