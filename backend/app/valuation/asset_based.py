"""
Asset-Based Valuation Model
"""
from typing import Optional
from dataclasses import dataclass
from app.data.data_fetcher import CompanyData


@dataclass
class AssetBasedResult:
    """Result of asset-based valuation"""
    fair_value_per_share: float
    book_value_per_share: float
    tangible_book_value_per_share: float
    liquidation_value_per_share: float
    method_used: str  # 'book', 'tangible', 'liquidation'


class AssetBasedValuation:
    """Asset-based valuation model"""
    
    def __init__(self, company_data: CompanyData):
        self.company_data = company_data
    
    def calculate_book_value(self) -> float:
        """Calculate book value per share"""
        if not self.company_data.balance_sheet:
            return 0.0
        
        # Get most recent balance sheet
        sorted_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
        if not sorted_dates:
            return 0.0
        
        statement = self.company_data.balance_sheet[sorted_dates[0]]
        if not isinstance(statement, dict):
            return 0.0
        
        # Total Shareholders' Equity
        equity = (
            statement.get('Total Stockholder Equity', 0) or
            statement.get('Stockholders Equity', 0) or
            statement.get('Shareholders Equity', 0) or
            0
        )
        
        shares = self.company_data.shares_outstanding
        if not shares or shares <= 0:
            return 0.0
        
        return equity / shares
    
    def calculate_tangible_book_value(self) -> float:
        """Calculate tangible book value per share"""
        if not self.company_data.balance_sheet:
            return 0.0
        
        sorted_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
        if not sorted_dates:
            return 0.0
        
        statement = self.company_data.balance_sheet[sorted_dates[0]]
        if not isinstance(statement, dict):
            return 0.0
        
        # Total Assets
        total_assets = statement.get('Total Assets', 0) or 0
        
        # Intangible Assets
        intangibles = (
            statement.get('Good Will', 0) or
            statement.get('Goodwill', 0) or
            statement.get('Intangible Assets', 0) or
            0
        )
        
        # Total Liabilities
        total_liabilities = statement.get('Total Liabilities', 0) or 0
        
        # Tangible Book Value = Total Assets - Intangibles - Total Liabilities
        tangible_book = total_assets - intangibles - total_liabilities
        
        shares = self.company_data.shares_outstanding
        if not shares or shares <= 0:
            return 0.0
        
        return tangible_book / shares
    
    def calculate_liquidation_value(self) -> float:
        """Calculate liquidation value (conservative estimate)"""
        if not self.company_data.balance_sheet:
            return 0.0
        
        sorted_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
        if not sorted_dates:
            return 0.0
        
        statement = self.company_data.balance_sheet[sorted_dates[0]]
        if not isinstance(statement, dict):
            return 0.0
        
        # Apply discount factors to assets
        # Accounts Receivable: 85% of book value
        ar = statement.get('Net Receivables', 0) or statement.get('Accounts Receivable', 0) or 0
        ar_value = ar * 0.85
        
        # Inventory: 60% of book value
        inventory = statement.get('Inventory', 0) or 0
        inventory_value = inventory * 0.60
        
        # Property, Plant & Equipment: 50% of book value
        ppe = (
            statement.get('Property Plant Equipment', 0) or
            statement.get('Net PPE', 0) or
            0
        )
        ppe_value = ppe * 0.50
        
        # Cash: 100% (fully liquid)
        cash = (
            statement.get('Cash And Cash Equivalents', 0) or
            statement.get('Cash', 0) or
            0
        )
        
        # Total Liabilities (must be paid in full)
        total_liabilities = statement.get('Total Liabilities', 0) or 0
        
        # Liquidation Value = Sum of discounted assets - Total Liabilities
        liquidation_value = ar_value + inventory_value + ppe_value + cash - total_liabilities
        
        shares = self.company_data.shares_outstanding
        if not shares or shares <= 0:
            return 0.0
        
        return liquidation_value / shares
    
    def determine_business_type(self) -> str:
        """Determine if business is asset-light or asset-heavy"""
        if not self.company_data.balance_sheet:
            return 'unknown'
        
        sorted_dates = sorted(self.company_data.balance_sheet.keys(), reverse=True)
        if not sorted_dates:
            return 'unknown'
        
        statement = self.company_data.balance_sheet[sorted_dates[0]]
        if not isinstance(statement, dict):
            return 'unknown'
        
        total_assets = statement.get('Total Assets', 0) or 0
        revenue = 0
        
        if self.company_data.income_statement:
            latest_income = self.company_data.income_statement.get(sorted_dates[0], {})
            if isinstance(latest_income, dict):
                revenue = latest_income.get('Total Revenue', 0) or latest_income.get('Revenue', 0) or 0
        
        if revenue > 0:
            asset_to_revenue = total_assets / revenue
            if asset_to_revenue > 2.0:
                return 'asset_heavy'
            else:
                return 'asset_light'
        
        return 'unknown'
    
    def calculate(self) -> AssetBasedResult:
        """Calculate asset-based fair value"""
        book_value = self.calculate_book_value()
        tangible_book = self.calculate_tangible_book_value()
        liquidation_value = self.calculate_liquidation_value()
        
        # Select appropriate method based on business type
        business_type = self.determine_business_type()
        
        if business_type == 'asset_heavy':
            # Use tangible book value or liquidation value (whichever is higher)
            fair_value = max(tangible_book, liquidation_value)
            method = 'tangible' if tangible_book >= liquidation_value else 'liquidation'
        elif business_type == 'asset_light':
            # Use book value
            fair_value = book_value
            method = 'book'
        else:
            # Default to tangible book value
            fair_value = tangible_book if tangible_book > 0 else book_value
            method = 'tangible' if tangible_book > 0 else 'book'
        
        # Ensure non-negative
        fair_value = max(fair_value, 0.0)
        
        return AssetBasedResult(
            fair_value_per_share=fair_value,
            book_value_per_share=book_value,
            tangible_book_value_per_share=tangible_book,
            liquidation_value_per_share=liquidation_value,
            method_used=method
        )

