"""
API client for fetching stock data from various sources
"""
import yfinance as yf
import pandas as pd
from typing import Optional, Dict, List
import requests
from datetime import datetime, timedelta
import os
import logging

logger = logging.getLogger(__name__)


class YahooFinanceClient:
    """Client for Yahoo Finance API using yfinance library"""
    
    def __init__(self):
        self.session = None
    
    def get_ticker(self, symbol: str) -> Optional[yf.Ticker]:
        """Get yfinance Ticker object"""
        try:
            ticker = yf.Ticker(symbol)
            # For international tickers, try to verify with a lightweight check
            # Some international tickers don't have fast_info, so we use history as a fallback
            try:
                _ = ticker.fast_info  # Fast check
            except:
                # For international tickers, try history as verification
                try:
                    hist = ticker.history(period="1d", timeout=10)
                    if hist.empty:
                        logger.warning(f"Ticker {symbol} exists but has no historical data")
                    # If we get here without exception, ticker is valid
                except Exception as hist_e:
                    # If both fast_info and history fail, ticker might still be valid
                    # (some tickers require different access methods)
                    logger.debug(f"Could not verify ticker {symbol} with fast_info or history: {hist_e}")
            return ticker
        except Exception as e:
            logger.error(f"Error getting ticker {symbol}: {e}")
            return None
    
    def get_current_price(self, ticker: yf.Ticker) -> Optional[float]:
        """Get current stock price with retry logic for rate limiting"""
        import time
        
        # Add initial delay to avoid hitting rate limits immediately
        time.sleep(1)
        
        # Try history first (least rate-limited, most reliable)
        try:
            hist = ticker.history(period="5d", timeout=15)  # Get 5 days, use most recent
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
                if price and price > 0:
                    logger.info(f"Got price from history: {price}")
                    return price
            else:
                # For international tickers, try longer period if 5d is empty
                logger.debug("5-day history empty, trying longer period for international tickers...")
                try:
                    hist_longer = ticker.history(period="1mo", timeout=15)
                    if not hist_longer.empty:
                        price = float(hist_longer['Close'].iloc[-1])
                        if price and price > 0:
                            logger.info(f"Got price from longer history: {price}")
                            return price
                except Exception as e2:
                    logger.debug(f"Longer history also failed: {e2}")
        except Exception as e:
            error_str = str(e).lower()
            if '429' not in error_str and 'too many requests' not in error_str:
                logger.warning(f"Error getting price from history: {e}")
        
        # Try fast_info (less rate-limited than info)
        try:
            time.sleep(1)  # Small delay between requests
            fast_info = ticker.fast_info
            if hasattr(fast_info, 'lastPrice') and fast_info.lastPrice:
                price = float(fast_info.lastPrice)
                if price and price > 0:
                    logger.info(f"Got price from fast_info: {price}")
                    return price
        except Exception as e:
            logger.debug(f"fast_info not available: {e}")
        
        # Try info with retry for rate limiting (most rate-limited)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = (2 ** attempt) * 5  # Exponential backoff: 10s, 20s, 40s
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                
                info = ticker.info
                price = info.get('currentPrice') or info.get('regularMarketPrice')
                if price and price > 0:
                    logger.info(f"Got price from info: {price}")
                    return price
                break  # Got info but no price, don't retry
            except Exception as e:
                error_str = str(e).lower()
                if '429' in error_str or 'too many requests' in error_str or 'rate limit' in error_str:
                    if attempt < max_retries - 1:
                        continue  # Will wait before next attempt
                    else:
                        logger.error(f"Rate limited after {max_retries} attempts. Cannot get current price.")
                else:
                    logger.warning(f"Error getting price from ticker.info: {e}")
                    break
        
        logger.error("Could not get current price from any source")
        return None
    
    def get_company_info(self, ticker: yf.Ticker) -> Dict:
        """Get company information"""
        try:
            return ticker.info
        except Exception:
            return {}
    
    def get_financials(self, ticker: yf.Ticker) -> Dict:
        """Get financial statements - tries multiple methods for better data"""
        result = {
            'income_statement': {},
            'balance_sheet': {},
            'cashflow': {}
        }
        
        try:
            # Try annual financials first
            financials = ticker.financials
            balance_sheet = ticker.balance_sheet
            cashflow = ticker.cashflow
            
            if not financials.empty:
                result['income_statement'] = financials.to_dict()
            if not balance_sheet.empty:
                result['balance_sheet'] = balance_sheet.to_dict()
            if not cashflow.empty:
                result['cashflow'] = cashflow.to_dict()
            
            # If annual data is empty, try quarterly/annual income statement
            if not result['income_statement']:
                try:
                    income_stmt = ticker.income_stmt  # Annual
                    if not income_stmt.empty:
                        result['income_statement'] = income_stmt.to_dict()
                except:
                    pass
            
            # Try quarterly statements if annual is limited
            if len(result['income_statement']) < 3:
                try:
                    quarterly_income = ticker.quarterly_income_stmt
                    if not quarterly_income.empty:
                        # Merge quarterly data
                        q_dict = quarterly_income.to_dict()
                        result['income_statement'].update(q_dict)
                except:
                    pass
            
            # Try balance sheet alternatives
            if not result['balance_sheet']:
                try:
                    bs = ticker.balance_sheet
                    if not bs.empty:
                        result['balance_sheet'] = bs.to_dict()
                except:
                    pass
            
            # Try cashflow alternatives
            if not result['cashflow']:
                try:
                    cf = ticker.cashflow
                    if not cf.empty:
                        result['cashflow'] = cf.to_dict()
                except:
                    pass
                    
        except Exception as e:
            print(f"Error getting financials: {e}")
        
        return result
    
    def get_historical_prices(self, ticker: yf.Ticker, period: str = "10y") -> Optional[pd.DataFrame]:
        """Get historical price data"""
        try:
            return ticker.history(period=period)
        except Exception:
            return None
    
    def search_tickers(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for ticker symbols and company names using Yahoo Finance API
        Filters out options contracts to return only stocks and ETFs"""
        try:
            import json
            import urllib.parse
            
            # Use Yahoo Finance search API directly
            url = f"https://query1.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}&quotesCount={max_results}&newsCount=0"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Extract quotes from the response
            if 'quotes' in data and isinstance(data['quotes'], list):
                for quote in data['quotes'][:max_results * 2]:  # Get more to filter options
                    ticker_symbol = quote.get('symbol', '')
                    company_name = quote.get('longname') or quote.get('shortname') or quote.get('name', '')
                    exchange = quote.get('exchange', '') or quote.get('exchDisp', '')
                    quote_type = quote.get('quoteType', '').upper()
                    
                    # Filter out options contracts and other non-stock instruments
                    # Options typically have: long tickers (15+ chars), exchange='OPR', quoteType='OPTION'
                    # Also check if company name contains "call" or "put" which indicates options
                    exchange_upper = str(exchange).upper()
                    company_name_lower = str(company_name).lower()
                    
                    is_option = (
                        quote_type == 'OPTION' or 
                        exchange_upper == 'OPR' or
                        (len(ticker_symbol) > 12 and any(char.isdigit() for char in ticker_symbol[-8:])) or  # Options have dates in ticker
                        'call' in company_name_lower or
                        'put' in company_name_lower
                    )
                    
                    if ticker_symbol and not is_option:
                        results.append({
                            'ticker': str(ticker_symbol),
                            'companyName': str(company_name) if company_name else '',
                            'exchange': str(exchange) if exchange else ''
                        })
                        
                        # Stop once we have enough non-option results
                        if len(results) >= max_results:
                            break
            
            return results
        except Exception as e:
            print(f"Error searching tickers: {e}")
            import traceback
            traceback.print_exc()
            return []


class FREDClient:
    """Client for FRED (Federal Reserve Economic Data) API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"
    
    def get_risk_free_rate(self) -> float:
        """Get 10-year Treasury yield as risk-free rate"""
        # Default to 4% if API not available
        if not self.api_key:
            return 0.04
        
        try:
            # Series ID for 10-Year Treasury Constant Maturity Rate
            series_id = "DGS10"
            params = {
                "series_id": series_id,
                "api_key": self.api_key,
                "file_type": "json",
                "limit": 1,
                "sort_order": "desc"
            }
            response = requests.get(self.base_url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('observations'):
                    rate = float(data['observations'][0]['value']) / 100
                    return rate
        except Exception:
            pass
        
        return 0.04  # Default 4%

