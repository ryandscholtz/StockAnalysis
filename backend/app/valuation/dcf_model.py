"""
Discounted Cash Flow (DCF) Model
"""
from typing import Optional, Dict
from dataclasses import dataclass
from app.data.data_fetcher import CompanyData
import numpy as np


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
    
    def project_future_cash_flows(self, historical_fcf: list[float], wacc: float) -> tuple[list[float], float]:
        """
        Project future free cash flows
        Returns (projected_cash_flows, terminal_value)
        """
        if not historical_fcf:
            return [], 0.0
        
        # Calculate growth rate (average of historical)
        if len(historical_fcf) >= 2:
            growth_rates = []
            for i in range(1, len(historical_fcf)):
                if historical_fcf[i-1] > 0:
                    growth = (historical_fcf[i] - historical_fcf[i-1]) / abs(historical_fcf[i-1])
                    growth_rates.append(growth)
            
            avg_growth = np.mean(growth_rates) if growth_rates else 0.05
            # Cap growth at reasonable levels
            avg_growth = min(max(avg_growth, -0.1), 0.3)
        else:
            avg_growth = 0.05  # Default 5%
        
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

