"""
MarketWatch Financial Data Scraper
Scrapes financial statements from MarketWatch as a backup source
"""
import requests
from bs4 import BeautifulSoup
import re
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MarketWatchScraper:
    """Scrape financial data from MarketWatch"""
    
    def __init__(self):
        self.base_url = "https://www.marketwatch.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    
    def _normalize_ticker(self, ticker: str) -> str:
        """Normalize ticker for MarketWatch URL"""
        # MarketWatch uses dots, not hyphens
        return ticker.replace('-', '.')
    
    def fetch_financials(self, ticker: str) -> Dict[str, Dict[str, float]]:
        """Fetch financial statements from MarketWatch"""
        try:
            url_ticker = self._normalize_ticker(ticker)
            url = f"{self.base_url}/investing/stock/{url_ticker}/financials"
            
            logger.info(f"Fetching financials from MarketWatch: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            
            if response.status_code != 200:
                logger.warning(f"MarketWatch returned status {response.status_code}")
                return {}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # MarketWatch displays financials in tables
            # Look for financial statement tables
            tables = soup.find_all('table', class_=re.compile(r'financial|data'))
            
            result = {}
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) < 2:
                        continue
                    
                    label = cells[0].get_text(strip=True)
                    if not label:
                        continue
                    
                    # Extract values from remaining cells
                    values = []
                    for cell in cells[1:]:
                        value_text = cell.get_text(strip=True)
                        if value_text and value_text != '-':
                            try:
                                # Remove commas and parse
                                value = float(value_text.replace(',', '').replace('(', '-').replace(')', ''))
                                values.append(value)
                            except ValueError:
                                continue
                    
                    if values:
                        # Use first value as most recent period
                        result[label] = values[0]
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching from MarketWatch: {e}")
            return {}

