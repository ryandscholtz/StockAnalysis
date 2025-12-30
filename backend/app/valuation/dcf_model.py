"""
Discounted Cash Flow (DCF) Model
"""
from typing import Optional, Dict
from dataclasses import dataclass
from app.data.data_fetcher import CompanyData
import numpy as np
import math
import logging

logger = logging.getLogger(__name__)


@dataclass
class DCFResult:
    """Result of DCF calculation"""
    fair_value_per_share: float
    enterprise_value: float
    equity_value: float
    wacc: float
    terminal_value: float
    pv_cash_flows: float


class DCFModel:
    """Discounted Cash Flow valuation model"""
    
    def __init__(self, company_data: CompanyData, risk_free_rate: float = 0.04):
        self.company_data = company_data
        self.risk_free_rate = risk_free_rate
        self.equity_risk_premium = 0.06  # 6% default
        self.terminal_growth_rate = 0.025  # 2.5% default
        self.forecast_period = 5  # 5 years
    
    def calculate_wacc(self) -> float:
        """Calculate Weighted Average Cost of Capital"""
        # Get beta (default to 1.0)
        beta = self.company_data.beta or 1.0
        
        # Cost of equity
        cost_of_equity = self.risk_free_rate + (beta * self.equity_risk_premium)
        
        # For simplicity, assume cost of debt = risk-free rate + 2%
        # In reality, would get from financial statements
        cost_of_debt = self.risk_free_rate + 0.02
        tax_rate = 0.21  # Default corporate tax rate
        
        # Get market values (simplified - would need actual debt data)
        # For now, estimate from balance sheet if available
        market_cap = self.company_data.market_cap
        if not market_cap:
            # Estimate from price and shares
            if self.company_data.current_price and self.company_data.shares_outstanding:
                market_cap = self.company_data.current_price * self.company_data.shares_outstanding
            else:
                # Can't calculate WACC without market cap
                return cost_of_equity
        
        # Estimate debt from balance sheet
        total_debt = 0
        if self.company_data.balance_sheet:
            # Look for debt items in balance sheet
            for date, statement in self.company_data.balance_sheet.items():
                if isinstance(statement, dict):
                    # Common debt line items
                    debt_items = [
                        statement.get('Total Debt', 0),
                        statement.get('Long Term Debt', 0),
                        statement.get('Short Term Debt', 0),
                        statement.get('Total Liabilities', 0) * 0.3  # Estimate 30% as debt
                    ]
                    total_debt = max([d for d in debt_items if d > 0], default=0)
                    break
        
        total_value = market_cap + total_debt
        
        if total_value == 0:
            return cost_of_equity
        
        # Calculate WACC
        equity_weight = market_cap / total_value
        debt_weight = total_debt / total_value
        
        wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt * (1 - tax_rate))
        
        return wacc
    
    def extract_free_cash_flow(self) -> list[float]:
        """Extract historical free cash flows"""
        fcf_history = []
        
        if not self.company_data.cashflow:
            print("Warning: No cashflow data available")
            return fcf_history
        
        # Sort by date (most recent first typically)
        sorted_dates = sorted(self.company_data.cashflow.keys(), reverse=True)
        print(f"Found {len(sorted_dates)} cashflow periods")
        
        for date in sorted_dates[:10]:  # Last 10 years max
            statement = self.company_data.cashflow[date]
            if isinstance(statement, dict):
                # Try multiple field name variations
                operating_cf = (
                    statement.get('Operating Cash Flow', 0) or 
                    statement.get('Total Cash From Operating Activities', 0) or
                    statement.get('OperatingCashFlow', 0) or
                    statement.get('operatingCashflow', 0) or
                    0
                )
                
                capex = abs(
                    statement.get('Capital Expenditures', 0) or 
                    statement.get('Capital Expenditure', 0) or
                    statement.get('CapitalExpenditures', 0) or
                    statement.get('capitalExpenditures', 0) or
                    0
                )
                
                if operating_cf:
                    fcf = operating_cf - capex
                    print(f"  {date}: OCF={operating_cf:,.0f}, CapEx={capex:,.0f}, FCF={fcf:,.0f}")
                    # Include all FCF values (positive and negative) for better analysis
                    fcf_history.append(fcf)
                else:
                    print(f"  {date}: No operating cash flow found. Available keys: {list(statement.keys())[:10]}")
        
        print(f"Extracted {len(fcf_history)} FCF values")
        return list(reversed(fcf_history))  # Oldest to newest
    
    def _classify_company_for_growth_cap(self) -> str:
        """
        Classify company for growth rate caps based on sector/industry
        Returns: 'high_growth', 'cyclical', or 'mature'
        """
        sector = (self.company_data.sector or '').lower()
        industry = (self.company_data.industry or '').lower()
        
        # High-growth sectors (tech, biotech)
        high_growth_keywords = [
            'technology', 'software', 'internet', 'biotechnology', 'biotech',
            'pharmaceutical', 'semiconductor', 'semiconductors', 'tech',
            'information technology', 'healthcare technology', 'cloud',
            'saas', 'ai', 'artificial intelligence', 'machine learning'
        ]
        
        # Cyclical/industrial sectors
        cyclical_keywords = [
            'industrial', 'manufacturing', 'automotive', 'construction',
            'materials', 'metals', 'mining', 'steel', 'chemical',
            'energy', 'oil', 'gas', 'petroleum', 'cyclical'
        ]
        
        # Mature/utility sectors
        mature_keywords = [
            'utility', 'utilities', 'telecommunications', 'telecom',
            'consumer staples', 'staples', 'food', 'beverage',
            'tobacco', 'retail', 'banking', 'financial services',
            'real estate', 'reit'
        ]
        
        # Check sector
        if any(keyword in sector for keyword in high_growth_keywords):
            return 'high_growth'
        if any(keyword in sector for keyword in cyclical_keywords):
            return 'cyclical'
        if any(keyword in sector for keyword in mature_keywords):
            return 'mature'
        
        # Check industry if sector didn't match
        if any(keyword in industry for keyword in high_growth_keywords):
            return 'high_growth'
        if any(keyword in industry for keyword in cyclical_keywords):
            return 'cyclical'
        if any(keyword in industry for keyword in mature_keywords):
            return 'mature'
        
        # Default to mature if unknown
        return 'mature'
    
    def _calculate_historical_cagr(self, values: list[float], years: int = None) -> Optional[float]:
        """
        Calculate CAGR from historical values
        Uses longest available period (5-10 years) if years not specified
        Returns CAGR as decimal (e.g., 0.15 for 15%)
        """
        if not values or len(values) < 2:
            return None
        
        # Use longest available period (up to 10 years)
        if years is None:
            years = min(len(values) - 1, 10)
            years = max(years, 5)  # Prefer at least 5 years
        
        if len(values) < years + 1:
            # Use what we have
            years = len(values) - 1
        
        if years < 1:
            return None
        
        start_value = values[0]
        end_value = values[-1]
        
        # Both must be positive for meaningful CAGR
        if start_value <= 0 or end_value <= 0:
            return None
        
        # Calculate CAGR: (End/Start)^(1/Years) - 1
        try:
            cagr = math.pow(end_value / start_value, 1.0 / years) - 1
            return cagr
        except (ValueError, ZeroDivisionError):
            return None
    
    def _get_revenue_history(self) -> list[float]:
        """Extract revenue history from income statements (oldest to newest)"""
        revenue_history = []
        
        if not self.company_data.income_statement:
            return revenue_history
        
        # Sort dates (most recent first typically)
        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
        
        for date in sorted_dates[:10]:  # Last 10 years
            statement = self.company_data.income_statement[date]
            if isinstance(statement, dict):
                # Try multiple revenue field names
                revenue = (
                    statement.get('Total Revenue') or
                    statement.get('Revenue') or
                    statement.get('Net Sales') or
                    statement.get('Sales') or
                    0
                )
                if revenue and revenue > 0:
                    revenue_history.append(float(revenue))
        
        return list(reversed(revenue_history))  # Oldest to newest
    
    def _calculate_growth_rate(self) -> float:
        """
        Calculate growth rate using improved method:
        1. Calculate historical revenue CAGR (5-10 years)
        2. Calculate historical FCF CAGR (same period)
        3. Take the LOWER of the two values
        4. Apply caps based on company classification
        """
        # Get revenue history
        revenue_history = self._get_revenue_history()
        revenue_cagr = None
        if len(revenue_history) >= 2:
            revenue_cagr = self._calculate_historical_cagr(revenue_history)
        
        # Get FCF history (already extracted, but need to get it again for consistency)
        fcf_history = self.extract_free_cash_flow()
        fcf_cagr = None
        if len(fcf_history) >= 2:
            fcf_cagr = self._calculate_historical_cagr(fcf_history)
        
        # Take the lower of the two (more conservative)
        growth_rate = None
        if revenue_cagr is not None and fcf_cagr is not None:
            growth_rate = min(revenue_cagr, fcf_cagr)
            logger.info(f"Revenue CAGR: {revenue_cagr*100:.2f}%, FCF CAGR: {fcf_cagr*100:.2f}%, Using lower: {growth_rate*100:.2f}%")
        elif revenue_cagr is not None:
            growth_rate = revenue_cagr
            logger.info(f"Using Revenue CAGR: {growth_rate*100:.2f}% (FCF CAGR not available)")
        elif fcf_cagr is not None:
            growth_rate = fcf_cagr
            logger.info(f"Using FCF CAGR: {growth_rate*100:.2f}% (Revenue CAGR not available)")
        
        # If we couldn't calculate CAGR, fall back to simple average
        if growth_rate is None:
            if len(fcf_history) >= 2:
                growth_rates = []
                for i in range(1, len(fcf_history)):
                    if fcf_history[i-1] > 0:
                        growth = (fcf_history[i] - fcf_history[i-1]) / abs(fcf_history[i-1])
                        growth_rates.append(growth)
                
                if growth_rates:
                    growth_rate = np.mean(growth_rates)
                    logger.info(f"Fallback: Using average FCF growth rate: {growth_rate*100:.2f}%")
                else:
                    growth_rate = 0.05  # Default 5%
                    logger.warning("No growth data available, using default 5%")
            else:
                growth_rate = 0.05  # Default 5%
                logger.warning("Insufficient data for CAGR, using default 5%")
        
        # Apply caps based on company classification
        company_type = self._classify_company_for_growth_cap()
        if company_type == 'high_growth':
            max_growth = 0.15  # 15% max
        elif company_type == 'cyclical':
            max_growth = 0.10  # 10% max
        else:  # mature
            max_growth = 0.05  # 5% max
        
        # Apply cap
        if growth_rate > max_growth:
            logger.info(f"Growth rate {growth_rate*100:.2f}% capped at {max_growth*100:.2f}% for {company_type} company")
            growth_rate = max_growth
        
        # Also apply minimum floor (prevent extreme negative growth)
        growth_rate = max(growth_rate, -0.10)  # -10% minimum
        
        logger.info(f"Final growth rate: {growth_rate*100:.2f}% (company type: {company_type})")
        return growth_rate
    
    def project_future_cash_flows(self, historical_fcf: list[float], wacc: float) -> tuple[list[float], float]:
        """
        Project future free cash flows
        Returns (projected_cash_flows, terminal_value)
        """
        if not historical_fcf:
            return [], 0.0
        
        # Calculate growth rate using improved method
        avg_growth = self._calculate_growth_rate()
        
        # Start with most recent FCF
        base_fcf = historical_fcf[-1]
        
        # Project cash flows with declining growth
        projected_cf = []
        current_fcf = base_fcf
        
        for year in range(1, self.forecast_period + 1):
            # Growth rate declines to terminal rate
            growth_rate = avg_growth - ((avg_growth - self.terminal_growth_rate) * (year - 1) / self.forecast_period)
            current_fcf = current_fcf * (1 + growth_rate)
            projected_cf.append(current_fcf)
        
        # Calculate terminal value
        final_fcf = projected_cf[-1]
        terminal_fcf = final_fcf * (1 + self.terminal_growth_rate)
        terminal_value = terminal_fcf / (wacc - self.terminal_growth_rate)
        
        return projected_cf, terminal_value
    
    def discount_cash_flows(self, cash_flows: list[float], wacc: float) -> float:
        """Discount cash flows to present value"""
        pv_sum = 0.0
        for year, cf in enumerate(cash_flows, start=1):
            pv = cf / ((1 + wacc) ** year)
            pv_sum += pv
        return pv_sum
    
    def calculate(self) -> DCFResult:
        """Calculate DCF fair value"""
        # Calculate WACC
        wacc = self.calculate_wacc()
        
        # Extract historical FCF
        historical_fcf = self.extract_free_cash_flow()
        
        if not historical_fcf:
            # Try to estimate FCF from earnings if available
            print("No FCF data, attempting to estimate from earnings...")
            estimated_fcf = self._estimate_fcf_from_earnings()
            if estimated_fcf:
                historical_fcf = estimated_fcf
                print(f"Estimated {len(historical_fcf)} FCF periods from earnings")
            else:
                print("Warning: Cannot calculate DCF - no FCF or earnings data")
                return DCFResult(
                    fair_value_per_share=0.0,
                    enterprise_value=0.0,
                    equity_value=0.0,
                    wacc=wacc,
                    terminal_value=0.0,
                    pv_cash_flows=0.0
                )
        
        # Project future cash flows
        projected_cf, terminal_value = self.project_future_cash_flows(historical_fcf, wacc)
        
        # Discount projected cash flows
        pv_cash_flows = self.discount_cash_flows(projected_cf, wacc)
        
        # Discount terminal value
        pv_terminal = terminal_value / ((1 + wacc) ** self.forecast_period)
        
        # Calculate enterprise value
        enterprise_value = pv_cash_flows + pv_terminal
        
        # Calculate equity value (subtract net debt)
        # Estimate net debt from balance sheet
        net_debt = 0
        if self.company_data.balance_sheet:
            for date, statement in self.company_data.balance_sheet.items():
                if isinstance(statement, dict):
                    total_debt = statement.get('Total Debt', 0) or statement.get('Long Term Debt', 0) or 0
                    cash = statement.get('Cash And Cash Equivalents', 0) or statement.get('Cash', 0) or 0
                    net_debt = total_debt - cash
                    break
        
        equity_value = enterprise_value - net_debt
        
        # Calculate per share
        shares = self.company_data.shares_outstanding
        if not shares or shares <= 0:
            fair_value_per_share = 0.0
        else:
            fair_value_per_share = equity_value / shares
        
        return DCFResult(
            fair_value_per_share=max(fair_value_per_share, 0.0),
            enterprise_value=enterprise_value,
            equity_value=equity_value,
            wacc=wacc,
            terminal_value=terminal_value,
            pv_cash_flows=pv_cash_flows
        )
    
    def _estimate_fcf_from_earnings(self) -> list[float]:
        """Estimate FCF from net income when cash flow data is unavailable"""
        estimated_fcf = []
        
        if not self.company_data.income_statement:
            return estimated_fcf
        
        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
        
        for date in sorted_dates[:10]:
            statement = self.company_data.income_statement[date]
            if isinstance(statement, dict):
                # Try to get net income
                net_income = (
                    statement.get('Net Income', 0) or
                    statement.get('NetIncome', 0) or
                    statement.get('netIncome', 0) or
                    statement.get('Net Income Common Stockholders', 0) or
                    0
                )
                
                if net_income:
                    # Estimate FCF as ~70% of net income (rough approximation)
                    estimated_fcf.append(net_income * 0.7)
        
        return list(reversed(estimated_fcf)) if estimated_fcf else []

