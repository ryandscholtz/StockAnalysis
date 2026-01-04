"""
Bank-Specific Analysis
Analyzes banks using financial services-specific metrics
"""
from dataclasses import dataclass
from typing import Optional
from app.data.data_fetcher import CompanyData
import numpy as np


@dataclass
class BankMetrics:
    """Bank-specific financial metrics"""
    net_interest_margin: float  # NIM
    return_on_equity: float  # ROE
    return_on_assets: float  # ROA
    tier_1_capital_ratio: Optional[float] = None  # Tier 1 capital / Risk-weighted assets
    loan_loss_provision_ratio: Optional[float] = None  # Loan loss provisions / Total loans
    efficiency_ratio: Optional[float] = None  # Non-interest expense / Revenue
    loan_to_deposit_ratio: Optional[float] = None  # Total loans / Total deposits
    non_performing_loans_ratio: Optional[float] = None  # NPL / Total loans


class BankAnalyzer:
    """Analyze bank-specific metrics"""
    
    def __init__(self, company_data: CompanyData):
        self.company_data = company_data
    
    def calculate_net_interest_margin(self) -> float:
        """Calculate Net Interest Margin (NIM)"""
        if not self.company_data.income_statement:
            return 0.0
        
        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
        if not sorted_dates:
            return 0.0
        
        income = self.company_data.income_statement[sorted_dates[0]]
        if not isinstance(income, dict):
            return 0.0
        
        # For banks, interest income and interest expense are key
        interest_income = income.get('Interest Income', 0) or income.get('Total Interest Income', 0) or 0
        interest_expense = abs(income.get('Interest Expense', 0) or 0)
        net_interest_income = interest_income - interest_expense
        
        # Average earning assets (simplified - use total assets as proxy)
        if self.company_data.balance_sheet:
            balance = self.company_data.balance_sheet.get(sorted_dates[0], {})
            if isinstance(balance, dict):
                earning_assets = balance.get('Total Assets', 0) or 0
                if earning_assets > 0:
                    return (net_interest_income / earning_assets) * 100
        
        return 0.0
    
    def calculate_efficiency_ratio(self) -> Optional[float]:
        """Calculate Efficiency Ratio (non-interest expense / revenue)"""
        if not self.company_data.income_statement:
            return None
        
        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
        if not sorted_dates:
            return None
        
        income = self.company_data.income_statement[sorted_dates[0]]
        if not isinstance(income, dict):
            return None
        
        non_interest_expense = abs(income.get('Non Interest Expense', 0) or 
                                   income.get('Operating Expense', 0) or 0)
        total_revenue = income.get('Total Revenue', 0) or income.get('Revenue', 0) or 0
        
        if total_revenue > 0:
            return (non_interest_expense / total_revenue) * 100
        
        return None
    
    def calculate_loan_to_deposit_ratio(self) -> Optional[float]:
        """Calculate Loan-to-Deposit Ratio"""
        if not self.company_data.balance_sheet:
            return None
        
        sorted_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
        if not sorted_dates:
            return None
        
        balance = self.company_data.balance_sheet[sorted_dates[0]]
        if not isinstance(balance, dict):
            return None
        
        total_loans = balance.get('Loans', 0) or balance.get('Total Loans', 0) or 0
        total_deposits = balance.get('Deposits', 0) or balance.get('Total Deposits', 0) or 0
        
        if total_deposits > 0:
            return (total_loans / total_deposits) * 100
        
        return None
    
    def analyze(self) -> BankMetrics:
        """Perform bank-specific analysis"""
        nim = self.calculate_net_interest_margin()
        efficiency = self.calculate_efficiency_ratio()
        ldr = self.calculate_loan_to_deposit_ratio()
        
        # Calculate ROE and ROA (from financial health analyzer)
        roe = 0.0
        roa = 0.0
        if self.company_data.income_statement and self.company_data.balance_sheet:
            sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)[:5]
            roe_values = []
            roa_values = []
            
            for date in sorted_dates:
                income = self.company_data.income_statement.get(date, {})
                balance = self.company_data.balance_sheet.get(date, {})
                
                if isinstance(income, dict) and isinstance(balance, dict):
                    net_income = income.get('Net Income', 0) or 0
                    equity = balance.get('Total Stockholder Equity', 0) or 0
                    assets = balance.get('Total Assets', 0) or 0
                    
                    if equity > 0:
                        roe_values.append(net_income / equity)
                    if assets > 0:
                        roa_values.append(net_income / assets)
            
            roe = np.mean(roe_values) if roe_values else 0.0
            roa = np.mean(roa_values) if roa_values else 0.0
        
        return BankMetrics(
            net_interest_margin=nim,
            return_on_equity=roe,
            return_on_assets=roa,
            efficiency_ratio=efficiency,
            loan_to_deposit_ratio=ldr
        )

