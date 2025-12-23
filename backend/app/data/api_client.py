"""
API client for fetching stock data from various sources
"""
import yfinance as yf
import pandas as pd
from typing import Optional, Dict, List
import requests
from datetime import datetime, timedelta
import os


class YahooFinanceClient:
    """Client for Yahoo Finance API using yfinance library"""
    
    def __init__(self):
        self.session = None
    
    def get_ticker(self, symbol: str) -> Optional[yf.Ticker]:
        """Get yfinance Ticker object"""
        try:
            return yf.Ticker(symbol)
        except Exception as e:
            print(f"Error getting ticker {symbol}: {e}")
            return None
    
    def get_current_price(self, ticker: yf.Ticker) -> Optional[float]:
        """Get current stock price"""
        try:
            info = ticker.info
            return info.get('currentPrice') or info.get('regularMarketPrice')
        except Exception:
            try:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    return float(hist['Close'].iloc[-1])
            except Exception:
                return None
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
        """Search for ticker symbols and company names"""
        try:
            from yfinance import Search
            search = Search(query, max_results=max_results, enable_fuzzy_query=True)
            
            results = []
            if hasattr(search, 'quotes') and search.quotes:
                for quote in search.quotes:
                    # Handle both dict and object attributes
                    if isinstance(quote, dict):
                        ticker_symbol = quote.get('symbol', '') or quote.get('ticker', '')
                        company_name = quote.get('longname') or quote.get('shortname') or quote.get('name', '') or quote.get('longName', '')
                        exchange = quote.get('exchange', '') or quote.get('exchDisp', '')
                    else:
                        # Handle object attributes
                        ticker_symbol = getattr(quote, 'symbol', '') or getattr(quote, 'ticker', '')
                        company_name = getattr(quote, 'longname', '') or getattr(quote, 'shortname', '') or getattr(quote, 'name', '') or getattr(quote, 'longName', '')
                        exchange = getattr(quote, 'exchange', '') or getattr(quote, 'exchDisp', '')
                    
                    if ticker_symbol:
                        results.append({
                            'ticker': str(ticker_symbol),
                            'companyName': str(company_name) if company_name else '',
                            'exchange': str(exchange) if exchange else ''
                        })
            
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

