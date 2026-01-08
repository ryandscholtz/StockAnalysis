"""
Property-based tests for data validation consistency
Feature: tech-stack-modernization, Property 1: Data Validation Consistency
"""
import pytest
from hypothesis import given, strategies as st, settings
from pydantic import ValidationError as PydanticValidationError
from datetime import datetime

from app.api.models import (
    StockAnalysis, QuoteResponse, AnalysisWeights
)
from app.core.exceptions import ValidationError as AppValidationError


class TestDataValidationConsistency:
    """Test that data validation consistently rejects invalid data and accepts valid data"""

    @given(ticker=st.text(min_size=1,
                          max_size=10).filter(lambda x: x.strip()),
           company_name=st.text(min_size=1,
                                max_size=200).filter(lambda x: x.strip()),
           current_price=st.floats(min_value=0.01,
                                   max_value=10000.0,
                                   allow_nan=False,
                                   allow_infinity=False),
           fair_value=st.floats(min_value=0.01,
                                max_value=10000.0,
                                allow_nan=False,
                                allow_infinity=False),
           margin_of_safety=st.floats(min_value=-100.0,
                                      max_value=100.0,
                                      allow_nan=False,
                                      allow_infinity=False),
           recommendation=st.sampled_from(["Strong Buy",
                                           "Buy",
                                           "Hold",
                                           "Avoid"]))
    @settings(max_examples=100)
    def test_stock_analysis_valid_data_acceptance(
        self,
        ticker: str,
        company_name: str,
        current_price: float,
        fair_value: float,
        margin_of_safety: float,
        recommendation: str
    ):
        """
        Feature: tech-stack-modernization, Property 1: Data Validation Consistency
        For any valid data input to the system, validation should consistently accept the data
        **Validates: Requirements 1.3, 10.3**
        """
        # Create valid StockAnalysis data with all required fields
        upside_potential = (fair_value - current_price) / \
            current_price * 100 if current_price > 0 else 0
        price_to_intrinsic = current_price / fair_value if fair_value > 0 else 1.0

        analysis_data = {
            "ticker": ticker,
            "companyName": company_name,
            "currentPrice": current_price,
            "fairValue": fair_value,
            "marginOfSafety": margin_of_safety,
            "upsidePotential": upside_potential,
            "priceToIntrinsicValue": price_to_intrinsic,
            "recommendation": recommendation,
            "recommendationReasoning": f"Based on analysis, {
                recommendation.lower()} recommendation",
            "valuation": {
                "dcf": fair_value * 0.4,
                "earningsPower": fair_value * 0.4,
                "assetBased": fair_value * 0.2,
                "weightedAverage": fair_value},
            "financialHealth": {
                "score": 7.5,
                "metrics": {
                    "debtToEquity": 0.5,
                    "currentRatio": 2.0,
                    "quickRatio": 1.5,
                    "interestCoverage": 10.0,
                    "roe": 0.15,
                    "roic": 0.12,
                    "roa": 0.08,
                    "fcfMargin": 0.10}},
            "businessQuality": {
                "score": 8.0,
                "moatIndicators": [
                    "Brand strength",
                    "Network effects"],
                "competitivePosition": "Strong"},
            "timestamp": datetime.now()}

        # Valid data should pass validation without raising exceptions
        analysis = StockAnalysis(**analysis_data)

        # Verify the data was processed correctly (accounting for trimming and
        # normalization)
        assert analysis.ticker == ticker.strip().upper()
        assert analysis.companyName == company_name.strip()
        assert analysis.currentPrice == current_price
        assert analysis.fairValue == fair_value
        assert analysis.marginOfSafety == margin_of_safety
        assert analysis.recommendation == recommendation

    @given(
        ticker=st.one_of(
            st.just(""),  # Empty string
            st.just("   "),  # Whitespace only
            st.none(),  # None value
            st.text(min_size=11, max_size=50)  # Too long
        ),
        current_price=st.one_of(
            st.floats(max_value=0.0),  # Zero or negative
            st.just(float('nan')),  # NaN
            st.just(float('inf')),  # Infinity
            st.just(float('-inf'))  # Negative infinity
        )
    )
    @settings(max_examples=100)
    def test_stock_analysis_invalid_data_rejection(self, ticker, current_price):
        """
        Feature: tech-stack-modernization, Property 1: Data Validation Consistency
        For any invalid data input to the system, validation should consistently reject the data
        **Validates: Requirements 1.3, 10.3**
        """
        # Create invalid StockAnalysis data
        analysis_data = {
            "ticker": ticker,
            "companyName": "Test Company",
            "currentPrice": current_price,
            "fairValue": 100.0,
            "marginOfSafety": 10.0,
            "upsidePotential": 15.0,
            "priceToIntrinsicValue": 0.85,
            "recommendation": "BUY",
            "recommendationReasoning": "Test reasoning",
            "valuation": {
                "dcf": 40.0,
                "earningsPower": 40.0,
                "assetBased": 20.0,
                "weightedAverage": 100.0
            },
            "financialHealth": {
                "score": 7.5,
                "metrics": {
                    "debtToEquity": 0.5,
                    "currentRatio": 2.0,
                    "quickRatio": 1.5,
                    "interestCoverage": 10.0,
                    "roe": 0.15,
                    "roic": 0.12,
                    "roa": 0.08,
                    "fcfMargin": 0.10
                }
            },
            "businessQuality": {
                "score": 8.0,
                "moatIndicators": ["Brand strength"],
                "competitivePosition": "Strong"
            },
            "timestamp": datetime.now()
        }

        # Invalid data should raise validation errors
        with pytest.raises((PydanticValidationError, ValueError, TypeError)):
            StockAnalysis(**analysis_data)

    @given(
        ticker=st.text(
            min_size=1,
            max_size=10).filter(
            lambda x: x.strip()),
        current_price=st.floats(
            min_value=0.01,
            max_value=10000.0,
            allow_nan=False,
            allow_infinity=False),
        company_name=st.text(
            min_size=1,
            max_size=200).filter(
            lambda x: x.strip()),
        market_cap=st.floats(
            min_value=1000000,
            max_value=1e15,
            allow_nan=False,
            allow_infinity=False))
    @settings(max_examples=100)
    def test_quote_response_valid_data_acceptance(
        self,
        ticker: str,
        current_price: float,
        company_name: str,
        market_cap: float
    ):
        """
        Feature: tech-stack-modernization, Property 1: Data Validation Consistency
        For any valid quote data, validation should consistently accept it
        **Validates: Requirements 1.3, 10.3**
        """
        quote_data = {
            "ticker": ticker,
            "companyName": company_name,
            "currentPrice": current_price,
            "marketCap": market_cap
        }

        # Valid quote data should pass validation
        quote = QuoteResponse(**quote_data)

        # Verify data integrity (accounting for trimming and normalization)
        assert quote.ticker == ticker.strip().upper()
        assert quote.currentPrice == current_price
        assert quote.companyName == company_name.strip()
        assert quote.marketCap == market_cap

    @given(dcf_weight=st.floats(min_value=0.0,
                                max_value=1.0,
                                allow_nan=False,
                                allow_infinity=False),
           epv_weight=st.floats(min_value=0.0,
                                max_value=1.0,
                                allow_nan=False,
                                allow_infinity=False),
           asset_weight=st.floats(min_value=0.0,
                                  max_value=1.0,
                                  allow_nan=False,
                                  allow_infinity=False))
    @settings(max_examples=100)
    def test_analysis_weights_normalization_consistency(
        self,
        dcf_weight: float,
        epv_weight: float,
        asset_weight: float
    ):
        """
        Feature: tech-stack-modernization, Property 1: Data Validation Consistency
        For any valid weight values, normalization should be consistent
        **Validates: Requirements 1.3, 10.3**
        """
        # Skip if all weights are zero (would cause division by zero)
        total = dcf_weight + epv_weight + asset_weight
        if total == 0:
            pytest.skip("All weights are zero - cannot normalize")

        weights_data = {
            "dcf_weight": dcf_weight,
            "epv_weight": epv_weight,
            "asset_weight": asset_weight
        }

        # Valid weights should be accepted
        weights = AnalysisWeights(**weights_data)

        # Verify weights are properly stored
        assert weights.dcf_weight == dcf_weight
        assert weights.epv_weight == epv_weight
        assert weights.asset_weight == asset_weight

    @given(
        invalid_weights=st.one_of(
            st.floats(min_value=-1.0, max_value=-0.01),  # Negative weights
            st.floats(min_value=1.01, max_value=10.0)    # Weights > 1 (but not NaN/inf)
        )
    )
    @settings(max_examples=100)
    def test_analysis_weights_invalid_data_rejection(self, invalid_weights):
        """
        Feature: tech-stack-modernization, Property 1: Data Validation Consistency
        For any invalid weight values, validation should consistently reject them
        **Validates: Requirements 1.3, 10.3**
        """
        weights_data = {
            "dcf_weight": invalid_weights,
            "epv_weight": 0.3,
            "asset_weight": 0.3
        }

        # Invalid weights should raise validation errors
        with pytest.raises((PydanticValidationError, ValueError)):
            AnalysisWeights(**weights_data)

    def test_validation_error_structure_consistency(self):
        """
        Feature: tech-stack-modernization, Property 1: Data Validation Consistency
        Validation errors should have consistent structure
        **Validates: Requirements 1.3, 10.3**
        """
        # Test that our custom validation errors have consistent structure
        error = AppValidationError(
            message="Test validation error",
            field="test_field",
            value="invalid_value"
        )

        assert error.message == "Test validation error"
        assert error.category.value == "validation"
        assert error.status_code == 400
        assert error.details["field"] == "test_field"
        assert error.details["value"] == "invalid_value"
        assert error.correlation_id is not None

    @given(
        field_name=st.text(min_size=1, max_size=50),
        field_value=st.one_of(
            st.text(),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.none()
        )
    )
    @settings(max_examples=100)
    def test_validation_error_field_handling_consistency(
            self, field_name: str, field_value):
        """
        Feature: tech-stack-modernization, Property 1: Data Validation Consistency
        Validation errors should consistently handle different field types
        **Validates: Requirements 1.3, 10.3**
        """
        error = AppValidationError(
            message=f"Invalid value for {field_name}",
            field=field_name,
            value=field_value
        )

        # Error should consistently store field information
        assert error.details["field"] == field_name
        assert error.details["value"] == str(
            field_value)  # Should be converted to string
        assert error.category.value == "validation"
        assert error.status_code == 400
