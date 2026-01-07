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
    
    def _get_current_price_with_tracking(self, ticker: yf.Ticker, symbol: str) -> List[Dict]:
        """Get current price with detailed tracking of each method attempted - optimized for speed"""
        import concurrent.futures
        import threading
        
        price_attempts = []
        
        def try_history_5d():
            """Try 5-day history with timeout"""
            attempt = {
                'api': 'Yahoo Finance Historical Data',
                'method': 'ticker.history(period="5d")',
                'status': 'attempting',
                'details': f'Fetching 5-day price history for {symbol}'
            }
            
            try:
                hist = ticker.history(period="5d", timeout=3)  # 3 second timeout
                if not hist.empty:
                    price = float(hist['Close'].iloc[-1])
                    if price and price > 0:
                        attempt.update({
                            'status': 'success',
                            'price': price,
                            'details': f'Retrieved price {price} from 5-day history (most recent close)'
                        })
                        return attempt, price
                    else:
                        attempt.update({
                            'status': 'failed',
                            'error': 'Invalid price value',
                            'details': f'History returned price {price} which is invalid (≤0)'
                        })
                else:
                    attempt.update({
                        'status': 'failed',
                        'error': 'Empty history data',
                        'details': '5-day history returned empty DataFrame'
                    })
            except Exception as e:
                error_str = str(e)
                attempt.update({
                    'status': 'failed',
                    'error': error_str,
                    'details': f'Exception during 5-day history: {error_str}'
                })
            
            return attempt, None
        
        def try_fast_info():
            """Try fast_info with timeout"""
            attempt = {
                'api': 'Yahoo Finance Fast Info',
                'method': 'ticker.fast_info.lastPrice',
                'status': 'attempting',
                'details': f'Fetching current price from fast_info for {symbol}'
            }
            
            try:
                fast_info = ticker.fast_info
                if hasattr(fast_info, 'lastPrice') and fast_info.lastPrice:
                    price = float(fast_info.lastPrice)
                    if price and price > 0:
                        attempt.update({
                            'status': 'success',
                            'price': price,
                            'details': f'Retrieved price {price} from fast_info.lastPrice'
                        })
                        return attempt, price
                    else:
                        attempt.update({
                            'status': 'failed',
                            'error': 'Invalid price value',
                            'details': f'fast_info returned price {price} which is invalid (≤0)'
                        })
                else:
                    attempt.update({
                        'status': 'failed',
                        'error': 'No lastPrice in fast_info',
                        'details': 'fast_info object does not contain lastPrice or it is None'
                    })
            except Exception as e:
                error_str = str(e)
                attempt.update({
                    'status': 'failed',
                    'error': error_str,
                    'details': f'Exception during fast_info access: {error_str}'
                })
            
            return attempt, None
        
        # Try methods in parallel with 2-second timeout each
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both methods simultaneously
            future_history = executor.submit(try_history_5d)
            future_fast_info = executor.submit(try_fast_info)
            
            # Wait for results with timeout
            try:
                # Check history first (usually faster)
                history_attempt, history_price = future_history.result(timeout=3)
                price_attempts.append(history_attempt)
                
                if history_price:
                    # Cancel the other future if we got a price
                    future_fast_info.cancel()
                    return price_attempts
                
                # If history failed, try fast_info
                fast_info_attempt, fast_info_price = future_fast_info.result(timeout=2)
                price_attempts.append(fast_info_attempt)
                
                if fast_info_price:
                    return price_attempts
                    
            except concurrent.futures.TimeoutError:
                # If both methods timeout, add timeout attempts
                price_attempts.append({
                    'api': 'Yahoo Finance',
                    'method': 'parallel_timeout',
                    'status': 'failed',
                    'error': 'Timeout',
                    'details': 'Both history and fast_info methods timed out after 3 seconds'
                })
        
        # If we get here, both methods failed
        return price_attempts

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
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get current quote (price and basic info) for a ticker symbol with detailed API attempt tracking"""
        import time
        start_time = time.time()
        api_attempts = []  # Track all API attempts and their results
        
        try:
            # Step 1: Try Yahoo Finance first (primary source) - max 5 seconds
            yahoo_attempts = self._try_yahoo_finance(symbol)
            api_attempts.extend(yahoo_attempts)
            
            # Check if Yahoo Finance succeeded
            for attempt in yahoo_attempts:
                if attempt.get('status') == 'success' and attempt.get('price'):
                    # Yahoo Finance succeeded - get company info and return
                    return self._build_successful_response(symbol, attempt.get('price'), api_attempts)
            
            # Check if we have time left (max 10 seconds total)
            elapsed_time = time.time() - start_time
            if elapsed_time >= 9:  # Leave 1 second buffer
                api_attempts.append({
                    'api': 'Timeout Handler',
                    'method': 'overall_timeout_check',
                    'status': 'failed',
                    'error': 'Overall timeout reached',
                    'details': f'Reached 9-second limit after Yahoo Finance, skipping backup APIs'
                })
                return self._build_failure_response(symbol, api_attempts)
            
            # Step 2: Yahoo Finance failed, try backup APIs (Google Finance first, then others)
            backup_attempts = self._try_backup_apis(symbol)
            api_attempts.extend(backup_attempts)
            
            # Check if any backup API succeeded
            for attempt in backup_attempts:
                if attempt.get('status') == 'success' and attempt.get('price'):
                    # Backup API succeeded
                    return self._build_successful_response(symbol, attempt.get('price'), api_attempts, 
                                                         company_name=attempt.get('company_name'),
                                                         market_cap=attempt.get('market_cap'))
            
            # All APIs failed - compile detailed failure report
            return self._build_failure_response(symbol, api_attempts)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error getting quote for {symbol}: {e}")
            
            # Add the exception to attempts log
            api_attempts.append({
                'api': 'General Error Handler',
                'method': 'get_quote()',
                'status': 'failed',
                'error': error_msg,
                'details': f'Unexpected exception during quote retrieval: {error_msg}'
            })
            
            return self._build_failure_response(symbol, api_attempts, error_msg)

    def _try_yahoo_finance(self, symbol: str) -> List[Dict]:
        """Try Yahoo Finance API with detailed tracking"""
        yahoo_attempts = []
        
        # Step 1: Try to create ticker object
        yahoo_attempts.append({
            'api': 'Yahoo Finance',
            'method': 'yf.Ticker() creation',
            'status': 'attempting',
            'details': f'Creating ticker object for {symbol}'
        })
        
        try:
            ticker = self.get_ticker(symbol)
            if not ticker:
                yahoo_attempts[-1].update({
                    'status': 'failed',
                    'error': 'Could not create ticker object',
                    'details': f'yf.Ticker({symbol}) returned None - symbol may not exist or be invalid'
                })
                return yahoo_attempts
            
            yahoo_attempts[-1].update({
                'status': 'success',
                'details': f'Successfully created ticker object for {symbol}'
            })
            
            # Step 2: Try to get current price using multiple Yahoo Finance methods
            price_attempts = self._get_current_price_with_tracking(ticker, symbol)
            yahoo_attempts.extend(price_attempts)
            
            # Check if any Yahoo Finance price method succeeded
            for attempt in price_attempts:
                if attempt.get('status') == 'success' and attempt.get('price'):
                    return yahoo_attempts  # Success with Yahoo Finance
            
            return yahoo_attempts
            
        except Exception as e:
            yahoo_attempts[-1].update({
                'status': 'failed',
                'error': str(e),
                'details': f'Exception during Yahoo Finance ticker creation: {str(e)}'
            })
            return yahoo_attempts

    def _try_backup_apis(self, symbol: str) -> List[Dict]:
        """Try backup APIs when Yahoo Finance fails - MarketStack prioritized first"""
        backup_attempts = []
        
        try:
            from app.data.backup_clients import BackupDataFetcher
            backup_fetcher = BackupDataFetcher()
            
            # Try MarketStack FIRST (prioritized - API key based, reliable)
            if backup_fetcher.marketstack_client.api_key:
                backup_attempts.append({
                    'api': 'MarketStack',
                    'method': 'get_intraday()',
                    'status': 'attempting',
                    'details': f'Fetching intraday data from MarketStack for {symbol}'
                })
                
                try:
                    intraday = backup_fetcher.marketstack_client.get_intraday(symbol)
                    if intraday and intraday.get('price'):
                        backup_attempts[-1].update({
                            'status': 'success',
                            'price': float(intraday['price']),
                            'company_name': symbol,  # MarketStack doesn't provide company name in intraday
                            'details': f'Successfully retrieved price {intraday["price"]} from MarketStack intraday data'
                        })
                        return backup_attempts  # Success, return early
                    else:
                        backup_attempts[-1].update({
                            'status': 'failed',
                            'error': 'No price data returned',
                            'details': 'MarketStack returned empty or invalid intraday data'
                        })
                except Exception as e:
                    backup_attempts[-1].update({
                        'status': 'failed',
                        'error': str(e),
                        'details': f'Exception during MarketStack request: {str(e)}'
                    })
            
            # If MarketStack succeeded, return early
            if backup_attempts and backup_attempts[-1].get('status') == 'success':
                return backup_attempts
            
            # Try Google Finance SECOND (web scraping - no API key needed, most reliable)
            backup_attempts.append({
                'api': 'Google Finance',
                'method': 'web_scraping',
                'status': 'attempting',
                'details': f'Fetching quote from Google Finance (web scraping) for {symbol}'
            })
            
            try:
                # Set a 3-second timeout for Google Finance
                import signal
                
                def timeout_handler(signum, frame):
                    raise TimeoutError("Google Finance request timed out")
                
                # Use signal for timeout on non-Windows systems, or try-except for Windows
                try:
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(3)  # 3 second timeout
                    quote = backup_fetcher.google_finance_client.get_quote(symbol)
                    signal.alarm(0)  # Cancel alarm
                except (AttributeError, OSError):
                    # Windows doesn't support SIGALRM, use basic timeout
                    quote = backup_fetcher.google_finance_client.get_quote(symbol)
                
                if quote and quote.get('price'):
                    backup_attempts[-1].update({
                        'status': 'success',
                        'price': float(quote['price']),
                        'company_name': quote.get('company_name', symbol),
                        'market_cap': quote.get('market_cap'),
                        'details': f'Successfully retrieved price {quote["price"]} from Google Finance web scraping'
                    })
                    return backup_attempts  # Success, return early
                else:
                    backup_attempts[-1].update({
                        'status': 'failed',
                        'error': 'No price data returned',
                        'details': 'Google Finance web scraping returned empty or invalid quote data'
                    })
            except TimeoutError:
                backup_attempts[-1].update({
                    'status': 'failed',
                    'error': 'Timeout after 3 seconds',
                    'details': 'Google Finance web scraping timed out'
                })
            except Exception as e:
                backup_attempts[-1].update({
                    'status': 'failed',
                    'error': str(e),
                    'details': f'Exception during Google Finance web scraping: {str(e)}'
                })
            
            # If Google Finance succeeded, return early
            if backup_attempts[-1].get('status') == 'success':
                return backup_attempts
            
            # Try other APIs in parallel with short timeouts
            import concurrent.futures
            
            def try_alpha_vantage():
                if not (backup_fetcher.alpha_vantage_client and backup_fetcher.alpha_vantage_client.api_key):
                    return None
                
                attempt = {
                    'api': 'Alpha Vantage',
                    'method': 'get_quote()',
                    'status': 'attempting',
                    'details': f'Fetching quote from Alpha Vantage for {symbol}'
                }
                
                try:
                    quote = backup_fetcher.alpha_vantage_client.get_quote(symbol)
                    if quote and quote.get('price'):
                        attempt.update({
                            'status': 'success',
                            'price': float(quote['price']),
                            'company_name': quote.get('company_name', symbol),
                            'market_cap': quote.get('market_cap'),
                            'details': f'Successfully retrieved price {quote["price"]} from Alpha Vantage'
                        })
                        return attempt, float(quote['price'])
                    else:
                        attempt.update({
                            'status': 'failed',
                            'error': 'No price data returned',
                            'details': 'Alpha Vantage returned empty or invalid quote data'
                        })
                except Exception as e:
                    attempt.update({
                        'status': 'failed',
                        'error': str(e),
                        'details': f'Exception during Alpha Vantage request: {str(e)}'
                    })
                
                return attempt, None
            
            def try_fmp():
                if not backup_fetcher.fmp_client.api_key:
                    return None
                
                attempt = {
                    'api': 'Financial Modeling Prep',
                    'method': 'get_quote()',
                    'status': 'attempting',
                    'details': f'Fetching quote from Financial Modeling Prep for {symbol}'
                }
                
                try:
                    quote = backup_fetcher.fmp_client.get_quote(symbol)
                    if quote and quote.get('price'):
                        attempt.update({
                            'status': 'success',
                            'price': float(quote['price']),
                            'company_name': quote.get('company_name', symbol),
                            'market_cap': quote.get('market_cap'),
                            'details': f'Successfully retrieved price {quote["price"]} from Financial Modeling Prep'
                        })
                        return attempt, float(quote['price'])
                    else:
                        attempt.update({
                            'status': 'failed',
                            'error': 'No price data returned',
                            'details': 'Financial Modeling Prep returned empty or invalid quote data'
                        })
                except Exception as e:
                    attempt.update({
                        'status': 'failed',
                        'error': str(e),
                        'details': f'Exception during Financial Modeling Prep request: {str(e)}'
                    })
                
                return attempt, None
            
            # Run remaining APIs in parallel with 2-second timeout each
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = []
                
                # Submit available APIs
                if backup_fetcher.alpha_vantage_client and backup_fetcher.alpha_vantage_client.api_key:
                    futures.append(executor.submit(try_alpha_vantage))
                
                if backup_fetcher.fmp_client.api_key:
                    futures.append(executor.submit(try_fmp))
                
                # Wait for results with timeout
                for future in concurrent.futures.as_completed(futures, timeout=3):
                    try:
                        result = future.result()
                        if result:
                            attempt, price = result
                            backup_attempts.append(attempt)
                            if price:  # Success
                                # Cancel remaining futures
                                for f in futures:
                                    f.cancel()
                                return backup_attempts
                    except Exception as e:
                        backup_attempts.append({
                            'api': 'Parallel API',
                            'method': 'concurrent_execution',
                            'status': 'failed',
                            'error': str(e),
                            'details': f'Exception during parallel API execution: {str(e)}'
                        })
            
            return backup_attempts
            
        except ImportError as e:
            backup_attempts.append({
                'api': 'Backup APIs',
                'method': 'import_backup_clients',
                'status': 'failed',
                'error': 'Import error',
                'details': f'Could not import backup clients: {str(e)}'
            })
            return backup_attempts
        except Exception as e:
            backup_attempts.append({
                'api': 'Backup APIs',
                'method': 'general_error',
                'status': 'failed',
                'error': str(e),
                'details': f'Unexpected error during backup API attempts: {str(e)}'
            })
            return backup_attempts

    def _build_successful_response(self, symbol: str, price: float, api_attempts: List[Dict], 
                                 company_name: str = None, market_cap: float = None) -> Dict:
        """Build successful response with all available data"""
        # Try to get additional company info from Yahoo Finance if not provided
        if not company_name:
            try:
                ticker = self.get_ticker(symbol)
                if ticker:
                    info = ticker.info
                    if info:
                        company_name = info.get('longName') or info.get('shortName') or symbol
                        if not market_cap:
                            market_cap = info.get('marketCap')
            except:
                pass
        
        # Compile success report
        successful_methods = [attempt['method'] for attempt in api_attempts if attempt.get('status') == 'success']
        successful_apis = list(set([attempt['api'] for attempt in api_attempts if attempt.get('status') == 'success']))
        
        result = {
            'price': price,
            'company_name': company_name or symbol,
            'market_cap': market_cap,
            'currency': 'USD',  # Default
            'symbol': symbol,
            'sector': None,
            'industry': None,
            'long_business_summary': '',
            'business_summary': '',
            'success': True,
            'error_detail': f"Successfully fetched data for {symbol} using: {', '.join(successful_apis)}",
            'api_attempts': api_attempts
        }
        
        logger.info(f"Successfully got quote for {symbol}: price={price}, APIs used: {', '.join(successful_apis)}")
        return result

    def _build_failure_response(self, symbol: str, api_attempts: List[Dict], exception_msg: str = None) -> Dict:
        """Build failure response with detailed error information"""
        # Compile detailed failure report
        failed_apis = list(set([attempt['api'] for attempt in api_attempts if attempt.get('status') == 'failed']))
        attempted_apis = list(set([attempt['api'] for attempt in api_attempts]))
        
        # Create a more user-friendly error message
        if not attempted_apis:
            error_detail = f"No price data sources were available for {symbol}"
        else:
            # Show which APIs were tried and their order
            api_order = []
            for attempt in api_attempts:
                api_name = attempt['api']
                if api_name not in api_order:
                    api_order.append(api_name)
            
            error_detail = f"Unable to fetch price for {symbol}. Tried {len(api_order)} data sources in order: {' → '.join(api_order)}"
            
            # Add specific failure reasons for key APIs
            key_failures = []
            for attempt in api_attempts:
                if attempt.get('status') == 'failed' and attempt['api'] in ['Google Finance', 'Yahoo Finance']:
                    error_reason = attempt.get('error', 'Unknown error')
                    key_failures.append(f"{attempt['api']}: {error_reason}")
            
            if key_failures:
                error_detail += f". Key failures: {'; '.join(key_failures)}"
        
        if exception_msg:
            error_detail += f". System error: {exception_msg}"
        
        # Provide helpful suggestions
        suggestions = []
        if symbol and len(symbol) > 5:
            suggestions.append("Try using just the ticker symbol (e.g., 'AAPL' instead of 'AAPL.US')")
        if '.' in symbol:
            suggestions.append("For international stocks, try the local ticker format")
        suggestions.append("Check if the ticker symbol is correct and the market is open")
        
        return {
            'error': f'Failed to get price data for {symbol}',
            'error_detail': error_detail,
            'suggestions': suggestions,
            'symbol': symbol,
            'api_attempts': api_attempts
        }
    
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

