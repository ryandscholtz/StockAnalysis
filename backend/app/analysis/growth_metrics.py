"""
Growth Metrics Calculator
Calculates revenue, earnings, and FCF growth rates
"""
from typing import Optional, Dict, List
from app.data.data_fetcher import CompanyData
import math


class GrowthMetricsCalculator:
    """Calculate growth rates for key financial metrics"""
    
    def __init__(self, company_data: CompanyData):
        self.company_data = company_data
    
    def calculate(self) -> Dict[str, Optional[float]]:
        """Calculate all growth metrics"""
        return {
            'revenueGrowth1Y': self._calculate_revenue_growth(1),
            'revenueGrowth3Y': self._calculate_revenue_growth(3),
            'revenueGrowth5Y': self._calculate_revenue_growth(5),
            'earningsGrowth1Y': self._calculate_earnings_growth(1),
            'earningsGrowth3Y': self._calculate_earnings_growth(3),
            'earningsGrowth5Y': self._calculate_earnings_growth(5),
            'fcfGrowth1Y': self._calculate_fcf_growth(1),
            'fcfGrowth3Y': self._calculate_fcf_growth(3),
            'fcfGrowth5Y': self._calculate_fcf_growth(5),
        }
    
    def _get_revenue_history(self) -> List[float]:
        """Extract revenue history from income statements"""
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
    
    def _get_earnings_history(self) -> List[float]:
        """Extract earnings (net income) history from income statements"""
        earnings_history = []
        
        if not self.company_data.income_statement:
            return earnings_history
        
        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
        
        for date in sorted_dates[:10]:
            statement = self.company_data.income_statement[date]
            if isinstance(statement, dict):
                # Try multiple net income field names
                net_income = (
                    statement.get('Net Income') or
                    statement.get('Net Income Common Stockholders') or
                    statement.get('Net Income From Continuing Operations') or
                    0
                )
                if net_income:  # Include negative earnings
                    earnings_history.append(float(net_income))
        
        return list(reversed(earnings_history))
    
    def _get_fcf_history(self) -> List[float]:
        """Extract free cash flow history from cash flow statements"""
        fcf_history = []
        
        if not self.company_data.cashflow:
            return fcf_history
        
        sorted_dates = sorted(self.company_data.cashflow.keys(), reverse=True)
        
        for date in sorted_dates[:10]:
            statement = self.company_data.cashflow[date]
            if isinstance(statement, dict):
                # Get operating cash flow
                operating_cf = (
                    statement.get('Operating Cash Flow') or
                    statement.get('Total Cash From Operating Activities') or
                    statement.get('OperatingCashFlow') or
                    0
                )
                
                # Get capital expenditures
                capex = abs(
                    statement.get('Capital Expenditures') or
                    statement.get('Capital Expenditure') or
                    statement.get('CapitalExpenditures') or
                    0
                )
                
                if operating_cf:
                    fcf = float(operating_cf) - capex
                    fcf_history.append(fcf)
        
        return list(reversed(fcf_history))
    
    def _calculate_revenue_growth(self, years: int) -> Optional[float]:
        """Calculate revenue growth rate over N years (CAGR)"""
        revenue_history = self._get_revenue_history()
        
        if len(revenue_history) < years + 1:
            return None
        
        # Get first and last values
        first_value = revenue_history[0]
        last_value = revenue_history[-1] if len(revenue_history) >= years + 1 else revenue_history[-(years + 1)]
        
        if first_value <= 0 or last_value <= 0:
            return None
        
        # Calculate CAGR: (End/Start)^(1/Years) - 1
        if years == 1:
            # Simple year-over-year growth
            if len(revenue_history) >= 2:
                prev_value = revenue_history[-2]
                if prev_value > 0:
                    return ((last_value - prev_value) / prev_value) * 100
        else:
            # CAGR
            if len(revenue_history) >= years + 1:
                start_value = revenue_history[-(years + 1)]
                if start_value > 0:
                    cagr = (math.pow(last_value / start_value, 1.0 / years) - 1) * 100
                    return cagr
        
        return None
    
    def _calculate_earnings_growth(self, years: int) -> Optional[float]:
        """Calculate earnings growth rate over N years (CAGR)"""
        earnings_history = self._get_earnings_history()
        
        if len(earnings_history) < years + 1:
            return None
        
        last_value = earnings_history[-1]
        
        if years == 1:
            # Simple year-over-year growth
            if len(earnings_history) >= 2:
                prev_value = earnings_history[-2]
                if prev_value != 0:
                    return ((last_value - prev_value) / abs(prev_value)) * 100
        else:
            # CAGR (handle negative values)
            if len(earnings_history) >= years + 1:
                start_value = earnings_history[-(years + 1)]
                if start_value != 0 and last_value != 0:
                    # If both are negative or both positive, calculate normally
                    if (start_value > 0 and last_value > 0) or (start_value < 0 and last_value < 0):
                        cagr = (math.pow(abs(last_value) / abs(start_value), 1.0 / years) - 1) * 100
                        if start_value < 0:
                            cagr = -cagr  # Maintain sign
                        return cagr
                    # If sign changed, return None (can't calculate meaningful CAGR)
        
        return None
    
    def _calculate_fcf_growth(self, years: int) -> Optional[float]:
        """Calculate FCF growth rate over N years (CAGR)"""
        fcf_history = self._get_fcf_history()
        
        if len(fcf_history) < years + 1:
            return None
        
        last_value = fcf_history[-1]
        
        if years == 1:
            # Simple year-over-year growth
            if len(fcf_history) >= 2:
                prev_value = fcf_history[-2]
                if prev_value != 0:
                    return ((last_value - prev_value) / abs(prev_value)) * 100
        else:
            # CAGR
            if len(fcf_history) >= years + 1:
                start_value = fcf_history[-(years + 1)]
                if start_value != 0:
                    # Handle negative values
                    if (start_value > 0 and last_value > 0) or (start_value < 0 and last_value < 0):
                        cagr = (math.pow(abs(last_value) / abs(start_value), 1.0 / years) - 1) * 100
                        if start_value < 0:
                            cagr = -cagr
                        return cagr
        
        return None

