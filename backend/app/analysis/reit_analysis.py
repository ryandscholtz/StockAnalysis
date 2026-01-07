"""
REIT-Specific Analysis
Analyzes REITs using real estate investment trust-specific metrics
"""
from dataclasses import dataclass
from typing import Optional
from app.data.data_fetcher import CompanyData
import numpy as np


@dataclass
class REITMetrics:
    """REIT-specific financial metrics"""
    funds_from_operations: Optional[float] = None  # FFO
    adjusted_funds_from_operations: Optional[float] = None  # AFFO
    ffo_per_share: Optional[float] = None
    affo_per_share: Optional[float] = None
    net_asset_value: Optional[float] = None  # NAV
    dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None
    occupancy_rate: Optional[float] = None


class REITAnalyzer:
    """Analyze REIT-specific metrics"""

    def __init__(self, company_data: CompanyData):
        self.company_data = company_data

    def calculate_ffo(self) -> Optional[float]:
        """Calculate Funds From Operations (FFO)"""
        # FFO = Net Income + Depreciation + Amortization - Gains from Sales of Property
        if not self.company_data.income_statement or not self.company_data.cashflow:
            return None

        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
        if not sorted_dates:
            return None

        income = self.company_data.income_statement[sorted_dates[0]]
        cf = self.company_data.cashflow.get(sorted_dates[0], {})

        if not isinstance(income, dict) or not isinstance(cf, dict):
            return None

        net_income = income.get('Net Income', 0) or 0
        depreciation = abs(cf.get('Depreciation', 0) or cf.get('Depreciation And Amortization', 0) or 0)

        # Gains from property sales (simplified - may not be available)
        gains = abs(income.get('Gain On Sale Of Property', 0) or 0)

        ffo = net_income + depreciation - gains
        return ffo

    def calculate_affo(self) -> Optional[float]:
        """Calculate Adjusted Funds From Operations (AFFO)"""
        # AFFO = FFO - Maintenance CapEx - Straight-line rent adjustments
        ffo = self.calculate_ffo()
        if ffo is None:
            return None

        if not self.company_data.cashflow:
            return ffo

        sorted_dates = sorted(self.company_data.cashflow.keys(), reverse=True)
        if not sorted_dates:
            return ffo

        cf = self.company_data.cashflow[sorted_dates[0]]
        if not isinstance(cf, dict):
            return ffo

        # Maintenance CapEx (simplified - use portion of total CapEx)
        capex = abs(cf.get('Capital Expenditures', 0) or 0)
        maintenance_capex = capex * 0.5  # Estimate 50% as maintenance

        affo = ffo - maintenance_capex
        return max(affo, 0.0)

    def calculate_nav(self) -> Optional[float]:
        """Calculate Net Asset Value (NAV) per share"""
        if not self.company_data.balance_sheet:
            return None

        sorted_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
        if not sorted_dates:
            return None

        balance = self.company_data.balance_sheet[sorted_dates[0]]
        if not isinstance(balance, dict):
            return None

        total_assets = balance.get('Total Assets', 0) or 0
        total_liabilities = balance.get('Total Liabilities', 0) or 0
        nav = total_assets - total_liabilities

        if self.company_data.shares_outstanding and self.company_data.shares_outstanding > 0:
            return nav / self.company_data.shares_outstanding

        return None

    def calculate_dividend_yield(self) -> Optional[float]:
        """Calculate Dividend Yield"""
        if not self.company_data.income_statement or not self.company_data.current_price:
            return None

        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
        if not sorted_dates:
            return None

        income = self.company_data.income_statement[sorted_dates[0]]
        if not isinstance(income, dict):
            return None

        # Dividends paid (from cash flow would be better, but use income statement proxy)
        dividends = abs(income.get('Dividends Paid', 0) or 0)

        if self.company_data.shares_outstanding and self.company_data.shares_outstanding > 0:
            dividend_per_share = dividends / self.company_data.shares_outstanding
            if self.company_data.current_price > 0:
                return (dividend_per_share / self.company_data.current_price) * 100

        return None

    def analyze(self) -> REITMetrics:
        """Perform REIT-specific analysis"""
        ffo = self.calculate_ffo()
        affo = self.calculate_affo()
        nav = self.calculate_nav()
        dividend_yield = self.calculate_dividend_yield()

        # Calculate per-share metrics
        ffo_per_share = None
        affo_per_share = None
        if self.company_data.shares_outstanding and self.company_data.shares_outstanding > 0:
            if ffo is not None:
                ffo_per_share = ffo / self.company_data.shares_outstanding
            if affo is not None:
                affo_per_share = affo / self.company_data.shares_outstanding

        # Calculate payout ratio (simplified)
        payout_ratio = None
        if affo is not None and affo > 0 and self.company_data.income_statement:
            sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
            if sorted_dates:
                income = self.company_data.income_statement[sorted_dates[0]]
                if isinstance(income, dict):
                    dividends = abs(income.get('Dividends Paid', 0) or 0)
                    payout_ratio = (dividends / affo) * 100 if affo > 0 else None

        return REITMetrics(
            funds_from_operations=ffo,
            adjusted_funds_from_operations=affo,
            ffo_per_share=ffo_per_share,
            affo_per_share=affo_per_share,
            net_asset_value=nav,
            dividend_yield=dividend_yield,
            payout_ratio=payout_ratio
        )
