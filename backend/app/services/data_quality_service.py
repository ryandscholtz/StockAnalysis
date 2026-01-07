"""
Data validation and quality service for the Stock Analysis system
"""
import re
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass
import logging

from app.core.exceptions import ValidationError, BusinessLogicError

logger = logging.getLogger(__name__)


class DataQualityLevel(str, Enum):
    """Data quality levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL = "critical"


class ValidationSeverity(str, Enum):
    """Validation issue severity levels"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a data validation issue"""
    field: str
    message: str
    severity: ValidationSeverity
    value: Any
    expected_type: Optional[str] = None
    constraint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "message": self.message,
            "severity": self.severity.value,
            "value": str(self.value),
            "expected_type": self.expected_type,
            "constraint": self.constraint
        }


@dataclass
class DataQualityReport:
    """Data quality assessment report"""
    overall_quality: DataQualityLevel
    quality_score: float  # 0.0 to 1.0
    total_fields: int
    valid_fields: int
    issues: List[ValidationIssue]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_quality": self.overall_quality.value,
            "quality_score": self.quality_score,
            "total_fields": self.total_fields,
            "valid_fields": self.valid_fields,
            "issues": [issue.to_dict() for issue in self.issues],
            "timestamp": self.timestamp.isoformat()
        }


class DataValidator:
    """Base class for data validators"""

    def __init__(self, name: str):
        self.name = name
        self.issues: List[ValidationIssue] = []

    def validate(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate data and return list of issues"""
        self.issues = []
        self._validate_data(data)
        return self.issues

    def _validate_data(self, data: Dict[str, Any]):
        """Override this method to implement validation logic"""
        raise NotImplementedError("Subclasses must implement _validate_data")

    def add_issue(self, field: str, message: str, severity: ValidationSeverity,
                  value: Any, expected_type: Optional[str] = None,
                  constraint: Optional[str] = None):
        """Add a validation issue"""
        issue = ValidationIssue(
            field=field,
            message=message,
            severity=severity,
            value=value,
            expected_type=expected_type,
            constraint=constraint
        )
        self.issues.append(issue)


class StockDataValidator(DataValidator):
    """Validator for stock analysis data"""

    def __init__(self):
        super().__init__("stock_data_validator")

    def _validate_data(self, data: Dict[str, Any]):
        """Validate stock analysis data"""
        # Validate ticker
        self._validate_ticker(data.get("ticker"))

        # Validate company name
        self._validate_company_name(data.get("company_name"))

        # Validate financial metrics
        self._validate_price(data.get("current_price"), "current_price")
        self._validate_price(data.get("fair_value"), "fair_value")

        # Validate percentages
        self._validate_percentage(data.get("margin_of_safety"), "margin_of_safety")

        # Validate recommendation
        self._validate_recommendation(data.get("recommendation"))

        # Validate financial ratios
        self._validate_financial_ratios(data.get("financial_ratios", {}))

        # Validate business metrics
        self._validate_business_metrics(data.get("business_metrics", {}))

    def _validate_ticker(self, ticker: Any):
        """Validate stock ticker symbol"""
        if ticker is None:
            self.add_issue("ticker", "Ticker is required", ValidationSeverity.ERROR, ticker, "string")
            return

        if not isinstance(ticker, str):
            self.add_issue("ticker", "Ticker must be a string", ValidationSeverity.ERROR, ticker, "string")
            return

        original_ticker = ticker
        ticker = ticker.strip().upper()

        if len(ticker) == 0:
            self.add_issue("ticker", "Ticker cannot be empty", ValidationSeverity.ERROR, original_ticker, "string")
            return

        if len(ticker) > 10:
            self.add_issue("ticker", "Ticker too long (max 10 characters)", ValidationSeverity.WARNING, original_ticker, "string", "max_length=10")

        if not re.match(r'^[A-Z0-9.-]+$', ticker):
            self.add_issue("ticker", "Ticker contains invalid characters", ValidationSeverity.ERROR, original_ticker, "string", "alphanumeric_with_dots_dashes")

    def _validate_company_name(self, company_name: Any):
        """Validate company name"""
        if company_name is None:
            self.add_issue("company_name", "Company name is required", ValidationSeverity.ERROR, company_name, "string")
            return

        if not isinstance(company_name, str):
            self.add_issue("company_name", "Company name must be a string", ValidationSeverity.ERROR, company_name, "string")
            return

        company_name = company_name.strip()

        if len(company_name) == 0:
            self.add_issue("company_name", "Company name cannot be empty", ValidationSeverity.ERROR, company_name, "string")

        if len(company_name) > 200:
            self.add_issue("company_name", "Company name too long (max 200 characters)", ValidationSeverity.WARNING, company_name, "string", "max_length=200")

    def _validate_price(self, price: Any, field_name: str):
        """Validate price values"""
        if price is None:
            self.add_issue(field_name, f"{field_name} is required", ValidationSeverity.ERROR, price, "float")
            return

        if not isinstance(price, (int, float)):
            self.add_issue(field_name, f"{field_name} must be a number", ValidationSeverity.ERROR, price, "float")
            return

        if price <= 0:
            self.add_issue(field_name, f"{field_name} must be positive", ValidationSeverity.ERROR, price, "float", "positive")

        if price > 1000000:
            self.add_issue(field_name, f"{field_name} seems unreasonably high", ValidationSeverity.WARNING, price, "float", "reasonable_range")

    def _validate_percentage(self, percentage: Any, field_name: str):
        """Validate percentage values"""
        if percentage is None:
            return  # Percentages are often optional

        if not isinstance(percentage, (int, float)):
            self.add_issue(field_name, f"{field_name} must be a number", ValidationSeverity.ERROR, percentage, "float")
            return

        if percentage < -100 or percentage > 100:
            self.add_issue(field_name, f"{field_name} should be between -100% and 100%", ValidationSeverity.WARNING, percentage, "float", "percentage_range")

    def _validate_recommendation(self, recommendation: Any):
        """Validate investment recommendation"""
        if recommendation is None:
            self.add_issue("recommendation", "Recommendation is required", ValidationSeverity.ERROR, recommendation, "string")
            return

        if not isinstance(recommendation, str):
            self.add_issue("recommendation", "Recommendation must be a string", ValidationSeverity.ERROR, recommendation, "string")
            return

        valid_recommendations = ["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell", "Avoid"]
        if recommendation not in valid_recommendations:
            self.add_issue("recommendation", f"Invalid recommendation. Must be one of: {valid_recommendations}", ValidationSeverity.ERROR, recommendation, "string", "enum")

    def _validate_financial_ratios(self, ratios: Dict[str, Any]):
        """Validate financial ratios"""
        if not isinstance(ratios, dict):
            self.add_issue("financial_ratios", "Financial ratios must be a dictionary", ValidationSeverity.ERROR, ratios, "dict")
            return

        # Validate specific ratios
        ratio_validations = {
            "pe_ratio": (0, 1000, "P/E ratio"),
            "pb_ratio": (0, 100, "P/B ratio"),
            "debt_to_equity": (0, 10, "Debt-to-equity ratio"),
            "current_ratio": (0, 20, "Current ratio"),
            "roe": (-1, 2, "ROE"),
            "roa": (-1, 1, "ROA")
        }

        for ratio_name, (min_val, max_val, display_name) in ratio_validations.items():
            if ratio_name in ratios:
                value = ratios[ratio_name]
                if value is not None:
                    if not isinstance(value, (int, float)):
                        self.add_issue(f"financial_ratios.{ratio_name}", f"{display_name} must be a number", ValidationSeverity.ERROR, value, "float")
                    elif value < min_val or value > max_val:
                        self.add_issue(f"financial_ratios.{ratio_name}", f"{display_name} outside reasonable range ({min_val}-{max_val})", ValidationSeverity.WARNING, value, "float", f"range_{min_val}_{max_val}")

    def _validate_business_metrics(self, metrics: Dict[str, Any]):
        """Validate business quality metrics"""
        if not isinstance(metrics, dict):
            self.add_issue("business_metrics", "Business metrics must be a dictionary", ValidationSeverity.ERROR, metrics, "dict")
            return

        # Validate scores (should be 0-10)
        score_fields = ["financial_health_score", "business_quality_score", "management_quality_score"]
        for field in score_fields:
            if field in metrics:
                score = metrics[field]
                if score is not None:
                    if not isinstance(score, (int, float)):
                        self.add_issue(f"business_metrics.{field}", f"{field} must be a number", ValidationSeverity.ERROR, score, "float")
                    elif score < 0 or score > 10:
                        self.add_issue(f"business_metrics.{field}", f"{field} must be between 0 and 10", ValidationSeverity.ERROR, score, "float", "score_range_0_10")


class FinancialDataValidator(DataValidator):
    """Validator for financial statement data"""

    def __init__(self):
        super().__init__("financial_data_validator")

    def _validate_data(self, data: Dict[str, Any]):
        """Validate financial statement data"""
        # Validate revenue
        self._validate_financial_amount(data.get("revenue"), "revenue")

        # Validate expenses
        self._validate_financial_amount(data.get("expenses"), "expenses")

        # Validate net income
        self._validate_financial_amount(data.get("net_income"), "net_income", allow_negative=True)

        # Validate assets
        self._validate_financial_amount(data.get("total_assets"), "total_assets")

        # Validate liabilities
        self._validate_financial_amount(data.get("total_liabilities"), "total_liabilities")

        # Validate equity
        self._validate_financial_amount(data.get("shareholders_equity"), "shareholders_equity", allow_negative=True)

        # Validate cash flow
        self._validate_financial_amount(data.get("operating_cash_flow"), "operating_cash_flow", allow_negative=True)

        # Validate date fields
        self._validate_date(data.get("report_date"), "report_date")
        self._validate_date(data.get("period_end_date"), "period_end_date")

    def _validate_financial_amount(self, amount: Any, field_name: str, allow_negative: bool = False):
        """Validate financial amounts"""
        if amount is None:
            self.add_issue(field_name, f"{field_name} is required", ValidationSeverity.ERROR, amount, "float")
            return

        if not isinstance(amount, (int, float)):
            self.add_issue(field_name, f"{field_name} must be a number", ValidationSeverity.ERROR, amount, "float")
            return

        if not allow_negative and amount < 0:
            self.add_issue(field_name, f"{field_name} cannot be negative", ValidationSeverity.ERROR, amount, "float", "non_negative")

        # Check for unreasonably large values (> $1 trillion)
        if abs(amount) > 1e12:
            self.add_issue(field_name, f"{field_name} seems unreasonably large", ValidationSeverity.WARNING, amount, "float", "reasonable_magnitude")

    def _validate_date(self, date_value: Any, field_name: str):
        """Validate date fields"""
        if date_value is None:
            self.add_issue(field_name, f"{field_name} is required", ValidationSeverity.ERROR, date_value, "date")
            return

        if isinstance(date_value, str):
            try:
                # Try to parse ISO format date
                datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except ValueError:
                self.add_issue(field_name, f"{field_name} is not a valid date format", ValidationSeverity.ERROR, date_value, "date", "iso_format")
        elif isinstance(date_value, (datetime, date)):
            # Date objects are valid
            pass
        else:
            self.add_issue(field_name, f"{field_name} must be a date", ValidationSeverity.ERROR, date_value, "date")


class DataQualityService:
    """Service for assessing and managing data quality"""

    def __init__(self):
        self.validators = {
            "stock_data": StockDataValidator(),
            "financial_data": FinancialDataValidator()
        }
        self.quality_reports: List[DataQualityReport] = []

    def validate_data(self, data: Dict[str, Any], data_type: str) -> DataQualityReport:
        """Validate data and generate quality report"""
        if data_type not in self.validators:
            raise ValidationError(f"Unknown data type: {data_type}", "data_type", data_type)

        validator = self.validators[data_type]
        issues = validator.validate(data)

        # Calculate quality metrics
        total_fields = len(data)
        error_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.ERROR)
        warning_count = sum(1 for issue in issues if issue.severity == ValidationSeverity.WARNING)

        valid_fields = total_fields - error_count

        # Calculate quality score (0.0 to 1.0)
        if total_fields == 0:
            quality_score = 1.0
        else:
            # Errors reduce score more than warnings
            error_penalty = error_count * 0.2
            warning_penalty = warning_count * 0.05
            quality_score = max(0.0, 1.0 - (error_penalty + warning_penalty) / total_fields)

        # Determine overall quality level
        if error_count > 0:
            overall_quality = DataQualityLevel.CRITICAL
        elif quality_score >= 0.9:
            overall_quality = DataQualityLevel.HIGH
        elif quality_score >= 0.7:
            overall_quality = DataQualityLevel.MEDIUM
        else:
            overall_quality = DataQualityLevel.LOW

        report = DataQualityReport(
            overall_quality=overall_quality,
            quality_score=quality_score,
            total_fields=total_fields,
            valid_fields=valid_fields,
            issues=issues,
            timestamp=datetime.now()
        )

        self.quality_reports.append(report)

        # Log quality issues
        if issues:
            logger.warning(f"Data quality issues found for {data_type}: {len(issues)} issues")
            for issue in issues:
                if issue.severity == ValidationSeverity.ERROR:
                    logger.error(f"Data validation error in {issue.field}: {issue.message}")
                elif issue.severity == ValidationSeverity.WARNING:
                    logger.warning(f"Data validation warning in {issue.field}: {issue.message}")

        return report

    def get_quality_summary(self) -> Dict[str, Any]:
        """Get summary of data quality across all reports"""
        if not self.quality_reports:
            return {
                "total_reports": 0,
                "average_quality_score": 0.0,
                "quality_distribution": {},
                "common_issues": []
            }

        total_reports = len(self.quality_reports)
        average_score = sum(report.quality_score for report in self.quality_reports) / total_reports

        # Quality level distribution
        quality_distribution = {}
        for level in DataQualityLevel:
            count = sum(1 for report in self.quality_reports if report.overall_quality == level)
            quality_distribution[level.value] = count

        # Common issues
        issue_counts = {}
        for report in self.quality_reports:
            for issue in report.issues:
                key = f"{issue.field}: {issue.message}"
                issue_counts[key] = issue_counts.get(key, 0) + 1

        common_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_reports": total_reports,
            "average_quality_score": average_score,
            "quality_distribution": quality_distribution,
            "common_issues": [{"issue": issue, "count": count} for issue, count in common_issues]
        }

    def reject_invalid_data(self, data: Dict[str, Any], data_type: str) -> Tuple[bool, DataQualityReport]:
        """Validate data and reject if it has critical issues"""
        report = self.validate_data(data, data_type)

        # Reject data if it has any errors
        has_errors = any(issue.severity == ValidationSeverity.ERROR for issue in report.issues)

        if has_errors:
            logger.error(f"Rejecting {data_type} data due to validation errors")
            raise BusinessLogicError(
                f"Data validation failed for {data_type}",
                context={
                    "data_type": data_type,
                    "error_count": len([i for i in report.issues if i.severity == ValidationSeverity.ERROR]),
                    "issues": [issue.to_dict() for issue in report.issues if issue.severity == ValidationSeverity.ERROR]
                }
            )

        return True, report


# Global data quality service instance
data_quality_service = DataQualityService()
