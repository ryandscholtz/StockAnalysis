"""
Unified data fetching interface
"""
from typing import Optional, Dict
from dataclasses import dataclass, field
from app.data.api_client import YahooFinanceClient, FREDClient
from app.data.sec_edgar_client import SECEdgarClient, AlphaVantageClient
from app.data.data_agent import FinancialDataAgent
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
    
    async def fetch_company_data(self, ticker: str) -> Optional[CompanyData]:
        """
        Fetch all company data for a ticker
        """
        try:
            logger.info(f"Fetching data for ticker: {ticker}")
            yf_ticker = self.yahoo_client.get_ticker(ticker)
            if not yf_ticker:
                logger.warning(f"Failed to get yfinance ticker object for {ticker}")
                return None
            
            # Get price first (tries fast_info and history which are less rate-limited)
            current_price = self.yahoo_client.get_current_price(yf_ticker)
            
            if not current_price:
                # Last resort: try to get most recent historical price directly
                logger.warning(f"Could not get current price for {ticker}, trying historical price as fallback")
                try:
                    hist = yf_ticker.history(period="1mo", timeout=15)
                    if not hist.empty and len(hist) > 0:
                        current_price = float(hist['Close'].iloc[-1])
                        logger.info(f"Using historical price as fallback: {current_price}")
                    else:
                        logger.error(f"Could not get any price data for {ticker}")
                        return None
                except Exception as e:
                    error_str = str(e).lower()
                    if '429' in error_str or 'too many requests' in error_str:
                        logger.error(f"Rate limited - please wait 5-10 minutes before trying again")
                    else:
                        logger.error(f"Failed to get historical price fallback: {e}")
                    return None
            
            # Get company info (may be rate-limited, but we already have price)
            info = self.yahoo_client.get_company_info(yf_ticker)
            if not info:
                logger.warning(f"No company info returned for {ticker}, but we have price: {current_price}")
                # Create minimal info dict if we have price but no info
                info = {'longName': ticker.upper(), 'shortName': ticker.upper()}
            
            # Get financial statements - try multiple sources
            financials = self.yahoo_client.get_financials(yf_ticker)
            
            # If yfinance data is limited, try Alpha Vantage
            if self.alpha_vantage_client and (not financials.get('income_statement') or 
                len(financials.get('income_statement', {})) < 3):
                logger.info(f"Limited yfinance data for {ticker}, trying Alpha Vantage...")
                av_income = self.alpha_vantage_client.get_income_statement(ticker)
                av_balance = self.alpha_vantage_client.get_balance_sheet(ticker)
                av_cashflow = self.alpha_vantage_client.get_cash_flow(ticker)
                
                # Convert Alpha Vantage format to our format
                if av_income and 'annualReports' in av_income:
                    av_data = self._convert_alpha_vantage_income(av_income)
                    if av_data:
                        financials['income_statement'].update(av_data)
                        logger.info(f"Supplemented income statement with {len(av_data)} periods from Alpha Vantage")
                
                if av_balance and 'annualReports' in av_balance:
                    av_data = self._convert_alpha_vantage_balance(av_balance)
                    if av_data:
                        financials['balance_sheet'].update(av_data)
                        logger.info(f"Supplemented balance sheet with {len(av_data)} periods from Alpha Vantage")
                
                if av_cashflow and 'annualReports' in av_cashflow:
                    av_data = self._convert_alpha_vantage_cashflow(av_cashflow)
                    if av_data:
                        financials['cashflow'].update(av_data)
                        logger.info(f"Supplemented cashflow with {len(av_data)} periods from Alpha Vantage")
            
            # Get historical prices
            hist_prices = self.yahoo_client.get_historical_prices(yf_ticker)
            hist_dict = None
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

