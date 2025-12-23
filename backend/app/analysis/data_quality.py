"""
Data Quality Analyzer
Identifies which assumptions and defaults are being used in calculations
"""
from typing import List, Dict, Optional
from app.data.data_fetcher import CompanyData
from dataclasses import dataclass


@dataclass
class DataQualityWarning:
    """Represents a data quality warning"""
    category: str  # 'assumption', 'missing_data', 'estimated'
    field: str
    message: str
    severity: str  # 'high', 'medium', 'low'
    assumed_value: Optional[float] = None
    actual_value: Optional[float] = None


class DataQualityAnalyzer:
    """Analyze data quality and identify assumptions"""
    
    def __init__(self, company_data: CompanyData):
        self.company_data = company_data
        self.warnings: List[DataQualityWarning] = []
    
    def analyze(self) -> List[DataQualityWarning]:
        """Analyze data quality and return warnings"""
        self.warnings = []
        
        # Check for missing financial statements
        self._check_financial_statements()
        
        # Check for missing key metrics
        self._check_key_metrics()
        
        # Check for assumptions in calculations
        self._check_calculation_assumptions()
        
        return self.warnings
    
    def _check_financial_statements(self):
        """Check if financial statements are missing or incomplete"""
        if not self.company_data.income_statement or len(self.company_data.income_statement) < 3:
            self.warnings.append(DataQualityWarning(
                category='missing_data',
                field='income_statement',
                message='Insufficient income statement data (less than 3 periods). DCF and EPV calculations may be inaccurate.',
                severity='high'
            ))
        
        if not self.company_data.balance_sheet or len(self.company_data.balance_sheet) < 3:
            self.warnings.append(DataQualityWarning(
                category='missing_data',
                field='balance_sheet',
                message='Insufficient balance sheet data (less than 3 periods). Asset-based valuation may be inaccurate.',
                severity='high'
            ))
        
        if not self.company_data.cashflow or len(self.company_data.cashflow) < 3:
            self.warnings.append(DataQualityWarning(
                category='missing_data',
                field='cashflow',
                message='Insufficient cash flow data (less than 3 periods). DCF calculation may use estimated FCF from earnings (70% of net income).',
                severity='high'
            ))
    
    def _check_key_metrics(self):
        """Check for missing key metrics"""
        if not self.company_data.shares_outstanding:
            self.warnings.append(DataQualityWarning(
                category='missing_data',
                field='shares_outstanding',
                message='Shares outstanding not available. Per-share valuations cannot be calculated accurately.',
                severity='high'
            ))
        
        if not self.company_data.beta:
            self.warnings.append(DataQualityWarning(
                category='assumption',
                field='beta',
                message='Beta not available. Using default beta of 1.0 for WACC calculation.',
                severity='medium',
                assumed_value=1.0
            ))
        
        if not self.company_data.market_cap:
            if not (self.company_data.current_price and self.company_data.shares_outstanding):
                self.warnings.append(DataQualityWarning(
                    category='missing_data',
                    field='market_cap',
                    message='Market cap not available and cannot be calculated. Some ratios may be unavailable.',
                    severity='medium'
                ))
    
    def _check_calculation_assumptions(self):
        """Check for assumptions used in calculations"""
        # Check if FCF is being estimated
        if self.company_data.cashflow:
            # Check if we have operating cash flow
            has_ocf = False
            for period_data in self.company_data.cashflow.values():
                if isinstance(period_data, dict):
                    if any(key.lower() in ['operating cash flow', 'operatingcashflow', 'total cash from operating activities'] 
                           for key in period_data.keys()):
                        has_ocf = True
                        break
            
            if not has_ocf:
                self.warnings.append(DataQualityWarning(
                    category='estimated',
                    field='free_cash_flow',
                    message='Operating cash flow not found. DCF may estimate FCF as 70% of net income.',
                    severity='high',
                    assumed_value=None  # Would be calculated dynamically
                ))
        
        # Check for debt assumptions
        if self.company_data.balance_sheet:
            has_debt = False
            for period_data in self.company_data.balance_sheet.values():
                if isinstance(period_data, dict):
                    if any(key.lower() in ['total debt', 'long term debt', 'short term debt'] 
                           for key in period_data.keys()):
                        has_debt = True
                        break
            
            if not has_debt:
                self.warnings.append(DataQualityWarning(
                    category='assumption',
                    field='debt',
                    message='Debt information not found. WACC calculation assumes cost of debt = risk-free rate + 2%.',
                    severity='medium',
                    assumed_value=None
                ))
        
        # Check tax rate assumption
        if self.company_data.income_statement:
            has_tax = False
            for period_data in self.company_data.income_statement.values():
                if isinstance(period_data, dict):
                    if any(key.lower() in ['tax provision', 'tax expense', 'income tax'] 
                           for key in period_data.keys()):
                        has_tax = True
                        break
            
            if not has_tax:
                self.warnings.append(DataQualityWarning(
                    category='assumption',
                    field='tax_rate',
                    message='Tax information not found. Using default corporate tax rate of 21%.',
                    severity='medium',
                    assumed_value=0.21
                ))

