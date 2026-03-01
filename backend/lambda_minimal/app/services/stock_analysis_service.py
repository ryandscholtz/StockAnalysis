"""
Stock Analysis Service - Business logic layer for stock analysis operations
"""
import time
from typing import Optional, Dict, Any
import logging
from datetime import datetime

from app.core.logging import LoggerMixin
from app.core.exceptions import BusinessLogicError, ValidationError, ExternalAPIError
from app.core.xray_middleware import trace_async_function, create_external_api_subsegment, end_subsegment
from app.data.data_fetcher import DataFetcher
from app.cache_manager import CacheManager
from app.database.db_service import DatabaseService
from app.api.models import StockAnalysis
from app.valuation.intrinsic_value import IntrinsicValueCalculator
from app.analysis.margin_of_safety import MarginOfSafetyCalculator
from app.analysis.financial_health import FinancialHealthAnalyzer
from app.analysis.business_quality import BusinessQualityAnalyzer
from app.analysis.management_quality import ManagementQualityAnalyzer

# Import metrics functions (with fallback if not available)
try:
    from app.core.metrics import record_analysis_completion
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

    async def record_analysis_completion(ticker: str, analysis_type: str, duration_seconds: float, success: bool):
        pass


class StockAnalysisService(LoggerMixin):
    """Service for stock analysis operations with business logic"""

    def __init__(
        self,
        data_fetcher: DataFetcher,
        cache_manager: CacheManager,
        database_service: DatabaseService
    ):
        self.data_fetcher = data_fetcher
        self.cache_manager = cache_manager
        self.database_service = database_service

    @trace_async_function(name="stock_analysis.analyze_stock", annotations={"operation": "analyze", "service": "stock_analysis"})
    async def analyze_stock(
        self,
        ticker: str,
        business_type: Optional[str] = None,
        analysis_weights: Optional[Dict[str, float]] = None,
        use_cache: bool = True
    ) -> StockAnalysis:
        """
        Perform comprehensive stock analysis

        Args:
            ticker: Stock ticker symbol
            business_type: Optional business type override
            analysis_weights: Optional custom analysis weights
            use_cache: Whether to use cached results

        Returns:
            StockAnalysis: Complete analysis results

        Raises:
            ValidationError: If ticker is invalid
            BusinessLogicError: If analysis cannot be performed
            ExternalAPIError: If data fetching fails
        """
        start_time = time.time()
        analysis_type = business_type or "comprehensive"
        success = False

        try:
            # Validate input
            if not ticker or not ticker.strip():
                raise ValidationError(
                    message="Ticker symbol is required",
                    field="ticker",
                    value=ticker
                )

            ticker = ticker.upper().strip()

            # Check cache first
            cache_key = f"analysis:{ticker}:{business_type}:{hash(str(analysis_weights))}"
            if use_cache:
                cached_result = await self._get_cached_analysis(cache_key)
                if cached_result:
                    self.log_info(
                        "Returning cached analysis",
                        ticker=ticker,
                        cache_key=cache_key
                    )
                    success = True
                    return cached_result

            # Fetch company data
            self.log_info("Starting stock analysis", ticker=ticker)
            company_data = await self.data_fetcher.fetch_company_data(ticker)

            if not company_data:
                # Try AI-extracted data as fallback
                ai_data = self.database_service.get_ai_extracted_data(ticker)
                if not ai_data:
                    raise BusinessLogicError(
                        message=f"No data available for ticker {ticker}",
                        context={"ticker": ticker, "data_sources_tried": ["yahoo_finance", "ai_extracted"]}
                    )

                # Create company data from AI-extracted data
                company_data = self._create_company_data_from_ai(ticker, ai_data)

            # Validate we have sufficient data for analysis
            self._validate_company_data(company_data, ticker)

            # Get risk-free rate
            try:
                risk_free_rate = self.data_fetcher.get_risk_free_rate()
            except Exception as e:
                self.log_warning(
                    "Failed to get risk-free rate, using default",
                    ticker=ticker,
                    error=str(e)
                )
                risk_free_rate = 0.04  # Default 4%

            # Perform analysis components
            analysis_result = await self._perform_comprehensive_analysis(
                company_data=company_data,
                risk_free_rate=risk_free_rate,
                business_type=business_type,
                analysis_weights=analysis_weights
            )

            # Cache the result
            if use_cache:
                await self._cache_analysis(cache_key, analysis_result)

            self.log_info(
                "Stock analysis completed successfully",
                ticker=ticker,
                fair_value=analysis_result.fairValue,
                recommendation=analysis_result.recommendation
            )

            success = True
            return analysis_result

        except (ValidationError, BusinessLogicError, ExternalAPIError):
            # Re-raise known exceptions
            raise
        except Exception as e:
            self.log_error(
                "Unexpected error during stock analysis",
                ticker=ticker,
                error=str(e),
                error_type=type(e).__name__
            )
            raise BusinessLogicError(
                message=f"Analysis failed for {ticker}: {str(e)}",
                context={"ticker": ticker, "error_type": type(e).__name__}
            )
        finally:
            # Record metrics regardless of success/failure
            duration_seconds = time.time() - start_time
            if METRICS_AVAILABLE:
                await record_analysis_completion(ticker, analysis_type, duration_seconds, success)

    async def _get_cached_analysis(self, cache_key: str) -> Optional[StockAnalysis]:
        """Get cached analysis result"""
        try:
            cached_data = self.cache_manager.get(cache_key)
            if cached_data:
                return StockAnalysis(**cached_data)
        except Exception as e:
            self.log_warning("Failed to retrieve cached analysis", cache_key=cache_key, error=str(e))
        return None

    async def _cache_analysis(self, cache_key: str, analysis: StockAnalysis) -> None:
        """Cache analysis result"""
        try:
            # Cache for 1 hour
            self.cache_manager.set(cache_key, analysis.dict(), ttl=3600)
        except Exception as e:
            self.log_warning("Failed to cache analysis", cache_key=cache_key, error=str(e))

    def _validate_company_data(self, company_data, ticker: str) -> None:
        """Validate that company data is sufficient for analysis"""
        if not company_data:
            raise BusinessLogicError(
                message=f"No company data available for {ticker}",
                context={"ticker": ticker}
            )

        # Check for minimum required data
        has_financial_data = (
            company_data.income_statement or
            company_data.balance_sheet or
            company_data.cashflow
        )

        if not has_financial_data:
            raise BusinessLogicError(
                message=f"Insufficient financial data for analysis of {ticker}",
                context={
                    "ticker": ticker,
                    "has_income_statement": bool(company_data.income_statement),
                    "has_balance_sheet": bool(company_data.balance_sheet),
                    "has_cashflow": bool(company_data.cashflow)
                }
            )

        if not company_data.current_price or company_data.current_price <= 0:
            raise BusinessLogicError(
                message=f"Invalid or missing current price for {ticker}",
                context={"ticker": ticker, "current_price": company_data.current_price}
            )

    def _create_company_data_from_ai(self, ticker: str, ai_data: Dict[str, Any]):
        """Create CompanyData from AI-extracted data"""
        # This would implement the logic to create CompanyData from AI data
        # For now, raise an error indicating this needs implementation
        raise BusinessLogicError(
            message="AI-extracted data processing not yet implemented",
            context={"ticker": ticker, "ai_data_keys": list(ai_data.keys())}
        )

    @trace_async_function(name="stock_analysis.perform_comprehensive_analysis", annotations={"operation": "analysis", "service": "stock_analysis"})
    async def _perform_comprehensive_analysis(
        self,
        company_data,
        risk_free_rate: float,
        business_type: Optional[str],
        analysis_weights: Optional[Dict[str, float]]
    ) -> StockAnalysis:
        """Perform the comprehensive analysis workflow"""

        # Analyze financial health
        health_analyzer = FinancialHealthAnalyzer(company_data)
        health_result = health_analyzer.analyze()

        # Analyze business quality
        quality_analyzer = BusinessQualityAnalyzer(company_data)
        quality_result = quality_analyzer.analyze()

        # Analyze management quality
        management_analyzer = ManagementQualityAnalyzer(company_data)
        management_result = management_analyzer.analyze()

        # Determine business type and weights
        from app.config.analysis_weights import AnalysisWeightPresets, BusinessType, AnalysisWeights

        if not business_type:
            # Auto-detect business type
            business_type_enum = AnalysisWeightPresets.detect_business_type(
                company_data.sector,
                company_data.industry,
                0.0,  # revenue_growth - would calculate this
                0.0   # asset_intensity - would calculate this
            )
            business_type = business_type_enum.value

        # Get analysis weights
        if analysis_weights:
            weights = AnalysisWeights.from_dict(analysis_weights)
            weights.normalize()
        else:
            try:
                business_type_enum = BusinessType(business_type)
            except ValueError:
                business_type_enum = BusinessType.DEFAULT
            weights = AnalysisWeightPresets.get_preset(business_type_enum)

        # Calculate intrinsic value
        intrinsic_calc = IntrinsicValueCalculator(company_data, risk_free_rate)

        # Override weights method
        original_get_weights = intrinsic_calc.get_weights
        def custom_get_weights(bt):
            return (weights.dcf_weight, weights.epv_weight, weights.asset_weight)
        intrinsic_calc.get_weights = custom_get_weights

        valuation_result = intrinsic_calc.calculate(
            business_quality_score=quality_result.score,
            financial_health_score=health_result.score
        )

        # Calculate margin of safety
        margin_calc = MarginOfSafetyCalculator(
            current_price=company_data.current_price,
            fair_value=valuation_result.fair_value
        )
        margin_result = margin_calc.calculate(
            business_quality_score=quality_result.score,
            financial_health_score=health_result.score,
            beta=company_data.beta or 1.0,
            market_cap=company_data.market_cap
        )

        # Build the analysis result
        # This is a simplified version - the full implementation would include all fields
        analysis = StockAnalysis(
            ticker=company_data.ticker,
            companyName=company_data.company_name,
            currentPrice=company_data.current_price,
            fairValue=valuation_result.fair_value,
            marginOfSafety=margin_result.margin_of_safety_percent,
            recommendation=margin_result.recommendation,
            # Add other required fields...
        )

        return analysis
