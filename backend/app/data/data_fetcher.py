"""
Unified data fetching interface
"""
from typing import Optional, Dict
from dataclasses import dataclass, field
from app.data.api_client import YahooFinanceClient, FREDClient
from app.data.sec_edgar_client import SECEdgarClient, AlphaVantageClient
from app.data.data_agent import FinancialDataAgent
from app.data.backup_clients import BackupDataFetcher
import os
import logging

logger = logging.getLogger(__name__)


@dataclass
class CompanyData:
    """Container for company financial data"""
    ticker: str
    company_name: str
    current_price: float
    market_cap: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    shares_outstanding: Optional[float] = None
    beta: Optional[float] = None
    currency: Optional[str] = None  # Trading currency (e.g., 'USD', 'EUR', 'GBP')
    financial_currency: Optional[str] = None  # Currency used in financial statements
    
    # Financial statements (as dictionaries with dates as keys)
    income_statement: dict = field(default_factory=dict)
    balance_sheet: dict = field(default_factory=dict)
    cashflow: dict = field(default_factory=dict)
    
    # Historical data
    historical_prices: Optional[dict] = None


class DataFetcher:
    """Main data fetching class"""
    
    def __init__(self):
        self.yahoo_client = YahooFinanceClient()
        fred_api_key = os.getenv("FRED_API_KEY")
        self.fred_client = FREDClient(api_key=fred_api_key)
        self.sec_client = SECEdgarClient()
        alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        self.alpha_vantage_client = AlphaVantageClient(api_key=alpha_vantage_key) if alpha_vantage_key else None
        self.data_agent = FinancialDataAgent()
        self.backup_fetcher = BackupDataFetcher()  # Backup data sources
    
    async def fetch_company_data(self, ticker: str) -> Optional[CompanyData]:
        """
        Fetch all company data for a ticker
        Uses backup APIs (MarketStack, Alpha Vantage, FMP) FIRST, then falls back to Yahoo Finance
        MarketStack is prioritized as the primary backup source
        For international tickers (with exchange suffixes like .JO, .L, etc.), prioritizes Yahoo Finance
        """
        try:
            logger.info(f"Fetching data for ticker: {ticker} (using backup APIs first)")
            current_price = None
            info = {}
            yf_ticker = None
            
            # Check if this is an international ticker (has exchange suffix)
            exchange_suffixes = ['.JO', '.L', '.TO', '.PA', '.DE', '.HK', '.SS', '.SZ', '.T', '.AS', '.BR', '.MX', '.SA', '.SW', '.VI', '.ST', '.OL', '.CO', '.HE', '.IC', '.LS', '.MC', '.MI', '.NX', '.TA', '.TW', '.V', '.WA']
            is_international = any(ticker.upper().endswith(suffix) for suffix in exchange_suffixes)
            
            # For international tickers, backup APIs often don't support them, so try Yahoo Finance first
            if is_international:
                logger.info(f"International ticker detected ({ticker}), prioritizing Yahoo Finance...")
                yf_ticker = self.yahoo_client.get_ticker(ticker)
                if yf_ticker:
                    # Try to get price from Yahoo Finance first for international tickers
                    current_price = self.yahoo_client.get_current_price(yf_ticker)
                    if current_price:
                        logger.info(f"✓ Got price from Yahoo Finance for international ticker: {current_price}")
                        info = self.yahoo_client.get_company_info(yf_ticker)
                        if not info:
                            info = {'longName': ticker.upper(), 'shortName': ticker.upper()}
                    else:
                        # For international tickers, even if no price, keep yf_ticker for financial statements
                        # Only reset if we can't get any data at all
                        logger.warning(f"Yahoo Finance returned no price for {ticker}, but ticker exists. Will try to get financials anyway.")
                        # Don't reset yf_ticker - we might still be able to get financial statements
                        # Try to get at least company name from fast_info
                        try:
                            fast_info = yf_ticker.fast_info
                            if hasattr(fast_info, 'lastPrice') and fast_info.lastPrice:
                                current_price = float(fast_info.lastPrice)
                                logger.info(f"Got price from fast_info: {current_price}")
                                info = {'longName': ticker.upper(), 'shortName': ticker.upper()}
                        except:
                            pass
                else:
                    logger.warning(f"Could not create Yahoo Finance ticker for {ticker}, trying backup sources...")
            
            # PRIORITY 1: Try backup data sources (skip for international if Yahoo already worked)
            if not (is_international and current_price):
                logger.info(f"Trying backup data sources for {ticker}...")
                quote_data = self.backup_fetcher.get_quote_with_metrics(ticker)
                
                if quote_data and quote_data.get('price'):
                    current_price = float(quote_data['price'])
                    logger.info(f"✓ Got price from backup source: {current_price}")
                    # Extract market cap if available
                    market_cap = quote_data.get('market_cap')
                    backup_info = self.backup_fetcher.get_company_info(ticker)
                    if backup_info:
                        info = {
                            'longName': backup_info.get('companyName', ticker.upper()),
                            'shortName': backup_info.get('companyName', ticker.upper()),
                            'sector': backup_info.get('sector'),
                            'industry': backup_info.get('industry'),
                            'marketCap': market_cap
                        }
                    else:
                        info = {
                            'longName': ticker.upper(), 
                            'shortName': ticker.upper(),
                            'marketCap': market_cap
                        }
                else:
                    # Fallback to just getting price if quote_with_metrics fails
                    backup_price = self.backup_fetcher.get_current_price(ticker)
                    if backup_price:
                        current_price = backup_price
                        logger.info(f"✓ Got price from backup source (fallback): {current_price}")
                        backup_info = self.backup_fetcher.get_company_info(ticker)
                        if backup_info:
                            info = {
                                'longName': backup_info.get('companyName', ticker.upper()),
                                'shortName': backup_info.get('companyName', ticker.upper()),
                                'sector': backup_info.get('sector'),
                                'industry': backup_info.get('industry')
                            }
                        else:
                            info = {'longName': ticker.upper(), 'shortName': ticker.upper()}
            
            # PRIORITY 2: Fall back to Yahoo Finance if backup sources didn't provide price
            # (or if we haven't tried Yahoo Finance yet for international tickers)
            if not current_price or not yf_ticker:
                if not yf_ticker:
                    logger.warning(f"Backup sources failed for {ticker}, falling back to Yahoo Finance...")
                    yf_ticker = self.yahoo_client.get_ticker(ticker)
                
                if not yf_ticker:
                    logger.error(f"All data sources failed for {ticker} - backup sources and Yahoo Finance unavailable")
                    # For international tickers, try one more time with explicit error handling
                    if is_international:
                        logger.warning(f"Retrying Yahoo Finance for international ticker {ticker} with explicit error handling...")
                        try:
                            import yfinance as yf
                            test_ticker = yf.Ticker(ticker)
                            # Try to access a simple property to verify it works
                            try:
                                _ = test_ticker.history(period="1d", timeout=10)
                                yf_ticker = test_ticker
                                logger.info(f"Successfully created Yahoo Finance ticker on retry for {ticker}")
                            except Exception as e:
                                logger.error(f"Yahoo Finance ticker {ticker} exists but cannot fetch data: {e}")
                        except Exception as e:
                            logger.error(f"Could not create Yahoo Finance ticker for {ticker}: {e}")
                    
                    if not yf_ticker:
                        return None
                
                # Get price from Yahoo Finance
                current_price = self.yahoo_client.get_current_price(yf_ticker)
                
                if not current_price:
                    # Last resort: try to get most recent historical price directly from Yahoo
                    logger.warning(f"Could not get current price for {ticker}, trying historical price as fallback")
                    try:
                        hist = yf_ticker.history(period="1mo", timeout=15)
                        if not hist.empty and len(hist) > 0:
                            current_price = float(hist['Close'].iloc[-1])
                            logger.info(f"Using historical price as fallback: {current_price}")
                    except Exception as e:
                        error_str = str(e).lower()
                        if '429' in error_str or 'too many requests' in error_str:
                            logger.warning(f"Yahoo Finance rate limited for {ticker}")
                        else:
                            logger.warning(f"Failed to get historical price fallback: {e}")
                
                # If we still don't have a price, we can't create CompanyData - return None
                if not current_price:
                    logger.error(f"All data sources failed for {ticker} - no price available from any source")
                    return None
                
                # Get company info from Yahoo Finance
                info = self.yahoo_client.get_company_info(yf_ticker)
                if not info:
                    # Try backup sources for company info
                    logger.warning(f"No company info from Yahoo Finance for {ticker}, trying backup sources...")
                    backup_info = self.backup_fetcher.get_company_info(ticker)
                    if backup_info:
                        # Convert backup info to Yahoo Finance format
                        info = {
                            'longName': backup_info.get('companyName', ticker.upper()),
                            'shortName': backup_info.get('companyName', ticker.upper()),
                            'sector': backup_info.get('sector'),
                            'industry': backup_info.get('industry')
                        }
                    else:
                        logger.warning(f"No company info from backup sources for {ticker}, using minimal info")
                        # Create minimal info dict if we have price but no info
                        info = {'longName': ticker.upper(), 'shortName': ticker.upper()}
            else:
                # We got price from backup sources, but try to get yf_ticker for financial statements
                yf_ticker = self.yahoo_client.get_ticker(ticker)
            
            # Get financial statements - PRIORITY: Try Alpha Vantage FIRST, then Yahoo Finance
            financials = {
                'income_statement': {},
                'balance_sheet': {},
                'cashflow': {}
            }
            
            # PRIORITY 1: Try Alpha Vantage FIRST for financial statements
            if self.alpha_vantage_client:
                logger.info(f"Trying Alpha Vantage for financial statements for {ticker}...")
                av_income = self.alpha_vantage_client.get_income_statement(ticker)
                av_balance = self.alpha_vantage_client.get_balance_sheet(ticker)
                av_cashflow = self.alpha_vantage_client.get_cash_flow(ticker)
                
                # Convert Alpha Vantage format to our format
                if av_income and 'annualReports' in av_income:
                    av_data = self._convert_alpha_vantage_income(av_income)
                    if av_data:
                        financials['income_statement'].update(av_data)
                        logger.info(f"✓ Got income statement with {len(av_data)} periods from Alpha Vantage")
                
                if av_balance and 'annualReports' in av_balance:
                    av_data = self._convert_alpha_vantage_balance(av_balance)
                    if av_data:
                        financials['balance_sheet'].update(av_data)
                        logger.info(f"✓ Got balance sheet with {len(av_data)} periods from Alpha Vantage")
                
                if av_cashflow and 'annualReports' in av_cashflow:
                    av_data = self._convert_alpha_vantage_cashflow(av_cashflow)
                    if av_data:
                        financials['cashflow'].update(av_data)
                        logger.info(f"✓ Got cashflow with {len(av_data)} periods from Alpha Vantage")
            
            # PRIORITY 2: Supplement with Yahoo Finance if available and Alpha Vantage data is limited
            if yf_ticker:
                yf_financials = self.yahoo_client.get_financials(yf_ticker)
                
                # Only use Yahoo Finance data if Alpha Vantage didn't provide enough
                if not financials.get('income_statement') or len(financials.get('income_statement', {})) < 3:
                    if yf_financials.get('income_statement'):
                        financials['income_statement'].update(yf_financials['income_statement'])
                        logger.info(f"Supplemented income statement with Yahoo Finance data")
                
                if not financials.get('balance_sheet') or len(financials.get('balance_sheet', {})) < 2:
                    if yf_financials.get('balance_sheet'):
                        financials['balance_sheet'].update(yf_financials['balance_sheet'])
                        logger.info(f"Supplemented balance sheet with Yahoo Finance data")
                
                if not financials.get('cashflow') or len(financials.get('cashflow', {})) < 2:
                    if yf_financials.get('cashflow'):
                        financials['cashflow'].update(yf_financials['cashflow'])
                        logger.info(f"Supplemented cashflow with Yahoo Finance data")
            
            # Get historical prices (only if we have yf_ticker)
            hist_dict = None
            if yf_ticker:
                hist_prices = self.yahoo_client.get_historical_prices(yf_ticker)
                if hist_prices is not None and not hist_prices.empty:
                    hist_dict = hist_prices.to_dict('index')
            
            # Extract key metrics
            market_cap = info.get('marketCap')
            shares_outstanding = info.get('sharesOutstanding')
            if market_cap and shares_outstanding:
                # Calculate if missing
                if not shares_outstanding and market_cap and current_price:
                    shares_outstanding = market_cap / current_price
            
            # Extract currency information
            currency = info.get('currency') or info.get('financialCurrency') or 'USD'
            financial_currency = info.get('financialCurrency') or currency
            
            company_data = CompanyData(
                ticker=ticker.upper(),
                company_name=info.get('longName') or info.get('shortName') or ticker,
                current_price=current_price,
                market_cap=market_cap,
                sector=info.get('sector'),
                industry=info.get('industry'),
                shares_outstanding=shares_outstanding,
                beta=info.get('beta', 1.0),
                currency=currency,
                financial_currency=financial_currency,
                income_statement=financials.get('income_statement', {}),
                balance_sheet=financials.get('balance_sheet', {}),
                cashflow=financials.get('cashflow', {}),
                historical_prices=hist_dict
            )
            
            # Use agent to identify and supplement missing data
            missing = self.data_agent.identify_missing_data(company_data)
            
            if any(missing.values()):
                logger.info(f"Missing data detected for {ticker}: {missing}")
                supplemented = self.data_agent.supplement_missing_data(company_data, missing)
                
                # Merge supplemented data
                if supplemented.get('income_statement'):
                    # Convert Alpha Vantage format if needed
                    if isinstance(supplemented['income_statement'], list):
                        av_data = self._convert_alpha_vantage_income({'annualReports': supplemented['income_statement']})
                        if av_data:
                            company_data.income_statement.update(av_data)
                            logger.info(f"Agent supplemented income statement with {len(av_data)} periods")
                
                if supplemented.get('balance_sheet'):
                    if isinstance(supplemented['balance_sheet'], list):
                        av_data = self._convert_alpha_vantage_balance({'annualReports': supplemented['balance_sheet']})
                        if av_data:
                            company_data.balance_sheet.update(av_data)
                            logger.info(f"Agent supplemented balance sheet with {len(av_data)} periods")
                
                if supplemented.get('cashflow'):
                    if isinstance(supplemented['cashflow'], list):
                        av_data = self._convert_alpha_vantage_cashflow({'annualReports': supplemented['cashflow']})
                        if av_data:
                            company_data.cashflow.update(av_data)
                            logger.info(f"Agent supplemented cashflow with {len(av_data)} periods")
            
            return company_data
            
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")
            return None
    
    def get_risk_free_rate(self) -> float:
        """Get risk-free rate from FRED"""
        return self.fred_client.get_risk_free_rate()
    
    def _convert_alpha_vantage_income(self, av_data: Dict) -> Dict:
        """Convert Alpha Vantage income statement to our format"""
        try:
            result = {}
            annual_reports = av_data.get('annualReports', [])
            for report in annual_reports[:10]:  # Last 10 years
                fiscal_date = report.get('fiscalDateEnding', '')
                if fiscal_date:
                    result[fiscal_date] = {
                        'Total Revenue': float(report.get('totalRevenue', 0) or 0),
                        'Cost Of Revenue': float(report.get('costOfRevenue', 0) or 0),
                        'Gross Profit': float(report.get('grossProfit', 0) or 0),
                        'Operating Income': float(report.get('operatingIncome', 0) or 0),
                        'EBIT': float(report.get('operatingIncome', 0) or 0),
                        'Net Income': float(report.get('netIncome', 0) or 0),
                        'Income Before Tax': float(report.get('incomeBeforeTax', 0) or 0),
                        'Tax Provision': float(report.get('incomeTaxExpense', 0) or 0),
                    }
            return result
        except Exception as e:
            print(f"Error converting Alpha Vantage income: {e}")
            return {}
    
    def _convert_alpha_vantage_balance(self, av_data: Dict) -> Dict:
        """Convert Alpha Vantage balance sheet to our format"""
        try:
            result = {}
            annual_reports = av_data.get('annualReports', [])
            for report in annual_reports[:10]:
                fiscal_date = report.get('fiscalDateEnding', '')
                if fiscal_date:
                    result[fiscal_date] = {
                        'Total Assets': float(report.get('totalAssets', 0) or 0),
                        'Total Current Assets': float(report.get('totalCurrentAssets', 0) or 0),
                        'Cash And Cash Equivalents': float(report.get('cashAndCashEquivalentsAtCarryingValue', 0) or 0),
                        'Inventory': float(report.get('inventory', 0) or 0),
                        'Net Receivables': float(report.get('currentNetReceivables', 0) or 0),
                        'Total Liabilities': float(report.get('totalLiabilities', 0) or 0),
                        'Total Current Liabilities': float(report.get('totalCurrentLiabilities', 0) or 0),
                        'Total Debt': float(report.get('totalDebt', 0) or 0),
                        'Long Term Debt': float(report.get('longTermDebt', 0) or 0),
                        'Total Stockholder Equity': float(report.get('totalShareholderEquity', 0) or 0),
                    }
            return result
        except Exception as e:
            print(f"Error converting Alpha Vantage balance sheet: {e}")
            return {}
    
    def _convert_alpha_vantage_cashflow(self, av_data: Dict) -> Dict:
        """Convert Alpha Vantage cash flow to our format"""
        try:
            result = {}
            annual_reports = av_data.get('annualReports', [])
            for report in annual_reports[:10]:
                fiscal_date = report.get('fiscalDateEnding', '')
                if fiscal_date:
                    result[fiscal_date] = {
                        'Operating Cash Flow': float(report.get('operatingCashflow', 0) or 0),
                        'Total Cash From Operating Activities': float(report.get('operatingCashflow', 0) or 0),
                        'Capital Expenditures': float(report.get('capitalExpenditures', 0) or 0),
                        'Free Cash Flow': float(report.get('operatingCashflow', 0) or 0) - abs(float(report.get('capitalExpenditures', 0) or 0)),
                    }
            return result
        except Exception as e:
            print(f"Error converting Alpha Vantage cash flow: {e}")
            return {}

