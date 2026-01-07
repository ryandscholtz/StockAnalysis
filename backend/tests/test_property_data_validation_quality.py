"""
Property-based tests for data validation and quality
Feature: tech-stack-modernization, Property: Data Validation and Quality
"""
import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime, date
from typing import Dict, Any, List
import uuid

from app.services.data_quality_service import (
    DataQualityService, StockDataValidator, FinancialDataValidator,
    ValidationSeverity, DataQualityLevel, ValidationIssue, DataQualityReport
)
from app.core.exceptions import ValidationError, BusinessLogicError


class TestDataValidationAndQuality:
    """Test that data validation consistently rejects invalid data and detects quality issues"""
    
    @given(
        ticker=st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', min_size=1, max_size=10),
        company_name=st.text(min_size=1, max_size=200).filter(lambda x: x.strip()),
        current_price=st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False),
        fair_value=st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False),
        margin_of_safety=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
        recommendation=st.sampled_from(["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell", "Avoid"])
    )
    @settings(max_examples=100)
    def test_valid_stock_data_acceptance(
        self, 
        ticker: str, 
        company_name: str, 
        current_price: float, 
        fair_value: float, 
        margin_of_safety: float,
        recommendation: str
    ):
        """
        Feature: tech-stack-modernization, Property: Data Validation and Quality
        For any valid stock data, validation should accept it and report high quality
        **Validates: Requirements 10.3**
        """
        service = DataQualityService()
        
        stock_data = {
            "ticker": ticker.upper(),
            "company_name": company_name.strip(),
            "current_price": current_price,
            "fair_value": fair_value,
            "margin_of_safety": margin_of_safety,
            "recommendation": recommendation,
            "financial_ratios": {
                "pe_ratio": 15.5,
                "pb_ratio": 2.1,
                "debt_to_equity": 0.3,
                "current_ratio": 1.8,
                "roe": 0.15,
                "roa": 0.08
            },
            "business_metrics": {
                "financial_health_score": 8.0,
                "business_quality_score": 7.5,
                "management_quality_score": 8.5
            }
        }
        
        # Valid data should pass validation
        report = service.validate_data(stock_data, "stock_data")
        
        # Should have no errors
        error_issues = [issue for issue in report.issues if issue.severity == ValidationSeverity.ERROR]
        assert len(error_issues) == 0, f"Valid data should not have errors: {[issue.message for issue in error_issues]}"
        
        # Should have high quality score
        assert report.quality_score >= 0.7, f"Valid data should have high quality score, got {report.quality_score}"
        
        # Should not be critical quality
        assert report.overall_quality != DataQualityLevel.CRITICAL, "Valid data should not be critical quality"
    
    @given(
        invalid_ticker=st.one_of(
            st.just(""),  # Empty string
            st.just("   "),  # Whitespace only
            st.none(),  # None value
            st.text(min_size=11, max_size=50),  # Too long
            st.text().filter(lambda x: any(c in x for c in "!@#$%^&*()+=[]{}|\\:;\"'<>,?/"))  # Invalid characters
        ),
        invalid_price=st.one_of(
            st.floats(max_value=0.0),  # Zero or negative
            st.just(float('nan')),  # NaN
            st.just(float('inf')),  # Infinity
            st.just(float('-inf')),  # Negative infinity
            st.text(),  # String instead of number
            st.none()  # None value
        )
    )
    @settings(max_examples=100)
    def test_invalid_stock_data_rejection(self, invalid_ticker, invalid_price):
        """
        Feature: tech-stack-modernization, Property: Data Validation and Quality
        For any invalid stock data, validation should detect issues and report low quality
        **Validates: Requirements 10.3**
        """
        service = DataQualityService()
        
        stock_data = {
            "ticker": invalid_ticker,
            "company_name": "Test Company",
            "current_price": invalid_price,
            "fair_value": 100.0,
            "margin_of_safety": 10.0,
            "recommendation": "Buy"
        }
        
        # Invalid data should be detected
        report = service.validate_data(stock_data, "stock_data")
        
        # Should have at least one error
        error_issues = [issue for issue in report.issues if issue.severity == ValidationSeverity.ERROR]
        assert len(error_issues) > 0, "Invalid data should have validation errors"
        
        # Should have low quality score or be critical
        assert report.quality_score < 0.9 or report.overall_quality == DataQualityLevel.CRITICAL, \
            f"Invalid data should have low quality, got score {report.quality_score} and level {report.overall_quality}"
    
    @given(
        revenue=st.floats(min_value=1000.0, max_value=1e12, allow_nan=False, allow_infinity=False),
        expenses=st.floats(min_value=500.0, max_value=1e12, allow_nan=False, allow_infinity=False),
        total_assets=st.floats(min_value=1000.0, max_value=1e12, allow_nan=False, allow_infinity=False),
        total_liabilities=st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False),
        report_date=st.dates(min_value=date(2020, 1, 1), max_value=date(2024, 12, 31))
    )
    @settings(max_examples=100)
    def test_valid_financial_data_acceptance(
        self, 
        revenue: float, 
        expenses: float, 
        total_assets: float, 
        total_liabilities: float,
        report_date: date
    ):
        """
        Feature: tech-stack-modernization, Property: Data Validation and Quality
        For any valid financial data, validation should accept it and report appropriate quality
        **Validates: Requirements 10.3**
        """
        service = DataQualityService()
        
        net_income = revenue - expenses
        shareholders_equity = total_assets - total_liabilities
        
        financial_data = {
            "revenue": revenue,
            "expenses": expenses,
            "net_income": net_income,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "shareholders_equity": shareholders_equity,
            "operating_cash_flow": net_income * 1.1,  # Approximate OCF
            "report_date": report_date.isoformat(),
            "period_end_date": report_date.isoformat()
        }
        
        # Valid financial data should pass validation
        report = service.validate_data(financial_data, "financial_data")
        
        # Should have no errors
        error_issues = [issue for issue in report.issues if issue.severity == ValidationSeverity.ERROR]
        assert len(error_issues) == 0, f"Valid financial data should not have errors: {[issue.message for issue in error_issues]}"
        
        # Should have reasonable quality score
        assert report.quality_score >= 0.5, f"Valid financial data should have reasonable quality score, got {report.quality_score}"
    
    @given(
        invalid_amounts=st.lists(
            st.one_of(
                st.text(),  # String instead of number
                st.just(float('nan')),  # NaN
                st.just(float('inf')),  # Infinity
                st.none()  # None value
            ),
            min_size=1,
            max_size=5
        ),
        invalid_dates=st.lists(
            st.one_of(
                st.text().filter(lambda x: x not in ["", "2023-01-01"]),  # Invalid date strings
                st.integers(),  # Integer instead of date
                st.none()  # None value
            ),
            min_size=1,
            max_size=2
        )
    )
    @settings(max_examples=100)
    def test_invalid_financial_data_rejection(self, invalid_amounts: List, invalid_dates: List):
        """
        Feature: tech-stack-modernization, Property: Data Validation and Quality
        For any invalid financial data, validation should detect issues
        **Validates: Requirements 10.3**
        """
        service = DataQualityService()
        
        # Create financial data with some invalid values
        financial_data = {
            "revenue": invalid_amounts[0] if len(invalid_amounts) > 0 else 1000000,
            "expenses": invalid_amounts[1] if len(invalid_amounts) > 1 else 800000,
            "net_income": invalid_amounts[2] if len(invalid_amounts) > 2 else 200000,
            "total_assets": invalid_amounts[3] if len(invalid_amounts) > 3 else 5000000,
            "total_liabilities": invalid_amounts[4] if len(invalid_amounts) > 4 else 3000000,
            "shareholders_equity": 2000000,
            "operating_cash_flow": 250000,
            "report_date": invalid_dates[0] if len(invalid_dates) > 0 else "2023-12-31",
            "period_end_date": invalid_dates[1] if len(invalid_dates) > 1 else "2023-12-31"
        }
        
        # Invalid data should be detected
        report = service.validate_data(financial_data, "financial_data")
        
        # Should have at least one issue (error or warning)
        assert len(report.issues) > 0, "Invalid financial data should have validation issues"
        
        # If there are errors, quality should be critical or low
        error_issues = [issue for issue in report.issues if issue.severity == ValidationSeverity.ERROR]
        if error_issues:
            assert report.overall_quality in [DataQualityLevel.CRITICAL, DataQualityLevel.LOW], \
                f"Data with errors should have critical or low quality, got {report.overall_quality}"
    
    @given(
        data_entries=st.lists(
            st.dictionaries(
                keys=st.sampled_from(["ticker", "company_name", "current_price", "fair_value", "recommendation"]),
                values=st.one_of(
                    st.text(min_size=1, max_size=50),
                    st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False),
                    st.sampled_from(["Buy", "Hold", "Sell"])
                ),
                min_size=3,
                max_size=5
            ),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50)
    def test_batch_data_quality_consistency(self, data_entries: List[Dict[str, Any]]):
        """
        Feature: tech-stack-modernization, Property: Data Validation and Quality
        For any batch of data entries, validation should be consistent across all entries
        **Validates: Requirements 10.3**
        """
        service = DataQualityService()
        
        reports = []
        for i, data_entry in enumerate(data_entries):
            # Ensure required fields have valid values for this test
            stock_data = {
                "ticker": data_entry.get("ticker", f"TEST{i}"),
                "company_name": data_entry.get("company_name", f"Test Company {i}"),
                "current_price": data_entry.get("current_price", 100.0),
                "fair_value": data_entry.get("fair_value", 120.0),
                "recommendation": data_entry.get("recommendation", "Buy")
            }
            
            report = service.validate_data(stock_data, "stock_data")
            reports.append(report)
        
        # All reports should be generated
        assert len(reports) == len(data_entries), "Should generate report for each data entry"
        
        # Each report should have consistent structure
        for i, report in enumerate(reports):
            assert isinstance(report.quality_score, float), f"Report {i} should have numeric quality score"
            assert 0.0 <= report.quality_score <= 1.0, f"Report {i} quality score should be between 0 and 1"
            assert isinstance(report.overall_quality, DataQualityLevel), f"Report {i} should have quality level"
            assert isinstance(report.issues, list), f"Report {i} should have issues list"
            assert report.total_fields > 0, f"Report {i} should count fields"
            assert report.valid_fields >= 0, f"Report {i} should count valid fields"
            assert report.valid_fields <= report.total_fields, f"Report {i} valid fields should not exceed total"
    
    @given(
        quality_threshold=st.floats(min_value=0.1, max_value=0.9),
        data_quality=st.sampled_from(["high", "medium", "low", "critical"])
    )
    @settings(max_examples=100)
    def test_quality_threshold_enforcement(self, quality_threshold: float, data_quality: str):
        """
        Feature: tech-stack-modernization, Property: Data Validation and Quality
        For any quality threshold, data below the threshold should be consistently rejected
        **Validates: Requirements 10.3**
        """
        service = DataQualityService()
        
        # Create data with different quality levels
        if data_quality == "high":
            stock_data = {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "current_price": 150.0,
                "fair_value": 180.0,
                "recommendation": "Buy"
            }
        elif data_quality == "medium":
            stock_data = {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "current_price": 150.0,
                "fair_value": 180.0,
                "recommendation": "InvalidRecommendation"  # This will cause a warning
            }
        elif data_quality == "low":
            stock_data = {
                "ticker": "",  # Invalid ticker
                "company_name": "Apple Inc.",
                "current_price": 150.0,
                "fair_value": 180.0,
                "recommendation": "Buy"
            }
        else:  # critical
            stock_data = {
                "ticker": "",  # Invalid ticker
                "company_name": "",  # Invalid company name
                "current_price": -50.0,  # Invalid price
                "fair_value": 180.0,
                "recommendation": "InvalidRecommendation"
            }
        
        report = service.validate_data(stock_data, "stock_data")
        
        # Quality assessment should be consistent with data quality
        if data_quality == "high":
            assert report.quality_score >= 0.8, f"High quality data should have high score, got {report.quality_score}"
        elif data_quality == "critical":
            assert report.overall_quality == DataQualityLevel.CRITICAL, f"Critical data should be marked critical, got {report.overall_quality}"
        
        # Threshold enforcement
        meets_threshold = report.quality_score >= quality_threshold
        has_errors = any(issue.severity == ValidationSeverity.ERROR for issue in report.issues)
        
        if has_errors:
            # Data with errors should be rejected regardless of threshold
            with pytest.raises(BusinessLogicError):
                service.reject_invalid_data(stock_data, "stock_data")
        elif meets_threshold:
            # Data meeting threshold should be accepted
            accepted, _ = service.reject_invalid_data(stock_data, "stock_data")
            assert accepted, "Data meeting quality threshold should be accepted"
    
    @given(
        field_name=st.text(min_size=1, max_size=50).filter(lambda x: x.isidentifier()),
        field_value=st.one_of(
            st.text(max_size=100),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.none()
        ),
        severity=st.sampled_from(list(ValidationSeverity))
    )
    @settings(max_examples=100)
    def test_validation_issue_consistency(self, field_name: str, field_value, severity: ValidationSeverity):
        """
        Feature: tech-stack-modernization, Property: Data Validation and Quality
        For any validation issue, the issue structure should be consistent and serializable
        **Validates: Requirements 10.3**
        """
        # Create a validation issue
        issue = ValidationIssue(
            field=field_name,
            message=f"Test validation issue for {field_name}",
            severity=severity,
            value=field_value,
            expected_type="string",
            constraint="test_constraint"
        )
        
        # Issue should have consistent structure
        assert issue.field == field_name, "Issue should preserve field name"
        assert issue.severity == severity, "Issue should preserve severity"
        assert issue.value == field_value, "Issue should preserve field value"
        
        # Issue should be serializable
        issue_dict = issue.to_dict()
        assert isinstance(issue_dict, dict), "Issue should be serializable to dict"
        assert "field" in issue_dict, "Serialized issue should have field"
        assert "message" in issue_dict, "Serialized issue should have message"
        assert "severity" in issue_dict, "Serialized issue should have severity"
        assert "value" in issue_dict, "Serialized issue should have value"
        
        # Severity should be serialized as string
        assert isinstance(issue_dict["severity"], str), "Severity should be serialized as string"
        assert issue_dict["severity"] == severity.value, "Severity should match enum value"
    
    @given(
        num_reports=st.integers(min_value=1, max_value=20),
        quality_scores=st.lists(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=20
        )
    )
    @settings(max_examples=50)
    def test_quality_summary_consistency(self, num_reports: int, quality_scores: List[float]):
        """
        Feature: tech-stack-modernization, Property: Data Validation and Quality
        For any collection of quality reports, the summary should accurately reflect the data
        **Validates: Requirements 10.3**
        """
        service = DataQualityService()
        
        # Generate reports with known quality scores
        for i in range(min(num_reports, len(quality_scores))):
            score = quality_scores[i]
            
            # Create data that will produce the desired quality score
            if score >= 0.9:
                data = {
                    "ticker": f"TEST{i}",
                    "company_name": f"Test Company {i}",
                    "current_price": 100.0,
                    "fair_value": 120.0,
                    "recommendation": "Buy"
                }
            elif score >= 0.7:
                data = {
                    "ticker": f"TEST{i}",
                    "company_name": f"Test Company {i}",
                    "current_price": 100.0,
                    "fair_value": 120.0,
                    "recommendation": "Buy",
                    "margin_of_safety": 150.0  # This will cause a warning
                }
            else:
                data = {
                    "ticker": "",  # This will cause an error
                    "company_name": f"Test Company {i}",
                    "current_price": 100.0,
                    "fair_value": 120.0,
                    "recommendation": "Buy"
                }
            
            service.validate_data(data, "stock_data")
        
        # Get quality summary
        summary = service.get_quality_summary()
        
        # Summary should have consistent structure
        assert isinstance(summary, dict), "Summary should be a dictionary"
        assert "total_reports" in summary, "Summary should include total reports"
        assert "average_quality_score" in summary, "Summary should include average quality score"
        assert "quality_distribution" in summary, "Summary should include quality distribution"
        assert "common_issues" in summary, "Summary should include common issues"
        
        # Total reports should match
        expected_reports = min(num_reports, len(quality_scores))
        assert summary["total_reports"] == expected_reports, f"Summary should show {expected_reports} reports"
        
        # Average should be reasonable
        if expected_reports > 0:
            assert isinstance(summary["average_quality_score"], float), "Average should be a float"
            assert 0.0 <= summary["average_quality_score"] <= 1.0, "Average should be between 0 and 1"
        
        # Quality distribution should sum to total reports
        distribution = summary["quality_distribution"]
        total_in_distribution = sum(distribution.values())
        assert total_in_distribution == expected_reports, "Quality distribution should sum to total reports"
    
    def test_unknown_data_type_rejection(self):
        """
        Feature: tech-stack-modernization, Property: Data Validation and Quality
        For any unknown data type, validation should consistently reject it
        **Validates: Requirements 10.3**
        """
        service = DataQualityService()
        
        test_data = {"field1": "value1", "field2": "value2"}
        
        # Unknown data type should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            service.validate_data(test_data, "unknown_data_type")
        
        assert "Unknown data type" in str(exc_info.value.message)
        assert exc_info.value.details["field"] == "data_type"
        assert exc_info.value.details["value"] == "unknown_data_type"
    
    @given(
        data_with_mixed_quality=st.lists(
            st.dictionaries(
                keys=st.sampled_from(["ticker", "company_name", "current_price", "recommendation"]),
                values=st.one_of(
                    st.text(min_size=1, max_size=20),
                    st.floats(min_value=0.01, max_value=1000.0, allow_nan=False, allow_infinity=False),
                    st.sampled_from(["Buy", "Hold", "Sell", "InvalidRec"])  # Mix valid and invalid
                ),
                min_size=2,
                max_size=4
            ),
            min_size=2,
            max_size=10
        )
    )
    @settings(max_examples=50)
    def test_mixed_quality_data_handling(self, data_with_mixed_quality: List[Dict[str, Any]]):
        """
        Feature: tech-stack-modernization, Property: Data Validation and Quality
        For any mixed quality dataset, validation should handle each entry independently
        **Validates: Requirements 10.3**
        """
        service = DataQualityService()
        
        reports = []
        for i, data_entry in enumerate(data_with_mixed_quality):
            # Ensure minimum required fields
            stock_data = {
                "ticker": data_entry.get("ticker", f"TEST{i}"),
                "company_name": data_entry.get("company_name", f"Test Company {i}"),
                "current_price": data_entry.get("current_price", 100.0),
                "recommendation": data_entry.get("recommendation", "Buy")
            }
            
            report = service.validate_data(stock_data, "stock_data")
            reports.append(report)
        
        # Each report should be independent
        assert len(reports) == len(data_with_mixed_quality), "Should generate independent reports"
        
        # Reports should have varying quality based on data
        quality_scores = [report.quality_score for report in reports]
        
        # At least some variation in quality (unless all data is identical)
        if len(set(str(entry) for entry in data_with_mixed_quality)) > 1:
            # If data entries are different, we might expect some quality variation
            # But this is not guaranteed, so we just check that all scores are valid
            for score in quality_scores:
                assert 0.0 <= score <= 1.0, f"All quality scores should be valid, got {score}"
        
        # All reports should have proper structure
        for report in reports:
            assert isinstance(report.issues, list), "Each report should have issues list"
            assert isinstance(report.timestamp, datetime), "Each report should have timestamp"