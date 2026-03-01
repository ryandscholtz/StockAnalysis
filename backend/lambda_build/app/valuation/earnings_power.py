"""
Earnings Power Value (EPV) Model
"""
from typing import Optional
from dataclasses import dataclass
from app.data.data_fetcher import CompanyData
import numpy as np
import math


@dataclass
class EPVResult:
    """Result of EPV calculation"""
    fair_value_per_share: float
    earnings_power_value: float
    normalized_earnings: float
    capitalization_rate: float


class EarningsPowerValue:
    """Earnings Power Value valuation model"""

    def __init__(self, company_data: CompanyData, risk_free_rate: float = 0.04):
        self.company_data = company_data
        self.risk_free_rate = risk_free_rate

    def normalize_earnings(self) -> float:
        """Calculate normalized earnings over 5-10 years"""
        import logging
        logger = logging.getLogger(__name__)

        earnings_history = []

        if not self.company_data.income_statement:
            logger.warning("EPV: No income statement data available")
            return 0.0

        # Check if data structure is inverted (line items as keys, dates as nested keys)
        # yfinance sometimes returns data as {line_item: {date: value}} instead of {date: {line_item: value}}
        first_key = next(iter(self.company_data.income_statement.keys()))
        first_value = self.company_data.income_statement[first_key]

        # Detect structure: if first value is a dict and its keys look like dates, it's normal structure
        # If first key looks like a line item (contains words like "Income", "Revenue", etc.), it's inverted
        is_inverted = False
        if isinstance(first_value, dict):
            # Check if keys look like dates (contain numbers that could be years)
            sample_nested_keys = list(first_value.keys())[:3]
            looks_like_dates = any(
                any(char.isdigit() for char in str(k)) and len(str(k)) >= 4
                for k in sample_nested_keys
            )
            if not looks_like_dates:
                # Might be inverted - check if first key looks like a line item
                first_key_str = str(first_key).lower()
                if any(term in first_key_str for term in ['income', 'revenue', 'expense', 'earnings', 'profit']):
                    is_inverted = True
                    logger.info(f"EPV: Detected inverted data structure (line items as keys)")

        if is_inverted:
            # Data structure: {line_item: {date: value}}
            # Find net income line item first
            net_income_line_item = None
            for line_item_key in self.company_data.income_statement.keys():
                line_item_lower = str(line_item_key).lower()
                if any(term in line_item_lower for term in ['net income', 'netincome', 'net_income']):
                    if 'per share' not in line_item_lower and 'diluted' not in line_item_lower:
                        net_income_line_item = line_item_key
                        logger.info(f"EPV: Found net income line item: {line_item_key}")
                        break

            if net_income_line_item:
                line_item_data = self.company_data.income_statement[net_income_line_item]
                if isinstance(line_item_data, dict):
                    # Get all date values
                    for date_key, value in line_item_data.items():
                        if value is not None:
                            try:
                                net_income = float(value)
                                # Check for nan and inf values
                                if not (math.isnan(net_income) or math.isinf(net_income)) and net_income != 0:
                                    earnings_history.append(net_income)
                                    logger.debug(f"EPV: Found net income for {date_key}: {net_income}")
                            except (ValueError, TypeError):
                                continue
        else:
            # Normal structure: {date: {line_item: value}}
            sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)
            logger.info(f"EPV: Found {len(sorted_dates)} income statement periods (normal structure)")

            # Show sample of available keys for debugging
            if sorted_dates:
                sample_statement = self.company_data.income_statement[sorted_dates[0]]
                if isinstance(sample_statement, dict):
                    sample_keys = list(sample_statement.keys())[:15]
                    logger.info(f"EPV: Sample keys from first period: {sample_keys}")

            for date in sorted_dates[:10]:  # Last 10 years
                statement = self.company_data.income_statement[date]
                if isinstance(statement, dict):
                    # Try multiple possible keys for net income (case-insensitive search)
                    net_income = None

                    # First, try exact matches
                    for key in [
                        'Net Income',
                        'Net Income Common Stockholders',
                        'Net Income From Continuing Operations',
                        'netIncome',
                        'netIncomeCommonStockholders',
                        'netIncomeFromContinuingOperations',
                        'NetIncome',
                        'NetIncomeCommonStockholders',
                        'NetIncomeFromContinuingOperations'
                    ]:
                        value = statement.get(key)
                        if value is not None:
                            try:
                                net_income = float(value)
                                # Check for nan and inf values
                                if not (math.isnan(net_income) or math.isinf(net_income)) and net_income != 0:
                                    logger.debug(f"EPV: Found via exact match ({key}) for {date}: {net_income}")
                                    break
                            except (ValueError, TypeError):
                                continue

                    # If not found, try case-insensitive search
                    if net_income is None:
                        for key, value in statement.items():
                            if value is not None:
                                key_lower = str(key).lower()
                                if any(term in key_lower for term in ['net income', 'netincome', 'net_income']):
                                    # Exclude items that are clearly not net income
                                    if 'per share' not in key_lower and 'diluted' not in key_lower:
                                        try:
                                            net_income = float(value)
                                            # Check for nan and inf values
                                            if not (math.isnan(net_income) or math.isinf(net_income)) and net_income != 0:
                                                logger.debug(f"EPV: Found via case-insensitive ({key}) for {date}: {net_income}")
                                                break
                                        except (ValueError, TypeError):
                                            continue

                    if net_income is not None and net_income != 0:
                        earnings_history.append(net_income)
                    else:
                        logger.debug(f"EPV: No net income found for {date}. Available keys: {list(statement.keys())[:10]}")

        if not earnings_history:
            logger.warning(f"EPV: No valid earnings found. Total periods checked: {len(self.company_data.income_statement)}")
            if not is_inverted and self.company_data.income_statement:
                first_key = next(iter(self.company_data.income_statement.keys()))
                first_value = self.company_data.income_statement[first_key]
                if isinstance(first_value, dict):
                    sample_keys = list(first_value.keys())[:20]
                    logger.warning(f"EPV: Available keys in first period: {sample_keys}")
            return 0.0

        # Filter out any remaining nan/inf values (safety check)
        earnings_history = [e for e in earnings_history if not (math.isnan(e) or math.isinf(e))]

        if not earnings_history:
            logger.warning(f"EPV: No valid earnings after filtering nan/inf values")
            return 0.0

        # Calculate average (normalized earnings)
        normalized = np.mean(earnings_history)

        # Check if result is nan (shouldn't happen after filtering, but safety check)
        if math.isnan(normalized) or math.isinf(normalized):
            logger.warning(f"EPV: Normalized earnings is nan/inf, returning 0")
            return 0.0

        # Remove outliers (earnings more than 3 std devs from mean)
        if len(earnings_history) > 3:
            std_dev = np.std(earnings_history)
            mean = np.mean(earnings_history)
            if not (math.isnan(std_dev) or math.isnan(mean)):
                filtered = [e for e in earnings_history if abs(e - mean) <= 3 * std_dev]
                if filtered:
                    normalized = np.mean(filtered)
                    # Final check
                    if math.isnan(normalized) or math.isinf(normalized):
                        normalized = mean  # Fall back to original mean

        logger.info(f"EPV: normalized earnings = {normalized:,.0f} (from {len(earnings_history)} periods)")
        return normalized

    def calculate_effective_tax_rate(self) -> float:
        """Calculate average effective tax rate"""
        tax_rates = []

        if not self.company_data.income_statement:
            return 0.21  # Default corporate tax rate

        sorted_dates = sorted(self.company_data.income_statement.keys(), reverse=True)

        for date in sorted_dates[:5]:  # Last 5 years
            statement = self.company_data.income_statement[date]
            if isinstance(statement, dict):
                income_before_tax = (
                    statement.get('Income Before Tax', 0) or
                    statement.get('Earnings Before Tax', 0) or
                    0
                )
                tax_expense = abs(statement.get('Tax Provision', 0) or statement.get('Tax Expense', 0) or 0)

                if income_before_tax > 0 and tax_expense > 0:
                    tax_rate = tax_expense / income_before_tax
                    tax_rates.append(tax_rate)

        if tax_rates:
            return np.mean(tax_rates)

        return 0.21  # Default

    def determine_capitalization_rate(self, business_quality_score: float = 50.0) -> float:
        """
        Determine capitalization rate based on risk
        Higher quality = lower cap rate (higher valuation)
        """
        # Base capitalization rate
        base_cap_rate = 0.10  # 10% default

        # Adjust based on business quality
        # Quality score 0-100, higher is better
        if business_quality_score >= 80:
            quality_adjustment = -0.02  # Lower cap rate for high quality
        elif business_quality_score >= 60:
            quality_adjustment = -0.01
        elif business_quality_score < 40:
            quality_adjustment = 0.02  # Higher cap rate for low quality
        else:
            quality_adjustment = 0.0

        cap_rate = base_cap_rate + quality_adjustment

        # Ensure reasonable bounds (6% to 15%)
        cap_rate = max(0.06, min(0.15, cap_rate))

        return cap_rate

    def calculate_excess_assets(self) -> float:
        """Calculate excess cash and non-operating assets"""
        excess_assets = 0.0

        if not self.company_data.balance_sheet:
            return excess_assets

        # Get most recent balance sheet
        sorted_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
        if not sorted_dates:
            return excess_assets

        statement = self.company_data.balance_sheet[sorted_dates[0]]
        if not isinstance(statement, dict):
            return excess_assets

        # Get cash
        cash = (
            statement.get('Cash And Cash Equivalents', 0) or
            statement.get('Cash', 0) or
            0
        )

        # Get revenue to determine if cash is excessive
        revenue = 0
        if self.company_data.income_statement:
            latest_income = self.company_data.income_statement.get(sorted_dates[0], {})
            if isinstance(latest_income, dict):
                revenue = latest_income.get('Total Revenue', 0) or latest_income.get('Revenue', 0) or 0

        # Excess cash = cash > 5% of revenue
        if revenue > 0:
            normal_cash = revenue * 0.05
            if cash > normal_cash:
                excess_assets += (cash - normal_cash)
        else:
            # If no revenue data, assume excess if cash > $1B
            if cash > 1_000_000_000:
                excess_assets += cash * 0.5  # Assume 50% is excess

        return excess_assets

    def calculate(self, business_quality_score: float = 50.0) -> EPVResult:
        """Calculate Earnings Power Value"""
        import logging
        logger = logging.getLogger(__name__)

        # Normalize earnings
        normalized_earnings = self.normalize_earnings()

        logger.info(f"EPV: normalized_earnings = {normalized_earnings}")

        # Check for nan/inf values
        if math.isnan(normalized_earnings) or math.isinf(normalized_earnings) or normalized_earnings <= 0:
            logger.warning(f"EPV: normalized_earnings is {normalized_earnings}, returning 0")
            return EPVResult(
                fair_value_per_share=0.0,
                earnings_power_value=0.0,
                normalized_earnings=0.0,
                capitalization_rate=0.0
            )

        # Calculate tax-adjusted earnings
        tax_rate = self.calculate_effective_tax_rate()
        tax_adjusted_earnings = normalized_earnings * (1 - tax_rate)
        logger.info(f"EPV: tax_rate = {tax_rate}, tax_adjusted_earnings = {tax_adjusted_earnings}")

        # Determine capitalization rate
        cap_rate = self.determine_capitalization_rate(business_quality_score)
        logger.info(f"EPV: cap_rate = {cap_rate} (quality_score = {business_quality_score})")

        # Calculate EPV
        epv = tax_adjusted_earnings / cap_rate
        logger.info(f"EPV: earnings_power_value = {epv}")

        # Add excess assets
        excess_assets = self.calculate_excess_assets()
        total_value = epv + excess_assets
        logger.info(f"EPV: excess_assets = {excess_assets}, total_value = {total_value}")

        # Calculate per share
        shares = self.company_data.shares_outstanding
        logger.info(f"EPV: shares_outstanding = {shares}")

        if not shares or shares <= 0:
            logger.warning(f"EPV: Invalid shares_outstanding ({shares}), returning 0")
            fair_value_per_share = 0.0
        else:
            fair_value_per_share = total_value / shares
            logger.info(f"EPV: fair_value_per_share = {fair_value_per_share}")

        return EPVResult(
            fair_value_per_share=max(fair_value_per_share, 0.0),
            earnings_power_value=epv,
            normalized_earnings=normalized_earnings,
            capitalization_rate=cap_rate
        )
