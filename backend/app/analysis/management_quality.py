"""
Management Quality Assessment
"""
from dataclasses import dataclass
from typing import List
from app.data.data_fetcher import CompanyData
from app.api.models import ManagementQuality
import numpy as np


class ManagementQualityAnalyzer:
    """Analyze management quality"""

    def __init__(self, company_data: CompanyData):
        self.company_data = company_data

    def assess_capital_allocation(self) -> float:
        """Assess capital allocation (0-30 points)"""
        score = 0.0

        # ROIC performance (would need industry average for comparison)
        # For now, use absolute ROIC
        if self.company_data.income_statement and self.company_data.balance_sheet:
            sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)[:5]
            roic_values = []

            for date in sorted_dates:
                income = self.company_data.income_statement.get(date, {})
                balance = self.company_data.balance_sheet.get(date, {})

                if isinstance(income, dict) and isinstance(balance, dict):
                    ebit = income.get('EBIT', 0) or income.get('Operating Income', 0) or 0
                    total_debt = balance.get('Total Debt', 0) or balance.get('Long Term Debt', 0) or 0
                    equity = balance.get('Total Stockholder Equity', 0) or 0
                    invested_capital = total_debt + equity

                    if invested_capital > 0:
                        tax_rate = 0.21
                        nopat = ebit * (1 - tax_rate)
                        roic = nopat / invested_capital
                        roic_values.append(roic)

            if roic_values:
                avg_roic = np.mean(roic_values)
                # Assume industry average is 10%, so >20% is 2x
                if avg_roic > 0.20:
                    score += 15.0
                elif avg_roic > 0.15:
                    score += 10.0
                elif avg_roic > 0.10:
                    score += 5.0

        # Share buybacks and dividends (simplified - would need cash flow analysis)
        score += 10.0  # Neutral assumption

        # Dividend policy (simplified)
        score += 5.0  # Stable assumption

        return min(score, 30.0)

    def assess_financial_discipline(self) -> float:
        """Assess financial discipline (0-25 points)"""
        score = 0.0

        # Debt management
        if self.company_data.balance_sheet:
            sorted_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
            if sorted_dates:
                balance = self.company_data.balance_sheet[sorted_dates[0]]
                if isinstance(balance, dict):
                    debt = balance.get('Total Debt', 0) or balance.get('Long Term Debt', 0) or 0
                    equity = balance.get('Total Stockholder Equity', 0) or 0

                    if equity > 0:
                        debt_to_equity = debt / equity
                        if debt_to_equity < 0.3:
                            score += 10.0  # Conservative
                        elif debt_to_equity < 0.7:
                            score += 5.0  # Moderate

        # Cash management
        if self.company_data.balance_sheet:
            sorted_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
            if sorted_dates:
                balance = self.company_data.balance_sheet[sorted_dates[0]]
                if isinstance(balance, dict):
                    cash = balance.get('Cash And Cash Equivalents', 0) or balance.get('Cash', 0) or 0
                    total_assets = balance.get('Total Assets', 0) or 0

                    if total_assets > 0:
                        cash_ratio = cash / total_assets
                        if cash_ratio > 0.15:
                            score += 8.0  # Strong
                        elif cash_ratio > 0.05:
                            score += 5.0  # Adequate

        # Earnings quality (simplified)
        score += 7.0  # Assume high

        return min(score, 25.0)

    def assess_transparency(self) -> float:
        """Assess transparency (0-20 points)"""
        # This would require analysis of financial reporting quality
        # For now, assume standard transparency
        return 15.0  # Standard assumption

    def assess_track_record(self) -> float:
        """Assess management track record (0-25 points)"""
        score = 0.0

        # Revenue growth
        if self.company_data.income_statement and len(self.company_data.income_statement) >= 3:
            sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
            revenues = []

            for date in sorted_dates[:5]:
                income = self.company_data.income_statement.get(date, {})
                if isinstance(income, dict):
                    revenue = income.get('Total Revenue', 0) or income.get('Revenue', 0) or 0
                    if revenue > 0:
                        revenues.append(revenue)

            if len(revenues) >= 3:
                # Check if consistently growing
                growth_rates = []
                for i in range(1, len(revenues)):
                    if revenues[i-1] > 0:
                        growth = (revenues[i] - revenues[i-1]) / revenues[i-1]
                        growth_rates.append(growth)

                if growth_rates:
                    avg_growth = np.mean(growth_rates)
                    if avg_growth > 0.05 and all(g > 0 for g in growth_rates):
                        score += 10.0  # Consistent growth
                    elif avg_growth > 0:
                        score += 5.0  # Volatile

        # Profitability trends
        if self.company_data.income_statement:
            sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)[:5]
            net_incomes = []

            for date in sorted_dates:
                income = self.company_data.income_statement.get(date, {})
                if isinstance(income, dict):
                    net_income = income.get('Net Income', 0) or 0
                    if net_income != 0:
                        net_incomes.append(net_income)

            if len(net_incomes) >= 3:
                recent_avg = np.mean(net_incomes[:3])
                older_avg = np.mean(net_incomes[-3:]) if len(net_incomes) >= 6 else net_incomes[-1]

                if recent_avg > older_avg * 1.1:
                    score += 8.0  # Improving
                elif recent_avg >= older_avg * 0.9:
                    score += 5.0  # Stable

        # Stock performance (would need market comparison)
        score += 7.0  # Assume matched market

        return min(score, 25.0)

    def identify_strengths_weaknesses(self, scores: dict) -> tuple[List[str], List[str]]:
        """Identify management strengths and weaknesses"""
        strengths = []
        weaknesses = []

        if scores.get('capital_allocation', 0) >= 20:
            strengths.append('Strong capital allocation')
        elif scores.get('capital_allocation', 0) < 10:
            weaknesses.append('Poor capital allocation')

        if scores.get('financial_discipline', 0) >= 18:
            strengths.append('Financial discipline')
        elif scores.get('financial_discipline', 0) < 12:
            weaknesses.append('Lack of financial discipline')

        if scores.get('track_record', 0) >= 18:
            strengths.append('Strong track record')
        elif scores.get('track_record', 0) < 12:
            weaknesses.append('Weak track record')

        return strengths, weaknesses

    def analyze(self) -> ManagementQuality:
        """Perform comprehensive management quality analysis"""
        capital_allocation = self.assess_capital_allocation()
        financial_discipline = self.assess_financial_discipline()
        transparency = self.assess_transparency()
        track_record = self.assess_track_record()

        # Calculate total score
        total_score = capital_allocation + financial_discipline + transparency + track_record

        # Normalize to 0-100
        management_score = min(total_score, 100.0)

        # Identify strengths and weaknesses
        scores = {
            'capital_allocation': capital_allocation,
            'financial_discipline': financial_discipline,
            'transparency': transparency,
            'track_record': track_record
        }
        strengths, weaknesses = self.identify_strengths_weaknesses(scores)

        return ManagementQuality(
            score=management_score,
            strengths=strengths,
            weaknesses=weaknesses
        )
