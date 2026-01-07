"""
Insurance-Specific Analysis
Analyzes insurance companies using insurance-specific metrics
"""
from dataclasses import dataclass
from typing import Optional
from app.data.data_fetcher import CompanyData
import numpy as np


@dataclass
class InsuranceMetrics:
    """Insurance-specific financial metrics"""
    combined_ratio: Optional[float] = None  # Loss ratio + Expense ratio
    loss_ratio: Optional[float] = None  # Incurred losses / Earned premiums
    expense_ratio: Optional[float] = None  # Underwriting expenses / Written premiums
    return_on_equity: float
    return_on_assets: float
    reserve_adequacy: Optional[float] = None  # Reserves / Net premiums earned
    investment_yield: Optional[float] = None  # Investment income / Invested assets


class InsuranceAnalyzer:
    """Analyze insurance-specific metrics"""

    def __init__(self, company_data: CompanyData):
        self.company_data = company_data

    def calculate_loss_ratio(self) -> Optional[float]:
        """Calculate Loss Ratio (Incurred losses / Earned premiums)"""
        if not self.company_data.income_statement:
            return None

        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
        if not sorted_dates:
            return None

        income = self.company_data.income_statement[sorted_dates[0]]
        if not isinstance(income, dict):
            return None

        # Insurance-specific line items
        incurred_losses = abs(income.get('Incurred Losses', 0) or
                            income.get('Losses And Loss Adjustment Expenses', 0) or 0)
        earned_premiums = income.get('Earned Premiums', 0) or income.get('Net Premiums Earned', 0) or 0

        if earned_premiums > 0:
            return (incurred_losses / earned_premiums) * 100

        return None

    def calculate_expense_ratio(self) -> Optional[float]:
        """Calculate Expense Ratio (Underwriting expenses / Written premiums)"""
        if not self.company_data.income_statement:
            return None

        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
        if not sorted_dates:
            return None

        income = self.company_data.income_statement[sorted_dates[0]]
        if not isinstance(income, dict):
            return None

        underwriting_expenses = abs(income.get('Underwriting Expenses', 0) or
                                   income.get('Acquisition Costs', 0) or 0)
        written_premiums = income.get('Written Premiums', 0) or income.get('Net Premiums Written', 0) or 0

        if written_premiums > 0:
            return (underwriting_expenses / written_premiums) * 100

        return None

    def calculate_combined_ratio(self) -> Optional[float]:
        """Calculate Combined Ratio (Loss Ratio + Expense Ratio)"""
        loss_ratio = self.calculate_loss_ratio()
        expense_ratio = self.calculate_expense_ratio()

        if loss_ratio is not None and expense_ratio is not None:
            return loss_ratio + expense_ratio

        return None

    def calculate_reserve_adequacy(self) -> Optional[float]:
        """Calculate Reserve Adequacy (Reserves / Net premiums earned)"""
        if not self.company_data.balance_sheet or not self.company_data.income_statement:
            return None

        sorted_bs_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
        sorted_is_dates = sorted(self.company_data.income_statement.keys(), reverse=True)

        if not sorted_bs_dates or not sorted_is_dates:
            return None

        balance = self.company_data.balance_sheet[sorted_bs_dates[0]]
        income = self.company_data.income_statement[sorted_is_dates[0]]

        if not isinstance(balance, dict) or not isinstance(income, dict):
            return None

        reserves = balance.get('Reserves', 0) or balance.get('Loss Reserves', 0) or 0
        earned_premiums = income.get('Earned Premiums', 0) or income.get('Net Premiums Earned', 0) or 0

        if earned_premiums > 0:
            return (reserves / earned_premiums) * 100

        return None

    def calculate_investment_yield(self) -> Optional[float]:
        """Calculate Investment Yield (Investment income / Invested assets)"""
        if not self.company_data.income_statement or not self.company_data.balance_sheet:
            return None

        sorted_is_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
        sorted_bs_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)

        if not sorted_is_dates or not sorted_bs_dates:
            return None

        income = self.company_data.income_statement[sorted_is_dates[0]]
        balance = self.company_data.balance_sheet[sorted_bs_dates[0]]

        if not isinstance(income, dict) or not isinstance(balance, dict):
            return None

        investment_income = income.get('Investment Income', 0) or income.get('Net Investment Income', 0) or 0
        invested_assets = balance.get('Invested Assets', 0) or balance.get('Total Investments', 0) or 0

        if invested_assets > 0:
            return (investment_income / invested_assets) * 100

        return None

    def analyze(self) -> InsuranceMetrics:
        """Perform insurance-specific analysis"""
        loss_ratio = self.calculate_loss_ratio()
        expense_ratio = self.calculate_expense_ratio()
        combined_ratio = self.calculate_combined_ratio()
        reserve_adequacy = self.calculate_reserve_adequacy()
        investment_yield = self.calculate_investment_yield()

        # Calculate ROE and ROA
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

        return InsuranceMetrics(
            combined_ratio=combined_ratio,
            loss_ratio=loss_ratio,
            expense_ratio=expense_ratio,
            return_on_equity=roe,
            return_on_assets=roa,
            reserve_adequacy=reserve_adequacy,
            investment_yield=investment_yield
        )
