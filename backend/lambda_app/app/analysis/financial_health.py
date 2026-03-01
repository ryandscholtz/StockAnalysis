"""
Financial Health Analysis
"""
from dataclasses import dataclass
from typing import List, Optional
from app.data.data_fetcher import CompanyData
from app.api.models import FinancialMetrics, FinancialHealth
import numpy as np
import math


class FinancialHealthAnalyzer:
    """Analyze financial health and calculate health score"""

    def __init__(self, company_data: CompanyData):
        self.company_data = company_data

    def calculate_liquidity_ratios(self) -> tuple[float, float]:
        """Calculate Current Ratio and Quick Ratio"""
        if not self.company_data.balance_sheet:
            return 0.0, 0.0

        sorted_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
        if not sorted_dates:
            return 0.0, 0.0

        statement = self.company_data.balance_sheet[sorted_dates[0]]
        if not isinstance(statement, dict):
            return 0.0, 0.0

        current_assets = statement.get('Total Current Assets', 0) or 0
        current_liabilities = statement.get('Total Current Liabilities', 0) or 0
        inventory = statement.get('Inventory', 0) or 0

        current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 0.0
        quick_ratio = (current_assets - inventory) / current_liabilities if current_liabilities > 0 else 0.0

        return current_ratio, quick_ratio

    def calculate_leverage_ratios(self) -> tuple[float, float]:
        """Calculate Debt-to-Equity and Debt-to-Assets"""
        if not self.company_data.balance_sheet:
            return 0.0, 0.0

        sorted_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
        if not sorted_dates:
            return 0.0, 0.0

        statement = self.company_data.balance_sheet[sorted_dates[0]]
        if not isinstance(statement, dict):
            return 0.0, 0.0

        total_debt = (
            statement.get('Total Debt', 0) or
            statement.get('Long Term Debt', 0) or
            0
        )
        total_equity = (
            statement.get('Total Stockholder Equity', 0) or
            statement.get('Stockholders Equity', 0) or
            0
        )
        total_assets = statement.get('Total Assets', 0) or 0

        debt_to_equity = total_debt / total_equity if total_equity > 0 else 0.0
        debt_to_assets = total_debt / total_assets if total_assets > 0 else 0.0

        return debt_to_equity, debt_to_assets

    def calculate_coverage_ratios(self) -> tuple[float, float]:
        """Calculate Interest Coverage and Debt Service Coverage"""
        if not self.company_data.income_statement or not self.company_data.cashflow:
            return 0.0, 0.0

        sorted_dates_income = sorted(self.company_data.income_statement.keys(), reverse=True)
        sorted_dates_cf = sorted(self.company_data.cashflow.keys(), reverse=True)

        if not sorted_dates_income:
            return 0.0, 0.0

        income_statement = self.company_data.income_statement[sorted_dates_income[0]]
        if not isinstance(income_statement, dict):
            return 0.0, 0.0

        ebit = (
            income_statement.get('EBIT', 0) or
            income_statement.get('Operating Income', 0) or
            0
        )
        interest_expense = abs(income_statement.get('Interest Expense', 0) or 0)

        interest_coverage = ebit / interest_expense if interest_expense > 0 else 999.0

        # Debt service coverage (simplified)
        debt_service_coverage = 0.0
        if sorted_dates_cf:
            cf_statement = self.company_data.cashflow[sorted_dates_cf[0]]
            if isinstance(cf_statement, dict):
                operating_cf = (
                    cf_statement.get('Operating Cash Flow', 0) or
                    cf_statement.get('Total Cash From Operating Activities', 0) or
                    0
                )
                if interest_expense > 0:
                    debt_service_coverage = operating_cf / interest_expense

        return interest_coverage, debt_service_coverage

    def calculate_profitability_ratios(self) -> tuple[float, float, float]:
        """Calculate ROE, ROIC, ROA (5-year averages)"""
        if not self.company_data.income_statement or not self.company_data.balance_sheet:
            return 0.0, 0.0, 0.0

        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)[:5]
        if not sorted_dates:
            return 0.0, 0.0, 0.0

        roe_values = []
        roic_values = []
        roa_values = []

        for date in sorted_dates:
            income = self.company_data.income_statement.get(date, {})
            balance = self.company_data.balance_sheet.get(date, {})

            if not isinstance(income, dict) or not isinstance(balance, dict):
                continue

            net_income = income.get('Net Income', 0) or 0
            equity = balance.get('Total Stockholder Equity', 0) or 0
            assets = balance.get('Total Assets', 0) or 0
            total_debt = balance.get('Total Debt', 0) or balance.get('Long Term Debt', 0) or 0

            # ROE
            if equity > 0:
                roe_values.append(net_income / equity)

            # ROA
            if assets > 0:
                roa_values.append(net_income / assets)

            # ROIC (simplified - NOPAT / (Debt + Equity))
            invested_capital = total_debt + equity
            if invested_capital > 0:
                # Estimate NOPAT as EBIT * (1 - tax_rate)
                ebit = income.get('EBIT', 0) or income.get('Operating Income', 0) or 0
                tax_rate = 0.21  # Default
                nopat = ebit * (1 - tax_rate)
                roic_values.append(nopat / invested_capital)

        roe = np.mean(roe_values) if roe_values else 0.0
        roic = np.mean(roic_values) if roic_values else 0.0
        roa = np.mean(roa_values) if roa_values else 0.0

        # Ensure all values are valid numbers (not NaN or inf)
        roe = 0.0 if (math.isnan(roe) or not math.isfinite(roe)) else roe
        roic = 0.0 if (math.isnan(roic) or not math.isfinite(roic)) else roic
        roa = 0.0 if (math.isnan(roa) or not math.isfinite(roa)) else roa

        return roe, roic, roa

    def analyze_cash_flow_trends(self) -> tuple[str, float]:
        """Analyze FCF trends and margin"""
        if not self.company_data.cashflow:
            return 'unknown', 0.0

        sorted_dates = sorted(self.company_data.cashflow.keys(), reverse=True)[:5]
        if not sorted_dates:
            return 'unknown', 0.0

        fcf_values = []
        revenues = []

        for date in sorted_dates:
            cf_statement = self.company_data.cashflow.get(date, {})
            income_statement = self.company_data.income_statement.get(date, {})

            if isinstance(cf_statement, dict):
                operating_cf = (
                    cf_statement.get('Operating Cash Flow', 0) or
                    cf_statement.get('Total Cash From Operating Activities', 0) or
                    0
                )
                capex = abs(cf_statement.get('Capital Expenditures', 0) or 0)
                fcf = operating_cf - capex
                fcf_values.append(fcf)

            if isinstance(income_statement, dict):
                revenue = income_statement.get('Total Revenue', 0) or income_statement.get('Revenue', 0) or 0
                revenues.append(revenue)

        # Determine trend
        if len(fcf_values) >= 3:
            recent_avg = np.mean(fcf_values[:3])
            older_avg = np.mean(fcf_values[-3:]) if len(fcf_values) >= 6 else fcf_values[-1]

            if recent_avg > older_avg * 1.1:
                trend = 'increasing'
            elif recent_avg < older_avg * 0.9:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'unknown'

        # Calculate FCF margin
        fcf_margin = 0.0
        if fcf_values and revenues:
            avg_fcf = np.mean(fcf_values)
            avg_revenue = np.mean(revenues)
            if avg_revenue > 0:
                fcf_margin = (avg_fcf / avg_revenue) * 100

        # Ensure fcf_margin is a valid number (not NaN or inf)
        if math.isnan(fcf_margin) or not math.isfinite(fcf_margin):
            fcf_margin = 0.0

        return trend, fcf_margin

    def analyze_earnings_consistency(self) -> float:
        """Calculate earnings consistency (coefficient of variation)"""
        if not self.company_data.income_statement:
            return 1.0  # High volatility if no data

        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)[:10]
        if len(sorted_dates) < 3:
            return 1.0

        earnings = []
        for date in sorted_dates:
            income = self.company_data.income_statement.get(date, {})
            if isinstance(income, dict):
                net_income = income.get('Net Income', 0) or 0
                if net_income != 0:
                    earnings.append(net_income)

        if len(earnings) < 3:
            return 1.0

        mean = np.mean(earnings)
        std_dev = np.std(earnings)

        if mean == 0:
            return 1.0

        coefficient_of_variation = abs(std_dev / mean)
        return coefficient_of_variation

    def calculate_health_score(self, metrics: FinancialMetrics,
                              fcf_trend: str, fcf_margin: float,
                              earnings_consistency: float) -> float:
        """Calculate overall financial health score (0-100)"""
        score = 0.0

        # Liquidity (20 points)
        if metrics.currentRatio > 1.5:
            score += 10.0
        elif metrics.currentRatio > 1.0:
            score += 5.0

        if metrics.quickRatio > 1.0:
            score += 10.0
        elif metrics.quickRatio > 0.5:
            score += 5.0

        # Leverage (25 points)
        if metrics.debtToEquity < 0.5:
            score += 15.0
        elif metrics.debtToEquity < 1.0:
            score += 7.0

        if metrics.interestCoverage > 5.0:
            score += 10.0
        elif metrics.interestCoverage > 2.0:
            score += 5.0

        # Profitability (30 points)
        if metrics.roe > 0.15:
            score += 10.0
        elif metrics.roe > 0.10:
            score += 5.0

        if metrics.roic > 0.12:
            score += 10.0
        elif metrics.roic > 0.08:
            score += 5.0

        if metrics.roa > 0.08:
            score += 10.0
        elif metrics.roa > 0.05:
            score += 5.0

        # Cash Flow (15 points)
        if fcf_trend == 'increasing':
            score += 10.0
        elif fcf_trend == 'stable':
            score += 5.0

        if fcf_margin > 10.0:
            score += 5.0
        elif fcf_margin > 5.0:
            score += 2.5

        # Consistency (10 points)
        if earnings_consistency < 0.3:
            score += 10.0
        elif earnings_consistency < 0.5:
            score += 5.0

        return min(score, 100.0)

    def analyze(self) -> FinancialHealth:
        """Perform comprehensive financial health analysis"""
        # Calculate all metrics
        current_ratio, quick_ratio = self.calculate_liquidity_ratios()
        debt_to_equity, debt_to_assets = self.calculate_leverage_ratios()
        interest_coverage, debt_service_coverage = self.calculate_coverage_ratios()
        roe, roic, roa = self.calculate_profitability_ratios()
        fcf_trend, fcf_margin = self.analyze_cash_flow_trends()
        earnings_consistency = self.analyze_earnings_consistency()

        # Create metrics object
        metrics = FinancialMetrics(
            debtToEquity=debt_to_equity,
            currentRatio=current_ratio,
            quickRatio=quick_ratio,
            interestCoverage=interest_coverage,
            roe=roe,
            roic=roic,
            roa=roa,
            fcfMargin=fcf_margin
        )

        # Calculate health score
        score = self.calculate_health_score(metrics, fcf_trend, fcf_margin, earnings_consistency)

        return FinancialHealth(
            score=score,
            metrics=metrics
        )
