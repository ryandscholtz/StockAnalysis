"""
Price Ratios Calculator
Calculates P/E, P/B, P/S, P/FCF, and EV/EBITDA ratios
"""
from typing import Optional
from app.data.data_fetcher import CompanyData
import math


class PriceRatiosCalculator:
    """Calculate price-to-X valuation ratios"""
    
    def __init__(self, company_data: CompanyData):
        self.company_data = company_data
    
    def calculate(self) -> dict:
        """Calculate all price ratios"""
        return {
            'priceToEarnings': self._calculate_pe_ratio(),
            'priceToBook': self._calculate_pb_ratio(),
            'priceToSales': self._calculate_ps_ratio(),
            'priceToFCF': self._calculate_pfcf_ratio(),
            'enterpriseValueToEBITDA': self._calculate_ev_ebitda_ratio(),
        }
    
    def _get_latest_net_income(self) -> Optional[float]:
        """Get most recent net income from income statement"""
        if not self.company_data.income_statement:
            return None
        
        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
        
        for date in sorted_dates[:1]:  # Most recent
            statement = self.company_data.income_statement[date]
            if isinstance(statement, dict):
                net_income = (
                    statement.get('Net Income') or
                    statement.get('Net Income Common Stockholders') or
                    statement.get('Net Income From Continuing Operations') or
                    None
                )
                if net_income is not None:
                    return float(net_income)
        
        return None
    
    def _get_latest_revenue(self) -> Optional[float]:
        """Get most recent revenue from income statement"""
        if not self.company_data.income_statement:
            return None
        
        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
        
        for date in sorted_dates[:1]:
            statement = self.company_data.income_statement[date]
            if isinstance(statement, dict):
                revenue = (
                    statement.get('Total Revenue') or
                    statement.get('Revenue') or
                    statement.get('Net Sales') or
                    statement.get('Sales') or
                    None
                )
                if revenue is not None:
                    return float(revenue)
        
        return None
    
    def _get_latest_fcf(self) -> Optional[float]:
        """Get most recent free cash flow"""
        if not self.company_data.cashflow:
            return None
        
        sorted_dates = sorted(self.company_data.cashflow.keys(), reverse=True)
        
        for date in sorted_dates[:1]:
            statement = self.company_data.cashflow[date]
            if isinstance(statement, dict):
                operating_cf = (
                    statement.get('Operating Cash Flow') or
                    statement.get('Total Cash From Operating Activities') or
                    statement.get('OperatingCashFlow') or
                    0
                )
                
                capex = abs(
                    statement.get('Capital Expenditures') or
                    statement.get('Capital Expenditure') or
                    statement.get('CapitalExpenditures') or
                    0
                )
                
                if operating_cf:
                    return float(operating_cf) - capex
        
        return None
    
    def _get_latest_book_value(self) -> Optional[float]:
        """Get most recent book value (shareholders' equity)"""
        if not self.company_data.balance_sheet:
            return None
        
        sorted_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
        
        for date in sorted_dates[:1]:
            statement = self.company_data.balance_sheet[date]
            if isinstance(statement, dict):
                equity = (
                    statement.get('Total Stockholder Equity') or
                    statement.get('Stockholders Equity') or
                    statement.get('Shareholders Equity') or
                    statement.get('Total Equity') or
                    None
                )
                if equity is not None:
                    return float(equity)
        
        return None
    
    def _get_latest_ebitda(self) -> Optional[float]:
        """Get most recent EBITDA"""
        if not self.company_data.income_statement:
            return None
        
        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
        
        for date in sorted_dates[:1]:
            statement = self.company_data.income_statement[date]
            if isinstance(statement, dict):
                # Try to get EBITDA directly
                ebitda = statement.get('EBITDA') or statement.get('EBIT') or None
                
                if ebitda is not None:
                    return float(ebitda)
                
                # Calculate from components if available
                operating_income = (
                    statement.get('Operating Income') or
                    statement.get('EBIT') or
                    None
                )
                
                if operating_income is not None:
                    # Approximate EBITDA = Operating Income + Depreciation & Amortization
                    # If we have D&A, add it; otherwise use Operating Income as proxy
                    da = (
                        statement.get('Depreciation And Amortization') or
                        statement.get('Depreciation') or
                        0
                    )
                    return float(operating_income) + float(da)
        
        return None
    
    def _normalize_price(self, price: float) -> float:
        """Normalize price based on currency (handle cents vs base currency)"""
        currency = (self.company_data.currency or '').upper()
        ticker = (self.company_data.ticker or '').upper()
        
        # Explicit subunit currencies
        subunit_currencies = ['ZAC', 'ZARC', 'GBX', 'GBPX']
        if currency in subunit_currencies:
            return price / 100.0
        
        # Check if currency ends with 'C' or 'X' (subunit indicator)
        if currency.endswith('C') or currency.endswith('X'):
            return price / 100.0
        
        # For South African stocks (.JO ticker) with ZAR currency
        # Yahoo Finance often returns prices in cents even though currency is "ZAR"
        if ticker.endswith('.JO') and currency == 'ZAR':
            # South African stocks: if price > 10, likely in cents
            # Normal ZAR stock prices are typically 0.01 to 1000 ZAR
            # But Yahoo often returns them as cents (so 207 ZAc = 2.07 ZAR)
            if price > 10:
                normalized = price / 100.0
                # Verify normalization makes sense (price should be reasonable)
                if 0.01 <= normalized <= 1000:
                    return normalized
        
        # For ZAR currency in general: if price seems unusually high, check if it's cents
        if currency == 'ZAR' and price > 50:
            # Check if dividing by 100 gives a more reasonable price
            # Most stock prices are between 0.01 and 1000 in base currency
            normalized = price / 100.0
            if 0.01 <= normalized <= 1000:
                return normalized
        
        return price
    
    def _calculate_pe_ratio(self) -> Optional[float]:
        """Calculate Price-to-Earnings ratio"""
        if not self.company_data.current_price or not self.company_data.shares_outstanding:
            return None
        
        net_income = self._get_latest_net_income()
        if net_income is None or net_income <= 0:
            return None
        
        # Normalize price (handle cents/subunits)
        normalized_price = self._normalize_price(self.company_data.current_price)
        
        # Earnings per share
        eps = net_income / self.company_data.shares_outstanding
        
        if eps <= 0:
            return None
        
        # P/E = Price / EPS
        pe_ratio = normalized_price / eps
        
        return pe_ratio if math.isfinite(pe_ratio) else None
    
    def _calculate_pb_ratio(self) -> Optional[float]:
        """Calculate Price-to-Book ratio"""
        if not self.company_data.current_price or not self.company_data.shares_outstanding:
            return None
        
        book_value = self._get_latest_book_value()
        if book_value is None or book_value <= 0:
            return None
        
        # Normalize price (handle cents/subunits)
        normalized_price = self._normalize_price(self.company_data.current_price)
        
        # Book value per share
        bvps = book_value / self.company_data.shares_outstanding
        
        if bvps <= 0:
            return None
        
        # P/B = Price / Book Value per Share
        pb_ratio = normalized_price / bvps
        
        return pb_ratio if math.isfinite(pb_ratio) else None
    
    def _calculate_ps_ratio(self) -> Optional[float]:
        """Calculate Price-to-Sales ratio"""
        if not self.company_data.current_price or not self.company_data.shares_outstanding:
            return None
        
        revenue = self._get_latest_revenue()
        if revenue is None or revenue <= 0:
            return None
        
        # Normalize price (handle cents/subunits)
        normalized_price = self._normalize_price(self.company_data.current_price)
        
        # Sales per share
        sps = revenue / self.company_data.shares_outstanding
        
        if sps <= 0:
            return None
        
        # P/S = Price / Sales per Share
        ps_ratio = normalized_price / sps
        
        return ps_ratio if math.isfinite(ps_ratio) else None
    
    def _calculate_pfcf_ratio(self) -> Optional[float]:
        """Calculate Price-to-Free Cash Flow ratio"""
        if not self.company_data.current_price or not self.company_data.shares_outstanding:
            return None
        
        fcf = self._get_latest_fcf()
        if fcf is None or fcf <= 0:
            return None
        
        # Normalize price (handle cents/subunits)
        normalized_price = self._normalize_price(self.company_data.current_price)
        
        # FCF per share
        fcfps = fcf / self.company_data.shares_outstanding
        
        if fcfps <= 0:
            return None
        
        # P/FCF = Price / FCF per Share
        pfcf_ratio = normalized_price / fcfps
        
        return pfcf_ratio if math.isfinite(pfcf_ratio) else None
    
    def _calculate_ev_ebitda_ratio(self) -> Optional[float]:
        """Calculate Enterprise Value to EBITDA ratio"""
        ebitda = self._get_latest_ebitda()
        if ebitda is None or ebitda <= 0:
            return None
        
        # Enterprise Value = Market Cap + Debt - Cash
        market_cap = self.company_data.market_cap
        if not market_cap:
            if self.company_data.current_price and self.company_data.shares_outstanding:
                # Normalize price before calculating market cap
                normalized_price = self._normalize_price(self.company_data.current_price)
                market_cap = normalized_price * self.company_data.shares_outstanding
            else:
                return None
        else:
            # If market cap is provided, check if it needs normalization
            # Market cap from yfinance should already be in base currency, but let's verify
            # For now, assume provided market_cap is correct
            pass
        
        # Get debt and cash from balance sheet
        debt = 0
        cash = 0
        
        if self.company_data.balance_sheet:
            sorted_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
            for date in sorted_dates[:1]:
                statement = self.company_data.balance_sheet[date]
                if isinstance(statement, dict):
                    debt = (
                        statement.get('Total Debt') or
                        statement.get('Long Term Debt') or
                        0
                    )
                    cash = (
                        statement.get('Cash And Cash Equivalents') or
                        statement.get('Cash') or
                        0
                    )
                    break
        
        enterprise_value = market_cap + debt - cash
        
        if enterprise_value <= 0 or ebitda <= 0:
            return None
        
        ev_ebitda = enterprise_value / ebitda
        
        return ev_ebitda if math.isfinite(ev_ebitda) else None

