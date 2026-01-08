"""
Data quality checks and validation
"""
from typing import Dict, List, Optional, Tuple
from app.data.data_fetcher import CompanyData


class DataValidator:
    """Validate and check data quality"""

    @staticmethod
    def validate_company_data(data: CompanyData) -> Tuple[bool, List[str]]:
        """
        Validate company data quality
        Returns (is_valid, list_of_warnings)
        """
        warnings = []

        # Check required fields
        if not data.current_price or data.current_price <= 0:
            return False, ["Invalid or missing current price"]

        if not data.shares_outstanding or data.shares_outstanding <= 0:
            warnings.append("Missing shares outstanding")

        # Check financial statement data
        if not data.income_statement:
            warnings.append("Missing income statement data")

        if not data.balance_sheet:
            warnings.append("Missing balance sheet data")

        if not data.cashflow:
            warnings.append("Missing cash flow data")

        # Check data recency (if we have dates)
        # This would require parsing the financial statement dates

        is_valid = len([w for w in warnings if "Missing" in w]) < 3

        return is_valid, warnings

    @staticmethod
    def has_sufficient_history(data: CompanyData, years: int = 5) -> bool:
        """Check if we have sufficient historical data"""
        if not data.income_statement:
            return False

        # Count number of years of data
        # This is simplified - actual implementation would parse dates
        statement_years = len(data.income_statement)
        return statement_years >= years

    @staticmethod
    def check_data_quality(data: CompanyData) -> Dict[str, any]:
        """
        Comprehensive data quality check
        Returns quality metrics
        """
        quality = {
            'has_price': bool(data.current_price),
            'has_financials': bool(data.income_statement),
            'has_balance_sheet': bool(data.balance_sheet),
            'has_cashflow': bool(data.cashflow),
            'has_historical_prices': bool(data.historical_prices),
            'data_completeness': 0.0
        }

        # Calculate completeness score
        checks = [
            quality['has_price'],
            quality['has_financials'],
            quality['has_balance_sheet'],
            quality['has_cashflow'],
            quality['has_historical_prices']
        ]
        quality['data_completeness'] = sum(checks) / len(checks) * 100

        return quality
