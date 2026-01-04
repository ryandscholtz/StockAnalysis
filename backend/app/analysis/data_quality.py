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
        # Check income statement
        if not self.company_data.income_statement:
            self.warnings.append(DataQualityWarning(
                category='missing_data',
                field='income_statement',
                message='No income statement data available. DCF and EPV calculations cannot be performed.',
                severity='high'
            ))
        elif len(self.company_data.income_statement) < 3:
            self.warnings.append(DataQualityWarning(
                category='missing_data',
                field='income_statement',
                message=f'Insufficient income statement data ({len(self.company_data.income_statement)} period(s), need 3+). DCF and EPV calculations may be inaccurate.',
                severity='high'
            ))
        
        # Always check for key fields if income statement exists (even if < 3 periods)
        if self.company_data.income_statement:
            # Check for key income statement fields across all periods
            required_fields = {
                'Total Revenue': ['total revenue', 'revenue', 'net sales', 'sales'],
                'Net Income': ['net income', 'net earnings', 'earnings'],
                'Operating Income': ['operating income', 'operating profit', 'ebit'],
                'EBIT': ['ebit', 'earnings before interest and tax']
            }
            
            # Check all periods to see if field exists in any
            for field_name, search_terms in required_fields.items():
                found = False
                for period_data in self.company_data.income_statement.values():
                    if isinstance(period_data, dict):
                        for key in period_data.keys():
                            key_lower = str(key).lower()
                            if any(term in key_lower for term in search_terms):
                                found = True
                                break
                        if found:
                            break
                
                if not found:
                    self.warnings.append(DataQualityWarning(
                        category='missing_data',
                        field=field_name.lower().replace(' ', '_'),
                        message=f'{field_name} not found in income statement. This may affect valuation accuracy.',
                        severity='high' if field_name in ['Total Revenue', 'Net Income'] else 'medium'
                    ))
        
        # Check balance sheet
        if not self.company_data.balance_sheet:
            self.warnings.append(DataQualityWarning(
                category='missing_data',
                field='balance_sheet',
                message='No balance sheet data available. Asset-based valuation cannot be performed.',
                severity='high'
            ))
        elif len(self.company_data.balance_sheet) < 3:
            self.warnings.append(DataQualityWarning(
                category='missing_data',
                field='balance_sheet',
                message=f'Insufficient balance sheet data ({len(self.company_data.balance_sheet)} period(s), need 3+). Asset-based valuation may be inaccurate.',
                severity='high'
            ))
        
        # Always check for key fields if balance sheet exists (even if < 3 periods)
        if self.company_data.balance_sheet:
            # Check for key balance sheet fields across all periods
            required_fields = {
                'Total Assets': ['total assets', 'assets'],
                'Total Liabilities': ['total liabilities', 'liabilities'],
                'Total Stockholder Equity': ['total stockholder equity', 'total equity', 'shareholders equity', 'stockholders equity'],
                'Cash And Cash Equivalents': ['cash and cash equivalents', 'cash', 'cash equivalents'],
                'Total Debt': ['total debt', 'debt', 'long term debt', 'short term debt']
            }
            
            # Check all periods to see if field exists in any
            for field_name, search_terms in required_fields.items():
                found = False
                for period_data in self.company_data.balance_sheet.values():
                    if isinstance(period_data, dict):
                        for key in period_data.keys():
                            key_lower = str(key).lower()
                            if any(term in key_lower for term in search_terms):
                                found = True
                                break
                        if found:
                            break
                
                if not found:
                    self.warnings.append(DataQualityWarning(
                        category='missing_data',
                        field=field_name.lower().replace(' ', '_'),
                        message=f'{field_name} not found in balance sheet. This may affect valuation accuracy.',
                        severity='high' if field_name in ['Total Assets', 'Total Liabilities', 'Total Stockholder Equity'] else 'medium'
                    ))
        
        # Check cash flow
        if not self.company_data.cashflow:
            self.warnings.append(DataQualityWarning(
                category='missing_data',
                field='cashflow',
                message='No cash flow data available. DCF calculation cannot be performed.',
                severity='high'
            ))
        elif len(self.company_data.cashflow) < 3:
            self.warnings.append(DataQualityWarning(
                category='missing_data',
                field='cashflow',
                message=f'Insufficient cash flow data ({len(self.company_data.cashflow)} period(s), need 3+). DCF calculation may use estimated FCF from earnings (70% of net income).',
                severity='high'
            ))
        
        # Always check for key fields if cash flow exists (even if < 3 periods)
        if self.company_data.cashflow:
            # Check for key cash flow fields across all periods
            required_fields = {
                'Operating Cash Flow': ['operating cash flow', 'cash from operating activities', 'operating activities'],
                'Free Cash Flow': ['free cash flow', 'fcf'],
                'Capital Expenditures': ['capital expenditures', 'capex', 'capital spending']
            }
            
            # Check all periods to see if field exists in any
            for field_name, search_terms in required_fields.items():
                found = False
                for period_data in self.company_data.cashflow.values():
                    if isinstance(period_data, dict):
                        for key in period_data.keys():
                            key_lower = str(key).lower()
                            if any(term in key_lower for term in search_terms):
                                found = True
                                break
                        if found:
                            break
                
                if not found:
                    self.warnings.append(DataQualityWarning(
                        category='missing_data',
                        field=field_name.lower().replace(' ', '_'),
                        message=f'{field_name} not found in cash flow statement. This may affect DCF valuation accuracy.',
                        severity='high' if field_name == 'Operating Cash Flow' else 'medium'
                    ))
    
    def _check_key_metrics(self):
        """Check for missing key metrics"""
        # Check shares_outstanding - use is None to allow 0 values
        if self.company_data.shares_outstanding is None:
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
        
        # Check market_cap - use is None to allow 0 values, but also try to calculate if possible
        if self.company_data.market_cap is None:
            # Try to calculate market cap if we have price and shares
            if self.company_data.current_price and self.company_data.shares_outstanding:
                # Market cap can be calculated, so don't warn
                pass
            else:
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

