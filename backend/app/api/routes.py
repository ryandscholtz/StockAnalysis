"""
API routes for stock analysis
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, AsyncGenerator, Optional
import json
import asyncio
import math
import logging
import base64
import io

logger = logging.getLogger(__name__)
from app.api.models import StockAnalysis, QuoteResponse, CompareRequest, CompareResponse, MissingDataInfo, ManualDataEntry, ManualDataResponse, DataQualityWarning, GrowthMetrics, PriceRatios, PDFJobResponse, PDFJobStatusResponse
from pydantic import BaseModel
from typing import List as ListType
from app.api.progress import ProgressTracker
from app.data.data_fetcher import DataFetcher
from app.data.api_client import YahooFinanceClient
from app.data.pdf_extractor import PDFExtractor
from app.valuation.intrinsic_value import IntrinsicValueCalculator
from app.analysis.margin_of_safety import MarginOfSafetyCalculator
from app.analysis.financial_health import FinancialHealthAnalyzer
from app.analysis.business_quality import BusinessQualityAnalyzer
from app.analysis.management_quality import ManagementQualityAnalyzer
from app.analysis.growth_metrics import GrowthMetricsCalculator
from app.analysis.price_ratios import PriceRatiosCalculator
from app.analysis.data_quality import DataQualityAnalyzer

router = APIRouter()

def _format_api_attempts_comment(api_attempts: list, success: bool = False) -> str:
    """Format API attempts into a detailed comment for the frontend"""
    if not api_attempts:
        return "No API attempt details available"
    
    if success:
        # For successful requests, show what worked
        successful_attempts = [attempt for attempt in api_attempts if attempt.get('status') == 'success']
        if successful_attempts:
            methods = [attempt.get('method', 'Unknown method') for attempt in successful_attempts]
            return f"✅ Success using: {', '.join(methods)}"
        else:
            return "✅ Success (method details unavailable)"
    else:
        # For failed requests, show detailed breakdown of what was tried
        comment_parts = []
        
        # Group attempts by API
        api_groups = {}
        for attempt in api_attempts:
            api_name = attempt.get('api', 'Unknown API')
            if api_name not in api_groups:
                api_groups[api_name] = []
            api_groups[api_name].append(attempt)
        
        for api_name, attempts in api_groups.items():
            failed_attempts = [a for a in attempts if a.get('status') == 'failed']
            if failed_attempts:
                errors = []
                for attempt in failed_attempts:
                    method = attempt.get('method', 'unknown')
                    error = attempt.get('error', 'unknown error')
                    errors.append(f"{method}: {error}")
                
                comment_parts.append(f"❌ {api_name} - {'; '.join(errors)}")
        
        if comment_parts:
            return " | ".join(comment_parts)
        else:
            return "❌ All API methods failed (no details available)"

# Test route to verify router is working
@router.get("/test-batch-route")
async def test_batch_route():
    return {"message": "Batch route test - router is working"}


@router.get("/version")
async def get_version():
    """Get backend version information"""
    from app.core.app import BUILD_TIMESTAMP
    return {
        "version": BUILD_TIMESTAMP,
        "build_time": BUILD_TIMESTAMP
    }


@router.get("/analysis-presets")
async def get_analysis_presets():
    """Get available business type presets and their default weights"""
    from app.config.analysis_weights import BusinessType, AnalysisWeightPresets
    
    presets = {}
    for business_type in BusinessType:
        weights = AnalysisWeightPresets.get_preset(business_type)
        presets[business_type.value] = weights.to_dict()
    
    return {
        "presets": presets,
        "business_types": [bt.value for bt in BusinessType]
    }

# In-memory storage for manual data (in production, use a database)
manual_data_store: dict = {}


@router.get("/search")
async def search_tickers(q: str = Query(..., min_length=1, description="Search query")):
    """
    Search for ticker symbols and company names
    Returns list of matching stocks
    """
    try:
        yahoo_client = YahooFinanceClient()
        # Run synchronous search in executor to avoid blocking
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, yahoo_client.search_tickers, q)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _analyze_stock_with_progress(ticker: str, progress_tracker: ProgressTracker, 
                                       business_type: Optional[str] = None,
                                       analysis_weights: Optional[dict] = None) -> StockAnalysis:
    """Internal function to perform analysis with progress tracking"""
    # Step 1: Fetch company data
    await progress_tracker.update(1, "Fetching company data and financial statements...")
    # Small delay to ensure progress update is sent before potentially blocking operation
    await asyncio.sleep(0.1)
    data_fetcher = DataFetcher()
    try:
        company_data = await data_fetcher.fetch_company_data(ticker)
        if company_data:
            logger.info(f"Successfully fetched company data for {ticker}")
        else:
            logger.warning(f"fetch_company_data returned None for {ticker} - may be rate-limited or ticker not found")
    except Exception as e:
        logger.error(f"Error fetching company data for {ticker}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        company_data = None
    
    # Check if we have AI-extracted data as fallback
    await progress_tracker.update(1, "Checking for AI-extracted data...")
    ai_data = {}
    try:
        from app.database.db_service import DatabaseService
        from app.data.data_fetcher import CompanyData
        db_service = DatabaseService(db_path="stock_analysis.db")
        ai_data = db_service.get_ai_extracted_data(ticker)
        logger.info(f"Checked AI-extracted data for {ticker}: Found {len(ai_data)} data types")
        if ai_data:
            await progress_tracker.update(1, f"Found AI-extracted data ({len(ai_data)} data types)...")
    except Exception as e:
        logger.warning(f"Error checking AI-extracted data for {ticker}: {e}")
        import traceback
        logger.warning(traceback.format_exc())
        # Continue without AI data if database check fails
    
    if not company_data:
        # If Yahoo Finance doesn't have the ticker, try to create CompanyData from AI-extracted data
        if ai_data and (ai_data.get('income_statement') or ai_data.get('balance_sheet') or ai_data.get('cashflow')):
            await progress_tracker.update(1, "Creating CompanyData from AI-extracted data...")
            logger.info(f"Ticker {ticker} not found in Yahoo Finance, but AI-extracted data exists. Creating CompanyData from AI data.")
            logger.info(f"AI data keys: {list(ai_data.keys())}")
            # Create minimal CompanyData from AI-extracted data
            # We need at least a current_price - try to get it from a quote or use a placeholder
            await progress_tracker.update(1, "Getting current price...")
            current_price = None
            try:
                yahoo_client = YahooFinanceClient()
                yf_ticker = yahoo_client.get_ticker(ticker)
                current_price = yahoo_client.get_current_price(yf_ticker) if yf_ticker else None
            except Exception as e:
                logger.warning(f"Could not get price from Yahoo Finance: {e}")
                current_price = None
            
            # If we still don't have a price, we can't do full analysis, but we can still try
            if not current_price:
                logger.warning(f"Could not get current price for {ticker}. Using placeholder price for analysis.")
                # Use a placeholder price - the analysis will still work with AI data
                current_price = 1.0  # Placeholder
            
            await progress_tracker.update(1, "Building CompanyData object from AI data...")
            try:
                company_data = CompanyData(
                    ticker=ticker.upper(),
                    company_name=ticker.upper(),
                    current_price=current_price,
                    income_statement=ai_data.get('income_statement', {}),
                    balance_sheet=ai_data.get('balance_sheet', {}),
                    cashflow=ai_data.get('cashflow', {}),
                    currency='USD',
                    financial_currency='USD'
                )
                
                # Apply key metrics from AI data if available
                if 'key_metrics' in ai_data and 'latest' in ai_data['key_metrics']:
                    metrics = ai_data['key_metrics']['latest']
                    if 'shares_outstanding' in metrics:
                        company_data.shares_outstanding = metrics['shares_outstanding']
                    if 'market_cap' in metrics:
                        company_data.market_cap = metrics['market_cap']
                
                logger.info(f"Created CompanyData from AI-extracted data for {ticker}")
                logger.info(f"Income statement periods: {len(company_data.income_statement)}")
                logger.info(f"Balance sheet periods: {len(company_data.balance_sheet)}")
                logger.info(f"Cashflow periods: {len(company_data.cashflow)}")
                await progress_tracker.update(1, f"CompanyData created: {len(company_data.income_statement)} income, {len(company_data.balance_sheet)} balance, {len(company_data.cashflow)} cashflow periods")
            except Exception as e:
                logger.error(f"Error creating CompanyData from AI data: {e}")
                import traceback
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail=f"Error creating CompanyData from AI-extracted data: {str(e)}")
        else:
            ai_data_summary = f"AI data available: {bool(ai_data)}"
            if ai_data:
                ai_data_summary += f", keys: {list(ai_data.keys())}"
            logger.warning(f"Ticker {ticker} not found. {ai_data_summary}")
            # Provide more helpful error message
            error_detail = f"Ticker {ticker} not found in any data source"
            if not ai_data:
                error_detail += " and no AI-extracted data available. "
                # Check if this is an international ticker
                exchange_suffixes = ['.JO', '.L', '.TO', '.PA', '.DE', '.HK', '.SS', '.SZ', '.T', '.AS', '.BR', '.MX', '.SA', '.SW', '.VI', '.ST', '.OL', '.CO', '.HE', '.IC', '.LS', '.MC', '.MI', '.NX', '.TA', '.TW', '.V', '.WA']
                is_international = any(ticker.upper().endswith(suffix) for suffix in exchange_suffixes)
                
                # Check if backup sources are configured
                from app.data.backup_clients import BackupDataFetcher
                backup_fetcher = BackupDataFetcher()
                has_backup = ((backup_fetcher.alpha_vantage_client and backup_fetcher.alpha_vantage_client.api_key) or 
                             backup_fetcher.fmp_client.api_key or 
                             backup_fetcher.marketstack_client.api_key)
                
                if is_international:
                    error_detail += "For international tickers, the system tried Yahoo Finance first (which supports international exchanges), "
                    error_detail += "then Google Finance and other backup APIs, but none returned data. "
                    error_detail += "This may be due to: (1) Invalid ticker symbol, (2) Ticker not available on any data source, (3) Network connectivity issues, or (4) API rate limits. "
                else:
                    if not has_backup:
                        error_detail += "Note: Backup data sources (Alpha Vantage, Financial Modeling Prep, MarketStack) are not configured. "
                        error_detail += "Consider setting ALPHA_VANTAGE_API_KEY, FMP_API_KEY, or MARKETSTACK_API_KEY environment variables. "
                    else:
                        error_detail += "The system tried backup APIs (Alpha Vantage, MarketStack) first, then Yahoo Finance, but none returned data. "
                    error_detail += "This may be due to: (1) Invalid ticker symbol, (2) Network connectivity issues, or (3) All APIs rate-limited. "
                error_detail += "For custom/private companies, please upload a PDF financial statement first."
            else:
                error_detail += f". AI-extracted data exists but is incomplete (keys: {list(ai_data.keys())}). Please ensure income_statement, balance_sheet, or cashflow data is available."
            raise HTTPException(status_code=404, detail=error_detail)
    
    # Apply manual data if available (in-memory store - backward compatibility)
    if ticker.upper() in manual_data_store:
        manual_data = manual_data_store[ticker.upper()]
        _apply_manual_data(company_data, manual_data)
    
    # Also load AI-extracted data from database and apply it
    if ai_data:
        await progress_tracker.update(1, "Applying AI-extracted data to company data...")
        logger.info(f"=== Loading AI-extracted data from database for {ticker} ===")
        logger.info(f"AI data keys: {list(ai_data.keys())}")
        if 'key_metrics' in ai_data:
            logger.info(f"Key metrics structure: {ai_data['key_metrics']}")
        # Apply AI-extracted data to company_data (will merge with Yahoo Finance data if available)
        logger.info(f"BEFORE applying: shares_outstanding={company_data.shares_outstanding}, market_cap={company_data.market_cap}")
        _apply_ai_extracted_data(company_data, ai_data)
        logger.info(f"Loaded and applied AI-extracted data from database for {ticker}")
        # Log key metrics specifically for debugging
        if 'key_metrics' in ai_data:
            logger.info(f"Key metrics in AI data: {ai_data['key_metrics']}")
        logger.info(f"AFTER applying: shares_outstanding={company_data.shares_outstanding}, market_cap={company_data.market_cap}")
    
    # Log data availability for debugging
    await progress_tracker.update(1, "Data preparation complete, starting analysis...")
    logger.info(f"\n=== Data Availability for {ticker} ===")
    logger.info(f"Income statements: {len(company_data.income_statement)} periods")
    logger.info(f"Balance sheets: {len(company_data.balance_sheet)} periods")
    logger.info(f"Cash flow statements: {len(company_data.cashflow)} periods")
    logger.info(f"Key metrics - shares_outstanding: {company_data.shares_outstanding}, market_cap: {company_data.market_cap}")
    
    # Validate we have at least some data
    if not company_data.income_statement and not company_data.balance_sheet and not company_data.cashflow:
        error_msg = f"No financial data available for {ticker}. Cannot perform analysis."
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    
    if company_data.income_statement:
        first_period = list(company_data.income_statement.values())[0]
        if isinstance(first_period, dict):
            logger.info(f"Income statement keys (sample): {list(first_period.keys())[:10]}")
    if company_data.cashflow:
        first_period = list(company_data.cashflow.values())[0]
        if isinstance(first_period, dict):
            logger.info(f"Cash flow keys (sample): {list(first_period.keys())[:10]}")
    logger.info("=" * 50)
    
    # Step 2: Get risk-free rate
    await progress_tracker.update(2, "Getting market data (risk-free rate)...")
    await asyncio.sleep(0.1)
    try:
        risk_free_rate = data_fetcher.get_risk_free_rate()
        await progress_tracker.update(2, f"Risk-free rate: {risk_free_rate*100:.2f}%")
    except Exception as e:
        logger.warning(f"Error getting risk-free rate: {e}. Using default 4%")
        risk_free_rate = 0.04  # Default 4%
        await progress_tracker.update(2, "Using default risk-free rate (4%)")
    
    # Step 3: Analyze financial health (needed for valuation)
    await progress_tracker.update(3, "Analyzing financial health and ratios...")
    await asyncio.sleep(0.1)
    try:
        health_analyzer = FinancialHealthAnalyzer(company_data)
        health_result = health_analyzer.analyze()
        await progress_tracker.update(3, f"Financial health score: {health_result.score:.1f}/10")
    except Exception as e:
        logger.error(f"Error analyzing financial health: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    
    # Step 4: Analyze business quality (needed for valuation)
    await progress_tracker.update(4, "Assessing business quality and competitive moats...")
    await asyncio.sleep(0.1)
    try:
        quality_analyzer = BusinessQualityAnalyzer(company_data)
        quality_result = quality_analyzer.analyze()
        await progress_tracker.update(4, f"Business quality score: {quality_result.score:.1f}/10")
    except Exception as e:
        logger.error(f"Error analyzing business quality: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    
    # Step 5: Determine business type and get analysis weights
    await progress_tracker.update(5, "Determining business type and analysis weights...")
    await asyncio.sleep(0.1)
    
    from app.config.analysis_weights import AnalysisWeightPresets, BusinessType, AnalysisWeights
    
    # Calculate revenue growth for business type detection
    revenue_growth = 0.0
    asset_intensity = 0.0
    if company_data.income_statement and len(company_data.income_statement) >= 2:
        sorted_dates = sorted(company_data.income_statement.keys(), reverse=True)
        if len(sorted_dates) >= 2:
            latest = company_data.income_statement[sorted_dates[0]]
            previous = company_data.income_statement[sorted_dates[1]]
            if isinstance(latest, dict) and isinstance(previous, dict):
                latest_rev = latest.get('Total Revenue', 0) or latest.get('Revenue', 0) or 0
                prev_rev = previous.get('Total Revenue', 0) or previous.get('Revenue', 0) or 0
                if prev_rev > 0:
                    revenue_growth = (latest_rev - prev_rev) / prev_rev
    
    if company_data.balance_sheet and company_data.income_statement:
        sorted_bs_dates = sorted(company_data.balance_sheet.keys(), reverse=True)
        sorted_is_dates = sorted(company_data.income_statement.keys(), reverse=True)
        if sorted_bs_dates and sorted_is_dates:
            latest_bs = company_data.balance_sheet[sorted_bs_dates[0]]
            latest_is = company_data.income_statement[sorted_is_dates[0]]
            if isinstance(latest_bs, dict) and isinstance(latest_is, dict):
                total_assets = latest_bs.get('Total Assets', 0) or 0
                revenue = latest_is.get('Total Revenue', 0) or latest_is.get('Revenue', 0) or 0
                if revenue > 0:
                    asset_intensity = total_assets / revenue
    
    # Detect or use provided business type
    detected_business_type = business_type
    if not detected_business_type:
        # Try AI-powered detection first, then fallback to rule-based
        try:
            from app.ai.business_type_detector import BusinessTypeDetector
            detector = BusinessTypeDetector()
            company_info = {
                'company_name': company_data.company_name,
                'sector': company_data.sector,
                'industry': company_data.industry,
                'description': '',  # Could fetch from API if needed
                'business_summary': '',
                'revenue_growth': revenue_growth,
                'asset_intensity': asset_intensity
            }
            detected_business_type_enum = detector.detect_with_fallback(
                company_info=company_info,
                sector=company_data.sector,
                industry=company_data.industry,
                revenue_growth=revenue_growth,
                asset_intensity=asset_intensity
            )
            detected_business_type = detected_business_type_enum.value
            logger.info(f"AI detected business type for {ticker}: {detected_business_type}")
        except Exception as e:
            logger.warning(f"Error in AI business type detection for {ticker}: {e}, using rule-based detection")
            detected_business_type = AnalysisWeightPresets.detect_business_type(
                company_data.sector, company_data.industry, revenue_growth, asset_intensity
            ).value
    
    # Get weights (use provided or preset)
    weights = None
    if analysis_weights:
        weights = AnalysisWeights.from_dict(analysis_weights)
        weights.normalize()
    else:
        try:
            business_type_enum = BusinessType(detected_business_type)
        except ValueError:
            business_type_enum = BusinessType.DEFAULT
        weights = AnalysisWeightPresets.get_preset(business_type_enum)
    
    await progress_tracker.update(5, f"Business type: {detected_business_type}, using custom weights" if analysis_weights else f"Business type: {detected_business_type}")
    
    # Step 6: Calculate DCF valuation (with quality scores and custom weights)
    await progress_tracker.update(6, "Calculating Discounted Cash Flow (DCF) model...")
    await asyncio.sleep(0.1)
    try:
        intrinsic_calc = IntrinsicValueCalculator(company_data, risk_free_rate)
        # Override get_weights method to use custom weights
        original_get_weights = intrinsic_calc.get_weights
        def custom_get_weights(bt):
            return (weights.dcf_weight, weights.epv_weight, weights.asset_weight)
        intrinsic_calc.get_weights = custom_get_weights
        valuation_result = intrinsic_calc.calculate(
            business_quality_score=quality_result.score,
            financial_health_score=health_result.score
        )
        await progress_tracker.update(6, f"DCF fair value: ${valuation_result.fair_value:.2f}")
    except Exception as e:
        logger.error(f"Error calculating DCF: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    
    # Step 7: Calculate margin of safety
    await progress_tracker.update(7, "Calculating margin of safety and investment recommendation...")
    await asyncio.sleep(0.1)
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
    
    # Step 8: Analyze management quality
    await progress_tracker.update(8, "Evaluating management quality...")
    await asyncio.sleep(0.1)
    management_analyzer = ManagementQualityAnalyzer(company_data)
    management_result = management_analyzer.analyze()
    
    # Step 9: Calculate growth metrics and price ratios
    await progress_tracker.update(9, "Calculating growth metrics and valuation ratios...")
    
    # Step 10: Run specialized analyzers if applicable
    bank_metrics = None
    reit_metrics = None
    insurance_metrics = None
    
    if detected_business_type == 'bank':
        await progress_tracker.update(10, "Running bank-specific analysis...")
        try:
            from app.analysis.bank_analysis import BankAnalyzer
            from app.api.models import BankMetrics as BankMetricsModel
            bank_analyzer = BankAnalyzer(company_data)
            bank_result = bank_analyzer.analyze()
            bank_metrics = BankMetricsModel(**bank_result.__dict__)
        except Exception as e:
            logger.warning(f"Error in bank analysis: {e}")
    elif detected_business_type == 'reit':
        await progress_tracker.update(10, "Running REIT-specific analysis...")
        try:
            from app.analysis.reit_analysis import REITAnalyzer
            from app.api.models import REITMetrics as REITMetricsModel
            reit_analyzer = REITAnalyzer(company_data)
            reit_result = reit_analyzer.analyze()
            reit_metrics = REITMetricsModel(**reit_result.__dict__)
        except Exception as e:
            logger.warning(f"Error in REIT analysis: {e}")
    elif detected_business_type == 'insurance':
        await progress_tracker.update(10, "Running insurance-specific analysis...")
        try:
            from app.analysis.insurance_analysis import InsuranceAnalyzer
            from app.api.models import InsuranceMetrics as InsuranceMetricsModel
            insurance_analyzer = InsuranceAnalyzer(company_data)
            insurance_result = insurance_analyzer.analyze()
            insurance_metrics = InsuranceMetricsModel(**insurance_result.__dict__)
        except Exception as e:
            logger.warning(f"Error in insurance analysis: {e}")
    else:
        await progress_tracker.update(10, "Standard analysis complete...")
    await asyncio.sleep(0.1)
    growth_calculator = GrowthMetricsCalculator(company_data)
    growth_metrics_dict = growth_calculator.calculate()
    growth_metrics = GrowthMetrics(**growth_metrics_dict) if any(v is not None for v in growth_metrics_dict.values()) else None
    
    price_ratios_calculator = PriceRatiosCalculator(company_data)
    price_ratios_dict = price_ratios_calculator.calculate()
    price_ratios = PriceRatios(**price_ratios_dict) if any(v is not None for v in price_ratios_dict.values()) else None
    
    # Build response
    from datetime import datetime
    from dataclasses import asdict
    
    # Check for missing data (after all data has been applied)
    logger.info(f"=== Checking for missing data ===")
    logger.info(f"Before identify_missing_data: shares_outstanding={company_data.shares_outstanding}, market_cap={company_data.market_cap}")
    missing = data_fetcher.data_agent.identify_missing_data(company_data)
    logger.info(f"Missing data identified: {missing}")
    # Always include missing data info if fair value is 0 or if there's missing data
    has_missing = any(missing.values()) or valuation_result.fair_value == 0
    missing_data_info = None
    if has_missing:
        missing_data_info = MissingDataInfo(
            income_statement=missing.get('income_statement', []),
            balance_sheet=missing.get('balance_sheet', []),
            cashflow=missing.get('cashflow', []),
            key_metrics=missing.get('key_metrics', []),
            has_missing_data=True
        )
    
    # Analyze data quality and identify assumptions
    # Log key metrics before quality check for debugging
    logger.info(f"=== Before DataQualityAnalyzer ===")
    logger.info(f"shares_outstanding: {company_data.shares_outstanding} (type: {type(company_data.shares_outstanding)}, is None: {company_data.shares_outstanding is None})")
    logger.info(f"market_cap: {company_data.market_cap} (type: {type(company_data.market_cap)}, is None: {company_data.market_cap is None})")
    logger.info(f"current_price: {company_data.current_price}")
    logger.info(f"Income statement periods: {len(company_data.income_statement) if company_data.income_statement else 0}")
    logger.info(f"Balance sheet periods: {len(company_data.balance_sheet) if company_data.balance_sheet else 0}")
    logger.info(f"Cash flow periods: {len(company_data.cashflow) if company_data.cashflow else 0}")
    if company_data.income_statement:
        sample_period = next(iter(company_data.income_statement.values()))
        if isinstance(sample_period, dict):
            logger.info(f"Income statement sample keys: {list(sample_period.keys())[:10]}")
    quality_analyzer = DataQualityAnalyzer(company_data)
    quality_warnings = quality_analyzer.analyze()
    data_quality_warnings = [DataQualityWarning(**w.__dict__) for w in quality_warnings] if quality_warnings else None
    logger.info(f"DataQualityAnalyzer found {len(quality_warnings) if quality_warnings else 0} warnings")
    if quality_warnings:
        for warning in quality_warnings:
            logger.info(f"  Warning: {warning.field} - {warning.message} (severity: {warning.severity}, category: {warning.category})")
    
    # Convert dataclass to dict for Pydantic, handling NaN values
    valuation_dict = asdict(valuation_result.breakdown)
    # Replace NaN with 0.0 for Pydantic validation
    for key, value in valuation_dict.items():
        if isinstance(value, float) and math.isnan(value):
            valuation_dict[key] = 0.0
    
    # Convert weights to API model
    from app.api.models import AnalysisWeights as AnalysisWeightsModel
    weights_model = AnalysisWeightsModel(**weights.to_dict())
    
    analysis = StockAnalysis(
        ticker=ticker.upper(),
        companyName=company_data.company_name,
        currentPrice=company_data.current_price,
        fairValue=valuation_result.fair_value,
        marginOfSafety=margin_result.margin_of_safety,
        upsidePotential=margin_result.upside_potential,
        priceToIntrinsicValue=margin_result.price_to_intrinsic_value,
        recommendation=margin_result.recommendation,
        recommendationReasoning=margin_result.reasoning,
        valuation=valuation_dict,
        financialHealth=health_result,
        businessQuality=quality_result,
        managementQuality=management_result,
        growthMetrics=growth_metrics,
        priceRatios=price_ratios,
        currency=company_data.currency,
        financialCurrency=company_data.financial_currency,
        timestamp=datetime.now(),
        missingData=missing_data_info,
        dataQualityWarnings=data_quality_warnings,
        businessType=detected_business_type,
        analysisWeights=weights_model,
        bankMetrics=bank_metrics,
        reitMetrics=reit_metrics,
        insuranceMetrics=insurance_metrics
    )
    
    return analysis


def _apply_manual_data(company_data, manual_data: dict):
    """Apply manually entered data to company_data"""
    for entry in manual_data.values():
        data_type = entry.get('data_type')
        period = entry.get('period')
        data = entry.get('data', {})
        
        if data_type == 'income_statement':
            if period not in company_data.income_statement:
                company_data.income_statement[period] = {}
            company_data.income_statement[period].update(data)
        elif data_type == 'balance_sheet':
            if period not in company_data.balance_sheet:
                company_data.balance_sheet[period] = {}
            company_data.balance_sheet[period].update(data)
        elif data_type == 'cashflow':
            if period not in company_data.cashflow:
                company_data.cashflow[period] = {}
            company_data.cashflow[period].update(data)
        elif data_type == 'key_metrics':
            if 'shares_outstanding' in data:
                company_data.shares_outstanding = data['shares_outstanding']
            if 'market_cap' in data:
                company_data.market_cap = data['market_cap']


def _apply_ai_extracted_data(company_data, ai_data: dict):
    """Apply AI-extracted data from database to company_data"""
    # Apply income statement data
    if 'income_statement' in ai_data:
        for period, data in ai_data['income_statement'].items():
            if period not in company_data.income_statement:
                company_data.income_statement[period] = {}
            company_data.income_statement[period].update(data)
    
    # Apply balance sheet data
    if 'balance_sheet' in ai_data:
        for period, data in ai_data['balance_sheet'].items():
            if period not in company_data.balance_sheet:
                company_data.balance_sheet[period] = {}
            company_data.balance_sheet[period].update(data)
    
    # Apply cash flow data
    if 'cashflow' in ai_data:
        for period, data in ai_data['cashflow'].items():
            if period not in company_data.cashflow:
                company_data.cashflow[period] = {}
            company_data.cashflow[period].update(data)
    
    # Apply key metrics
    if 'key_metrics' in ai_data:
        logger.info(f"Found key_metrics in AI data: {ai_data['key_metrics']}")
        if 'latest' in ai_data['key_metrics']:
            metrics = ai_data['key_metrics']['latest']
            logger.info(f"Applying key_metrics from 'latest': {metrics}")
            if 'shares_outstanding' in metrics:
                old_value = company_data.shares_outstanding
                company_data.shares_outstanding = metrics['shares_outstanding']
                logger.info(f"Set shares_outstanding: {old_value} -> {company_data.shares_outstanding}")
            if 'market_cap' in metrics:
                old_value = company_data.market_cap
                company_data.market_cap = metrics['market_cap']
                logger.info(f"Set market_cap: {old_value} -> {company_data.market_cap}")
        else:
            logger.warning(f"key_metrics found but 'latest' key not present. Keys: {list(ai_data['key_metrics'].keys())}")
    else:
        logger.info("No key_metrics found in AI data")


@router.get("/analyze/{ticker}")
async def analyze_stock(
    ticker: str, 
    stream: bool = Query(False, description="Stream progress updates"), 
    force_refresh: bool = Query(False, description="Force new analysis even if cached"),
    business_type: Optional[str] = Query(None, description="Business type preset (e.g., 'bank', 'reit', 'insurance')"),
    weights: Optional[str] = Query(None, description="JSON-encoded analysis weights")
):
    """
    Perform comprehensive stock analysis for a given ticker
    Use ?stream=true for progress updates via Server-Sent Events
    Use ?force_refresh=true to bypass database cache and run new analysis
    """
    # Normalize ticker: convert hyphens back to dots for international exchanges
    # Common exchange suffixes (e.g., MRF-JO -> MRF.JO for Johannesburg)
    exchange_suffixes = ['JO', 'L', 'TO', 'PA', 'DE', 'HK', 'SS', 'SZ', 'T', 'AS', 'BR', 'MX', 'SA', 'SW', 'VI', 'ST', 'OL', 'CO', 'HE', 'IC', 'LS', 'MC', 'MI', 'NX', 'TA', 'TW', 'V', 'WA']
    ticker_upper = ticker.upper()
    for suffix in exchange_suffixes:
        if ticker_upper.endswith(f'-{suffix}'):
            ticker = ticker_upper[:-len(suffix)-1] + '.' + suffix
            break
    
    # Check database first (unless force_refresh is True)
    if not force_refresh:
        try:
            from app.database.db_service import DatabaseService
            from datetime import date, datetime
            db_service = DatabaseService(db_path="stock_analysis.db")
            
            # First check if we have analysis for today
            today = date.today().isoformat()
            existing_analysis = db_service.get_analysis(ticker, today)
            
            if existing_analysis and existing_analysis.get('status') == 'success':
                logger.info(f"Found fresh analysis for {ticker} from today ({today}), returning cached result")
                analysis_data = existing_analysis.get('analysis_data', {})
                if analysis_data:
                    from app.api.models import StockAnalysis
                    try:
                        cached_analysis = StockAnalysis(**analysis_data)
                        if stream:
                            async def generate_cached():
                                complete_data = {'type': 'complete', 'data': cached_analysis.model_dump(mode='json'), 'cached': True, 'cache_date': today}
                                yield f"data: {json.dumps(complete_data)}\n\n"
                            return StreamingResponse(generate_cached(), media_type="text/event-stream")
                        else:
                            return cached_analysis
                    except Exception as e:
                        logger.warning(f"Error converting cached analysis to model: {e}, will run new analysis")
            else:
                # Check if we have any analysis from a previous date
                latest_analysis = db_service.get_latest_analysis(ticker)
                if latest_analysis:
                    analysis_date = latest_analysis.get('analysis_date')
                    logger.info(f"Found analysis for {ticker} from {analysis_date}, but not from today ({today}). Running fresh analysis.")
                else:
                    logger.info(f"No previous analysis found for {ticker}. Running fresh analysis.")
                    
        except Exception as e:
            logger.warning(f"Error checking database for cached analysis: {e}, will run new analysis")
            import traceback
            logger.warning(traceback.format_exc())
    
    if stream:
        # Stream progress via SSE
        async def generate() -> AsyncGenerator[str, None]:
            progress_queue = asyncio.Queue()
            progress_tracker = ProgressTracker(total_steps=10)
            
            async def progress_callback(update: dict):
                try:
                    await progress_queue.put(update)
                    logger.debug(f"Progress callback: Added update to queue - Step {update.get('step')}, Task: {update.get('task')}")
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")
                    import traceback
                    traceback.print_exc()
            
            progress_tracker.set_callback(progress_callback)
            
            # Send initial progress immediately
            initial_progress = {'type': 'progress', 'step': 0, 'total': 8, 'task': 'Initializing analysis...', 'progress': 0}
            yield f"data: {json.dumps(initial_progress)}\n\n"
            logger.info(f"Sent initial progress: {initial_progress}")  # Debug log
            
            # Stream progress updates
            analysis_complete = False
            analysis_result = None
            analysis_error = None
            
            # Small delay to ensure initial progress is sent and flushed
            await asyncio.sleep(0.2)
            
            # Parse weights if provided
            analysis_weights_dict = None
            if weights:
                try:
                    analysis_weights_dict = json.loads(weights)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid weights JSON, ignoring: {weights}")
            
            # Start analysis in background AFTER ensuring initial progress is sent
            logger.info(f"Starting analysis task for {ticker}")
            analysis_task = asyncio.create_task(
                _analyze_stock_with_progress(ticker, progress_tracker, business_type, analysis_weights_dict)
            )
            
            # Monitor analysis task
            async def monitor_analysis():
                nonlocal analysis_complete, analysis_result, analysis_error
                try:
                    analysis_result = await analysis_task
                    analysis_complete = True
                    # Ensure we have a result
                    if analysis_result is None:
                        analysis_error = "Analysis completed but returned None"
                        analysis_result = None
                except HTTPException as e:
                    # HTTPException needs special handling
                    analysis_error = f"HTTP {e.status_code}: {e.detail}"
                    analysis_complete = True
                except Exception as e:
                    import traceback
                    error_traceback = traceback.format_exc()
                    logger.error(f"Analysis error for {ticker}: {e}\n{error_traceback}")
                    analysis_error = f"Analysis failed: {str(e)}"
                    analysis_complete = True
            
            monitor_task = asyncio.create_task(monitor_analysis())
            
            # Stream progress and wait for completion
            last_progress_time = asyncio.get_event_loop().time()
            while not analysis_complete:
                try:
                    # Wait for progress update with timeout
                    update = await asyncio.wait_for(progress_queue.get(), timeout=2.0)
                    progress_json = json.dumps(update)
                    yield f"data: {progress_json}\n\n"
                    last_progress_time = asyncio.get_event_loop().time()
                    logger.debug(f"Sent progress update: Step {update.get('step')}, Task: {update.get('task', 'unknown')}")
                except asyncio.TimeoutError:
                    # Check if analysis is complete
                    if analysis_complete:
                        break
                    # Check if we've been waiting too long without progress (analysis might be stuck)
                    current_time = asyncio.get_event_loop().time()
                    elapsed = current_time - last_progress_time
                    if elapsed > 30:
                        logger.warning(f"No progress updates for {elapsed:.1f} seconds, analysis might be stuck")
                        # Send a warning heartbeat with elapsed time
                        yield f"data: {json.dumps({'type': 'heartbeat', 'warning': f'No progress updates received for {int(elapsed)} seconds - analysis may be taking longer than expected'})}\n\n"
                    else:
                        # Send a normal heartbeat to keep connection alive (every 2 seconds)
                        yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    continue
            
            # Wait for analysis to complete
            await monitor_task
            
            # Debug logging
            logger.info(f"Analysis complete for {ticker}. Error: {analysis_error}, Result: {analysis_result is not None}")
            
            # Save analysis to database if successful
            if analysis_result and not analysis_error:
                try:
                    from app.database.db_service import DatabaseService
                    from datetime import date
                    db_service = DatabaseService(db_path="stock_analysis.db")
                    analysis_dict = analysis_result.model_dump(mode='json')
                    save_success = db_service.save_analysis(
                        ticker=ticker,
                        analysis_data=analysis_dict,
                        exchange=None,  # Could extract from ticker if needed
                        analysis_date=date.today().isoformat()
                    )
                    if save_success:
                        logger.info(f"Successfully saved analysis to database for {ticker}")
                    else:
                        logger.warning(f"Failed to save analysis to database for {ticker}")
                except Exception as e:
                    logger.error(f"Error saving analysis to database for {ticker}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # Don't fail the request if database save fails
            
            # Send final result
            if analysis_error:
                error_data = {'type': 'error', 'message': analysis_error}
                yield f"data: {json.dumps(error_data)}\n\n"
            elif analysis_result:
                # Replace NaN and Inf values before JSON serialization
                def replace_nan(obj):
                    if isinstance(obj, dict):
                        return {k: replace_nan(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [replace_nan(item) for item in obj]
                    elif isinstance(obj, float) and (math.isnan(obj) or not math.isfinite(obj)):
                        return None
                    return obj
                
                result_data = analysis_result.model_dump(mode='json')
                result_data = replace_nan(result_data)
                complete_data = {'type': 'complete', 'data': result_data}
                yield f"data: {json.dumps(complete_data)}\n\n"
            else:
                error_data = {'type': 'error', 'message': 'Analysis completed but no result returned'}
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    else:
        # Non-streaming response
        # Parse weights if provided
        analysis_weights_dict = None
        if weights:
            try:
                analysis_weights_dict = json.loads(weights)
            except json.JSONDecodeError:
                logger.warning(f"Invalid weights JSON, ignoring: {weights}")
        
        progress_tracker = ProgressTracker(total_steps=10)
        analysis = await _analyze_stock_with_progress(ticker, progress_tracker, business_type, analysis_weights_dict)
        
        # Save analysis to database
        if analysis:
            try:
                from app.database.db_service import DatabaseService
                from datetime import date
                db_service = DatabaseService(db_path="stock_analysis.db")
                analysis_dict = analysis.model_dump(mode='json')
                save_success = db_service.save_analysis(
                    ticker=ticker,
                    analysis_data=analysis_dict,
                    exchange=None,
                    analysis_date=date.today().isoformat()
                )
                if save_success:
                    logger.info(f"Successfully saved analysis to database for {ticker}")
                else:
                    logger.warning(f"Failed to save analysis to database for {ticker}")
            except Exception as e:
                logger.error(f"Error saving analysis to database for {ticker}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Don't fail the request if database save fails
        
        return analysis


@router.post("/manual-data", response_model=ManualDataResponse)
async def add_manual_data(entry: ManualDataEntry):
    """
    Add manual financial data for a ticker
    This data will be saved to the database and used in subsequent analyses
    """
    try:
        from app.database.db_service import DatabaseService
        
        ticker_upper = entry.ticker.upper()
        
        # Normalize period for key_metrics (should be 'latest')
        period = entry.period
        if entry.data_type == 'key_metrics':
            period = 'latest'
        
        # Store in memory (for backward compatibility)
        if ticker_upper not in manual_data_store:
            manual_data_store[ticker_upper] = {}
        
        entry_key = f"{entry.data_type}_{period}"
        manual_data_store[ticker_upper][entry_key] = {
            'ticker': ticker_upper,
            'data_type': entry.data_type,
            'period': period,
            'data': entry.data
        }
        
        # Save to database (like PDF upload does)
        db_service = DatabaseService(db_path="stock_analysis.db")
        logger.info(f"Saving manual data for {ticker_upper}: data_type={entry.data_type}, period={period}, data_keys={list(entry.data.keys())}, data_values={entry.data}")
        save_success = db_service.save_ai_extracted_data(
            ticker=ticker_upper,
            data_type=entry.data_type,
            period=period,
            data=entry.data,
            source='manual_entry'
        )
        
        if save_success:
            # Verify the save by reading it back immediately
            saved_data = db_service.get_ai_extracted_data(ticker_upper, entry.data_type)
            logger.info(f"Verification: Read back data for {ticker_upper} {entry.data_type}: {saved_data}")
            if entry.data_type == 'key_metrics':
                # For key_metrics, check 'latest' period
                key_metrics_data = saved_data.get('key_metrics', {})
                latest_data = key_metrics_data.get('latest', {})
                logger.info(f"Verification: Saved key_metrics for {ticker_upper} - keys in DB: {list(latest_data.keys())}, values: {latest_data}")
                # Also verify shares_outstanding and market_cap specifically
                if 'shares_outstanding' in latest_data:
                    logger.info(f"✓ shares_outstanding saved: {latest_data['shares_outstanding']}")
                else:
                    logger.warning(f"✗ shares_outstanding NOT found in saved data!")
                if 'market_cap' in latest_data:
                    logger.info(f"✓ market_cap saved: {latest_data['market_cap']}")
                else:
                    logger.warning(f"✗ market_cap NOT found in saved data!")
            else:
                period_data = saved_data.get(entry.data_type, {}).get(period, {})
                logger.info(f"Verification: Saved data for {ticker_upper} {entry.data_type} period {period} - keys in DB: {list(period_data.keys()) if period_data else 'None'}")
        else:
            logger.error(f"✗ FAILED to save manual data to database for {ticker_upper}!")
            logger.error(f"  Data that failed to save: data_type={entry.data_type}, period={period}, data={entry.data}")
        
        # Count updated periods
        updated_periods = len(manual_data_store[ticker_upper])
        
        # Build success message
        if save_success:
            message = f"Manual data added and saved successfully. {updated_periods} period(s) stored for {ticker_upper}."
        else:
            message = f"Manual data added (memory only). {updated_periods} period(s) stored for {ticker_upper}. Database save failed."
        
        return ManualDataResponse(
            success=True,
            message=message,
            updated_periods=updated_periods
        )
    except Exception as e:
        logger.error(f"Error adding manual data: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract-pdf-images")
async def extract_pdf_images(
    file: UploadFile = File(..., description="PDF file to extract images from")
):
    """
    Extract images from PDF pages for testing/debugging
    Returns base64-encoded images of all PDF pages
    """
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read PDF content
        pdf_bytes = await file.read()
        if len(pdf_bytes) == 0:
            raise HTTPException(status_code=400, detail="PDF file is empty")
        
        if len(pdf_bytes) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="PDF file too large (max 50MB)")
        
        # Check if pdf2image is available
        try:
            from pdf2image import convert_from_bytes
            from PIL import Image
        except ImportError:
            raise HTTPException(
                status_code=400,
                detail="PDF to image conversion requires pdf2image and Pillow. Install with: pip install pdf2image Pillow. Also install Poppler from https://github.com/oschwartz10612/poppler-windows/releases/"
            )
        
        # Convert PDF pages to images
        try:
            images = convert_from_bytes(pdf_bytes, dpi=150)  # Lower DPI for faster processing and smaller images
        except Exception as convert_error:
            error_msg = str(convert_error).lower()
            if "poppler" in error_msg or "pdftoppm" in error_msg or "cannot find" in error_msg:
                raise HTTPException(
                    status_code=400,
                    detail=f"PDF to image conversion failed: Poppler is not installed or not in PATH. Install Poppler: Windows - Download from https://github.com/oschwartz10612/poppler-windows/releases/ or use: winget install poppler. Error: {convert_error}"
                )
            else:
                raise HTTPException(status_code=400, detail=f"PDF to image conversion failed: {convert_error}")
        
        if not images:
            raise HTTPException(status_code=400, detail="No images could be extracted from PDF. The PDF may be corrupted or empty.")
        
        # Convert images to base64
        image_data = []
        for i, image in enumerate(images):
            try:
                # Convert PIL Image to base64
                buffer = io.BytesIO()
                image.save(buffer, format='PNG')
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                image_data.append({
                    'page_number': i + 1,
                    'image_base64': f'data:image/png;base64,{img_base64}',
                    'width': image.size[0],
                    'height': image.size[1]
                })
            except Exception as e:
                logger.error(f"Failed to convert page {i+1} to base64: {e}")
                continue
        
        return JSONResponse(content={
            'success': True,
            'total_pages': len(images),
            'images': image_data,
            'message': f'Successfully extracted {len(image_data)} page(s) from PDF'
        })
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error extracting images from PDF: {str(e)}")


async def _process_pdf_background(job_id: int, pdf_bytes: bytes, ticker: str, filename: str):
    """
    Background task to process PDF and update job status
    """
    import os
    from app.database.db_service import DatabaseService
    db_service = DatabaseService(db_path="stock_analysis.db")
    
    ticker_upper = ticker.upper()
    
    try:
        # Update job: starting processing
        db_service.update_pdf_job(job_id, current_task="Initializing PDF processing...")
        
        # Extract text and data from PDF (with OCR fallback for image-based PDFs)
        extractor = PDFExtractor()
        
        # Get page count
        total_pages = extractor.get_pdf_page_count(pdf_bytes)
        db_service.update_pdf_job(job_id, total_pages=total_pages, current_task=f"PDF loaded: {total_pages} pages")
        
        try:
            pdf_text = extractor.extract_text_from_pdf(pdf_bytes, use_ocr=True)
        except Exception as e:
            error_msg = str(e)
            if "OCR" in error_msg and "not installed" in error_msg:
                db_service.fail_pdf_job(job_id, f"{error_msg}. For scanned PDFs, install OCR dependencies.")
                return
            db_service.fail_pdf_job(job_id, f"Failed to extract text from PDF: {error_msg}")
            return
        
        if not pdf_text or len(pdf_text.strip()) < 100:
            db_service.fail_pdf_job(job_id, "Could not extract text from PDF. File may be corrupted or image-based.")
            return
        
        # Create progress callback to update job status
        def progress_callback(current_page: int, total: int):
            """Update job progress"""
            try:
                if current_page == 0:
                    # Special case: page is starting (not completed yet)
                    db_service.update_pdf_job(
                        job_id,
                        current_task=f"Starting page processing (0 of {total} completed)..."
                    )
                else:
                    db_service.update_pdf_job(
                        job_id,
                        pages_processed=current_page,
                        current_page=current_page,
                        current_task=f"Processing page {current_page} of {total}..."
                    )
            except Exception as e:
                logger.warning(f"Failed to update job progress: {e}")
        
        # Use LLM to extract financial data
        extraction_error = None
        extraction_error_type = None
        updated_periods = 0
        extraction_details = {
            "pdf_text_length": len(pdf_text),
            "extraction_provider": "textract" if extractor.use_textract else "local",
            "extraction_method": None,
            "error_type": None,
            "error_message": None,
            "textract_enabled": extractor.use_textract if hasattr(extractor, 'use_textract') else False
        }
        
        raw_llm_response = None
        try:
            logger.info(f"Starting extraction for {ticker_upper} (job {job_id})")
            db_service.update_pdf_job(job_id, current_task="Starting extraction...")
            
            # Use per-page processing with progress callback
            extracted_data, raw_llm_response = await extractor.extract_financial_data_per_page(
                pdf_bytes, ticker_upper, progress_callback=progress_callback
            )
            
            logger.info(f"Extraction completed for {ticker_upper} (job {job_id})")
            extraction_details["extraction_method"] = "textract" if extractor.use_textract else "local_extraction"
            
            # EC2 auto-stop no longer needed (using Textract instead)
            
            if raw_llm_response:
                extraction_details["raw_llm_response_preview"] = raw_llm_response[:2000] if len(raw_llm_response) > 2000 else raw_llm_response
                extraction_details["raw_llm_response_length"] = len(raw_llm_response)
        except ValueError as e:
            extraction_error = str(e)
            extraction_error_type = "validation_error"
            extraction_details["error_type"] = "validation_error"
            extraction_details["error_message"] = str(e)
            logger.error(f"PDF validation error for {ticker_upper}: {e}")
            extracted_data = {
                "income_statement": {},
                "balance_sheet": {},
                "cashflow": {},
                "key_metrics": {}
            }
        except json.JSONDecodeError as e:
            extraction_error = f"Failed to parse LLM response as JSON: {str(e)}"
            extraction_error_type = "json_parse_error"
            extraction_details["error_type"] = "json_parse_error"
            extraction_details["error_message"] = str(e)
            logger.error(f"JSON parsing error for {ticker_upper}: {e}")
            extracted_data = {
                "income_statement": {},
                "balance_sheet": {},
                "cashflow": {},
                "key_metrics": {}
            }
        except Exception as e:
            extraction_error = str(e)
            extraction_error_type = "extraction_error"
            extraction_details["error_type"] = "extraction_error"
            extraction_details["error_message"] = str(e)
            logger.error(f"Extraction failed for {ticker_upper}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            extracted_data = {
                "income_statement": {},
                "balance_sheet": {},
                "cashflow": {},
                "key_metrics": {}
            }
        
        # Analyze extracted data
        income_statement = extracted_data.get('income_statement', {})
        balance_sheet = extracted_data.get('balance_sheet', {})
        cashflow = extracted_data.get('cashflow', {})
        key_metrics = extracted_data.get('key_metrics', {})
        
        # Analyze PDF text for financial keywords to diagnose issues
        pdf_text_lower = pdf_text.lower()
        financial_keywords = {
            "income_statement": ["revenue", "net income", "operating income", "ebit", "income before tax", "earnings", "profit", "sales"],
            "balance_sheet": ["total assets", "total liabilities", "stockholder equity", "shareholder equity", "cash and cash equivalents", "total debt"],
            "cash_flow": ["operating cash flow", "cash from operations", "capital expenditures", "capex", "free cash flow", "financing activities"],
            "dates": ["2024", "2023", "2022", "fiscal year", "year ended", "quarter ended", "period ended"]
        }
        
        # Check for financial keywords in PDF
        found_keywords = {}
        for category, keywords in financial_keywords.items():
            matches = [kw for kw in keywords if kw in pdf_text_lower]
            if matches:
                found_keywords[category] = len(matches)
        
        extraction_details["financial_keywords_detected"] = found_keywords
        extraction_details["pdf_contains_financial_data"] = len(found_keywords) > 0
        
        # Analyze what the LLM actually returned
        llm_response_analysis = []
        if raw_llm_response:
            extraction_details["raw_llm_response_length"] = len(raw_llm_response)
            # Check if LLM returned empty objects
            if raw_llm_response.strip().startswith('{'):
                try:
                    parsed = json.loads(raw_llm_response)
                    for key, value in parsed.items():
                        if isinstance(value, dict):
                            if len(value) == 0:
                                llm_response_analysis.append(f"LLM returned empty {key} object")
                            else:
                                llm_response_analysis.append(f"LLM returned {key} with {len(value)} items (but no valid periods extracted)")
                        elif isinstance(value, list):
                            llm_response_analysis.append(f"LLM returned {key} as array with {len(value)} items")
                        else:
                            llm_response_analysis.append(f"LLM returned {key} as {type(value).__name__}")
                except:
                    llm_response_analysis.append(f"LLM response is not valid JSON structure")
            
            # Show preview of what LLM said
            preview = raw_llm_response[:1000] if len(raw_llm_response) > 1000 else raw_llm_response
            extraction_details["raw_llm_response_preview"] = preview
        
        extraction_details["llm_response_analysis"] = llm_response_analysis
        
        total_periods = (
            (len(income_statement) if isinstance(income_statement, dict) else 0) +
            (len(balance_sheet) if isinstance(balance_sheet, dict) else 0) +
            (len(cashflow) if isinstance(cashflow, dict) else 0) +
            (1 if key_metrics and isinstance(key_metrics, dict) and len(key_metrics) > 0 else 0)
        )
        
        extraction_details["income_statement_periods"] = len(income_statement) if isinstance(income_statement, dict) else 0
        extraction_details["balance_sheet_periods"] = len(balance_sheet) if isinstance(balance_sheet, dict) else 0
        extraction_details["cashflow_periods"] = len(cashflow) if isinstance(cashflow, dict) else 0
        extraction_details["has_key_metrics"] = bool(key_metrics and isinstance(key_metrics, dict) and len(key_metrics) > 0)
        extraction_details["total_periods_found"] = total_periods
        
        # Store extracted data in database
        db_service.update_pdf_job(job_id, current_task="Saving extracted data to database...")
        
        updated_periods = 0
        db_save_results = {
            'saved': 0,
            'failed': 0,
            'verified': 0,
            'details': []
        }
        
        # Process income statement data
        if income_statement and isinstance(income_statement, dict):
            for period, data in income_statement.items():
                save_success = db_service.save_ai_extracted_data(
                    ticker=ticker_upper,
                    data_type='income_statement',
                    period=period,
                    data=data,
                    source='pdf_upload',
                    extraction_method='llama_vision'
                )
                if save_success:
                    db_save_results['saved'] += 1
                    saved_data = db_service.get_ai_extracted_data(ticker_upper, 'income_statement')
                    if saved_data and period in saved_data:
                        db_save_results['verified'] += 1
                else:
                    db_save_results['failed'] += 1
                updated_periods += 1
        
        # Process balance sheet data
        if balance_sheet and isinstance(balance_sheet, dict):
            for period, data in balance_sheet.items():
                save_success = db_service.save_ai_extracted_data(
                    ticker=ticker_upper,
                    data_type='balance_sheet',
                    period=period,
                    data=data,
                    source='pdf_upload',
                    extraction_method='llama_vision'
                )
                if save_success:
                    db_save_results['saved'] += 1
                    saved_data = db_service.get_ai_extracted_data(ticker_upper, 'balance_sheet')
                    if saved_data and period in saved_data:
                        db_save_results['verified'] += 1
                else:
                    db_save_results['failed'] += 1
                updated_periods += 1
        
        # Process cash flow data
        if cashflow and isinstance(cashflow, dict):
            for period, data in cashflow.items():
                save_success = db_service.save_ai_extracted_data(
                    ticker=ticker_upper,
                    data_type='cashflow',
                    period=period,
                    data=data,
                    source='pdf_upload',
                    extraction_method='llama_vision'
                )
                if save_success:
                    db_save_results['saved'] += 1
                    saved_data = db_service.get_ai_extracted_data(ticker_upper, 'cashflow')
                    if saved_data and period in saved_data:
                        db_save_results['verified'] += 1
                else:
                    db_save_results['failed'] += 1
                updated_periods += 1
        
        # Process key metrics
        if 'key_metrics' in extracted_data and extracted_data['key_metrics']:
            save_success = db_service.save_ai_extracted_data(
                ticker=ticker_upper,
                data_type='key_metrics',
                period='latest',
                data=extracted_data['key_metrics'],
                source='pdf_upload',
                extraction_method='llama_vision'
            )
            if save_success:
                db_save_results['saved'] += 1
                saved_data = db_service.get_ai_extracted_data(ticker_upper, 'key_metrics')
                if saved_data and 'latest' in saved_data:
                    db_save_results['verified'] += 1
            else:
                db_save_results['failed'] += 1
            updated_periods += 1
        
        extraction_details['database_save'] = db_save_results
        
        # Build helpful diagnostics and recommendations (similar to sync endpoint)
        if updated_periods == 0:
            diagnostic_parts = []
            llm_response_analysis = extraction_details.get("llm_response_analysis", [])
            
            # Check if PDF contains financial keywords
            if extraction_details.get("pdf_contains_financial_data"):
                keywords_info = extraction_details.get("financial_keywords_detected", {})
                keyword_summary = ", ".join([f"{k}: {v} matches" for k, v in keywords_info.items()])
                diagnostic_parts.append(f"PDF text analysis: Financial keywords detected ({keyword_summary}), but LLM did not extract structured data.")
            else:
                diagnostic_parts.append("PDF text analysis: No financial keywords detected. The PDF may not contain standard financial statements.")
            
            # Check what LLM returned
            if llm_response_analysis:
                diagnostic_parts.append(f"LLM response analysis: {'; '.join(llm_response_analysis)}")
            
            # Check structure
            if income_statement == {} and balance_sheet == {} and cashflow == {} and not key_metrics:
                diagnostic_parts.append("LLM returned empty objects for all financial statement types.")
            else:
                diagnostic_parts.append(f"LLM returned partial structure: Income Statement ({extraction_details.get('income_statement_periods', 0)} periods), Balance Sheet ({extraction_details.get('balance_sheet_periods', 0)} periods), Cash Flow ({extraction_details.get('cashflow_periods', 0)} periods), Key Metrics ({'Yes' if extraction_details.get('has_key_metrics') else 'No'})")
            
            # Add actionable recommendations
            if extraction_details.get("pdf_contains_financial_data") and updated_periods == 0:
                # Textract-based extraction troubleshooting
                textract_enabled = extraction_details.get("textract_enabled", False)
                
                if textract_enabled:
                    diagnostic_parts.append("RECOMMENDATION: PDF contains financial data but Textract extraction failed.")
                    diagnostic_parts.append("Troubleshooting steps:")
                    diagnostic_parts.append("  1. Check AWS Textract permissions in IAM")
                    diagnostic_parts.append("  2. Verify AWS credentials are configured (AWS_PROFILE or default)")
                    diagnostic_parts.append("  3. Ensure PDF has complete financial statements with clear labels")
                    diagnostic_parts.append("  4. Verify the document format matches standard 10-K/annual report structure")
                    diagnostic_parts.append("  5. Check that financial tables are properly formatted (dates in headers, values in cells)")
                else:
                    diagnostic_parts.append("RECOMMENDATION: PDF contains financial data but local extraction failed.")
                    diagnostic_parts.append("Troubleshooting steps:")
                    diagnostic_parts.append("  1. Enable Textract by setting USE_TEXTRACT=true in .env")
                    diagnostic_parts.append("  2. Configure AWS credentials for Textract access")
                    diagnostic_parts.append("  3. Ensure PDF has complete financial statements with clear labels")
            elif not extraction_details.get("pdf_contains_financial_data"):
                diagnostic_parts.append("RECOMMENDATION: Upload a document with complete financial statements (10-K filing, annual report, or quarterly report with Income Statement, Balance Sheet, and Cash Flow sections).")
            
            # Check PDF text quality
            if extraction_details["pdf_text_length"] < 500:
                diagnostic_parts.append(f"PDF text is very short ({extraction_details['pdf_text_length']} characters). The PDF may be image-based or corrupted.")
            elif extraction_details["pdf_text_length"] < 1000:
                diagnostic_parts.append(f"PDF text is short ({extraction_details['pdf_text_length']} characters). The document may not contain complete financial statements.")
            
            extraction_details['diagnostics'] = diagnostic_parts
            extraction_details['llm_response_analysis'] = llm_response_analysis
        
        # Build result message
        result = {
            "success": True,
            "updated_periods": updated_periods,
            "extracted_data": extracted_data,
            "extraction_details": extraction_details
        }
        
        # Complete job
        db_service.complete_pdf_job(
            job_id,
            result=result,
            extraction_details=extraction_details
        )
        logger.info(f"PDF processing completed for {ticker_upper} (job {job_id}): {updated_periods} periods extracted")
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error processing PDF for {ticker_upper} (job {job_id}): {e}")
        logger.error(f"Traceback: {error_traceback}")
        db_service.fail_pdf_job(job_id, f"Error processing PDF: {str(e)}")


@router.post("/upload-pdf", response_model=ManualDataResponse)
async def upload_pdf(
    ticker: str = Query(..., description="Stock ticker symbol"),
    file: UploadFile = File(..., description="PDF file to upload")
):
    """
    Upload a PDF financial statement and extract data using LLM (synchronous)
    This endpoint processes the PDF immediately and returns results
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read PDF content
        try:
            pdf_bytes = await file.read()
        except Exception as read_error:
            logger.error(f"Error reading PDF file: {read_error}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=400, detail=f"Failed to read PDF file: {str(read_error)}")
        
        if len(pdf_bytes) == 0:
            raise HTTPException(status_code=400, detail="PDF file is empty")
        
        if len(pdf_bytes) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="PDF file too large (max 50MB)")
        
        ticker_upper = ticker.upper()
        
        # Extract text and data from PDF (with OCR fallback for image-based PDFs)
        extractor = PDFExtractor()
        try:
            pdf_text = extractor.extract_text_from_pdf(pdf_bytes, use_ocr=True)
        except Exception as e:
            error_msg = str(e)
            if "OCR" in error_msg and "not installed" in error_msg:
                raise HTTPException(
                    status_code=400, 
                    detail=f"{error_msg}. For scanned PDFs, install OCR dependencies: pip install pytesseract pdf2image Pillow, and install Tesseract OCR from https://github.com/tesseract-ocr/tesseract"
                )
            raise HTTPException(status_code=400, detail=f"Failed to extract text from PDF: {error_msg}")
        
        if not pdf_text or len(pdf_text.strip()) < 100:
            raise HTTPException(
                status_code=400, 
                detail="Could not extract text from PDF. File may be corrupted or image-based. OCR was attempted but may need Tesseract OCR installed. See server logs for details."
            )
        
        # Llama-only mode: Check if Ollama is available
        import os
        logger.info(f"Using Textract for PDF extraction")
        
        # Use LLM to extract financial data
        extraction_error = None
        extraction_error_type = None
        updated_periods = 0  # Initialize early to avoid reference errors
        extraction_details = {
            "pdf_text_length": len(pdf_text),
            "llm_provider": "textract" if extractor.use_textract else "local",
            "extraction_method": None,
            "error_type": None,
            "error_message": None,
            "textract_enabled": extractor.use_textract if hasattr(extractor, 'use_textract') else False
        }
        
        raw_llm_response = None
        try:
            logger.info(f"Starting extraction for {ticker_upper} (sync mode)")
            # Extract financial data (Textract processes entire PDF at once)
            extracted_data, raw_llm_response = await extractor.extract_financial_data_per_page(pdf_bytes, ticker_upper)
            
            logger.info(f"Extraction completed for {ticker_upper}")
            extraction_details["extraction_method"] = "textract" if extractor.use_textract else "local_extraction"
            
            if raw_llm_response:
                extraction_details["raw_llm_response_preview"] = raw_llm_response[:2000] if len(raw_llm_response) > 2000 else raw_llm_response
                extraction_details["raw_llm_response_length"] = len(raw_llm_response)
        except ValueError as e:
            # PDF text validation errors
            extraction_error = str(e)
            extraction_error_type = "validation_error"
            extraction_details["error_type"] = "validation_error"
            extraction_details["error_message"] = str(e)
            logger.error(f"PDF validation error for {ticker_upper}: {e}")
            extracted_data = {
                "income_statement": {},
                "balance_sheet": {},
                "cashflow": {},
                "key_metrics": {}
            }
        except json.JSONDecodeError as e:
            # JSON parsing errors
            extraction_error = f"Failed to parse LLM response as JSON: {str(e)}"
            extraction_error_type = "json_parse_error"
            extraction_details["error_type"] = "json_parse_error"
            extraction_details["error_message"] = str(e)
            logger.error(f"JSON parsing error for {ticker_upper}: {e}")
            extracted_data = {
                "income_statement": {},
                "balance_sheet": {},
                "cashflow": {},
                "key_metrics": {}
            }
        except Exception as e:
            # Other LLM API errors
            extraction_error = str(e)
            extraction_error_type = "llm_api_error"
            extraction_details["error_type"] = "llm_api_error"
            extraction_details["error_message"] = str(e)
            logger.error(f"LLM extraction failed for {ticker_upper}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Return empty structure but still indicate success
            extracted_data = {
                "income_statement": {},
                "balance_sheet": {},
                "cashflow": {},
                "key_metrics": {}
            }
        
        # Analyze PDF text for financial keywords to diagnose issues
        pdf_text_lower = pdf_text.lower()
        financial_keywords = {
            "income_statement": ["revenue", "net income", "operating income", "ebit", "income before tax", "earnings", "profit", "sales"],
            "balance_sheet": ["total assets", "total liabilities", "stockholder equity", "shareholder equity", "cash and cash equivalents", "total debt"],
            "cash_flow": ["operating cash flow", "cash from operations", "capital expenditures", "capex", "free cash flow", "financing activities"],
            "dates": ["2024", "2023", "2022", "fiscal year", "year ended", "quarter ended", "period ended"]
        }
        
        # Analyze extracted data to determine why it might be empty
        income_statement = extracted_data.get('income_statement', {})
        balance_sheet = extracted_data.get('balance_sheet', {})
        cashflow = extracted_data.get('cashflow', {})
        key_metrics = extracted_data.get('key_metrics', {})
        
        total_periods = (
            (len(income_statement) if isinstance(income_statement, dict) else 0) +
            (len(balance_sheet) if isinstance(balance_sheet, dict) else 0) +
            (len(cashflow) if isinstance(cashflow, dict) else 0) +
            (1 if key_metrics and isinstance(key_metrics, dict) and len(key_metrics) > 0 else 0)
        )
        
        extraction_details["income_statement_periods"] = len(income_statement) if isinstance(income_statement, dict) else 0
        extraction_details["balance_sheet_periods"] = len(balance_sheet) if isinstance(balance_sheet, dict) else 0
        extraction_details["cashflow_periods"] = len(cashflow) if isinstance(cashflow, dict) else 0
        extraction_details["has_key_metrics"] = bool(key_metrics and isinstance(key_metrics, dict) and len(key_metrics) > 0)
        extraction_details["total_periods_found"] = total_periods
        
        # Analyze what the LLM actually returned
        llm_response_analysis = extraction_details.get("llm_response_analysis", [])
        if not llm_response_analysis:
            llm_response_analysis = []
        
        if raw_llm_response:
            extraction_details["raw_llm_response_length"] = len(raw_llm_response)
            # Check if LLM returned empty objects
            if raw_llm_response.strip().startswith('{'):
                try:
                    parsed = json.loads(raw_llm_response)
                    for key, value in parsed.items():
                        if isinstance(value, dict):
                            if len(value) == 0:
                                llm_response_analysis.append(f"LLM returned empty {key} object")
                            else:
                                llm_response_analysis.append(f"LLM returned {key} with {len(value)} items (but no valid periods extracted)")
                        elif isinstance(value, list):
                            llm_response_analysis.append(f"LLM returned {key} as array with {len(value)} items")
                        else:
                            llm_response_analysis.append(f"LLM returned {key} as {type(value).__name__}")
                except:
                    llm_response_analysis.append(f"LLM response is not valid JSON structure")
            
            # Show preview of what LLM said
            preview = raw_llm_response[:1000] if len(raw_llm_response) > 1000 else raw_llm_response
            extraction_details["raw_llm_response_preview"] = preview
            extraction_details["llm_response_analysis"] = llm_response_analysis
        
        # Check for financial keywords in PDF
        found_keywords = {}
        for category, keywords in financial_keywords.items():
            matches = [kw for kw in keywords if kw in pdf_text_lower]
            if matches:
                found_keywords[category] = len(matches)
        
        extraction_details["financial_keywords_detected"] = found_keywords
        extraction_details["pdf_contains_financial_data"] = len(found_keywords) > 0
        
        # Log extracted data for debugging
        logger.info(f"Extracted data for {ticker_upper}: {json.dumps(extracted_data, indent=2, default=str)}")
        logger.info(f"Extracted data keys: {list(extracted_data.keys())}")
        logger.info(f"Income statement periods: {len(income_statement) if isinstance(income_statement, dict) else 0}")
        logger.info(f"Balance sheet periods: {len(balance_sheet) if isinstance(balance_sheet, dict) else 0}")
        logger.info(f"Cashflow periods: {len(cashflow) if isinstance(cashflow, dict) else 0}")
        
        # Note: raw_llm_response is already set from the extraction call above
        # If it wasn't set, try to get it from extraction_details
        if not raw_llm_response and extraction_details.get("raw_llm_response_preview"):
            # Try to reconstruct from preview if available
            raw_llm_response = extraction_details.get("raw_llm_response_preview", "")
        
        if total_periods == 0 and not extraction_error and not raw_llm_response:
            # Fallback: serialize extracted_data if we don't have raw response
            raw_llm_response = json.dumps(extracted_data, indent=2, default=str)
            logger.warning(f"LLM returned data structure but no periods extracted. Using serialized extracted_data as fallback.")
            if len(raw_llm_response) > 0:
                extraction_details["raw_llm_response_preview"] = raw_llm_response[:1000]  # First 1000 chars for debugging
        
        # Store extracted data in both in-memory store (for backward compatibility) and database
        if ticker_upper not in manual_data_store:
            manual_data_store[ticker_upper] = {}
        
        # Also save to database for persistence
        from app.database.db_service import DatabaseService
        db_service = DatabaseService(db_path="stock_analysis.db")
        
        updated_periods = 0
        db_save_results = {
            'saved': 0,
            'failed': 0,
            'verified': 0,
            'details': []
        }
        
        # Process income statement data
        if income_statement and isinstance(income_statement, dict):
            for period, data in income_statement.items():
                entry_key = f"income_statement_{period}"
                # Store in-memory (backward compatibility)
                manual_data_store[ticker_upper][entry_key] = {
                    'ticker': ticker_upper,
                    'data_type': 'income_statement',
                    'period': period,
                    'data': data
                }
                # Save to database
                save_success = db_service.save_ai_extracted_data(
                    ticker=ticker_upper,
                    data_type='income_statement',
                    period=period,
                    data=data,
                    source='pdf_upload',
                    extraction_method='llama_vision'
                )
                if save_success:
                    db_save_results['saved'] += 1
                    # Verify the save by reading it back
                    saved_data = db_service.get_ai_extracted_data(ticker_upper, 'income_statement')
                    if saved_data and period in saved_data:
                        db_save_results['verified'] += 1
                        db_save_results['details'].append(f"Income Statement {period}: Saved and verified ✓")
                    else:
                        db_save_results['details'].append(f"Income Statement {period}: Saved but verification failed ⚠")
                else:
                    db_save_results['failed'] += 1
                    db_save_results['details'].append(f"Income Statement {period}: Save failed ✗")
                updated_periods += 1
        
        # Process balance sheet data
        if balance_sheet and isinstance(balance_sheet, dict):
            for period, data in balance_sheet.items():
                entry_key = f"balance_sheet_{period}"
                # Store in-memory (backward compatibility)
                manual_data_store[ticker_upper][entry_key] = {
                    'ticker': ticker_upper,
                    'data_type': 'balance_sheet',
                    'period': period,
                    'data': data
                }
                # Save to database
                save_success = db_service.save_ai_extracted_data(
                    ticker=ticker_upper,
                    data_type='balance_sheet',
                    period=period,
                    data=data,
                    source='pdf_upload',
                    extraction_method='llama_vision'
                )
                if save_success:
                    db_save_results['saved'] += 1
                    # Verify the save by reading it back
                    saved_data = db_service.get_ai_extracted_data(ticker_upper, 'balance_sheet')
                    if saved_data and period in saved_data:
                        db_save_results['verified'] += 1
                        db_save_results['details'].append(f"Balance Sheet {period}: Saved and verified ✓")
                    else:
                        db_save_results['details'].append(f"Balance Sheet {period}: Saved but verification failed ⚠")
                else:
                    db_save_results['failed'] += 1
                    db_save_results['details'].append(f"Balance Sheet {period}: Save failed ✗")
                updated_periods += 1
        
        # Process cash flow data
        if cashflow and isinstance(cashflow, dict):
            for period, data in cashflow.items():
                entry_key = f"cashflow_{period}"
                # Store in-memory (backward compatibility)
                manual_data_store[ticker_upper][entry_key] = {
                    'ticker': ticker_upper,
                    'data_type': 'cashflow',
                    'period': period,
                    'data': data
                }
                # Save to database
                save_success = db_service.save_ai_extracted_data(
                    ticker=ticker_upper,
                    data_type='cashflow',
                    period=period,
                    data=data,
                    source='pdf_upload',
                    extraction_method='llama_vision'
                )
                if save_success:
                    db_save_results['saved'] += 1
                    # Verify the save by reading it back
                    saved_data = db_service.get_ai_extracted_data(ticker_upper, 'cashflow')
                    if saved_data and period in saved_data:
                        db_save_results['verified'] += 1
                        db_save_results['details'].append(f"Cash Flow {period}: Saved and verified ✓")
                    else:
                        db_save_results['details'].append(f"Cash Flow {period}: Saved but verification failed ⚠")
                else:
                    db_save_results['failed'] += 1
                    db_save_results['details'].append(f"Cash Flow {period}: Save failed ✗")
                updated_periods += 1
        
        # Process key metrics
        if 'key_metrics' in extracted_data and extracted_data['key_metrics']:
            # Store key metrics with a special period
            entry_key = "key_metrics_latest"
            # Store in-memory (backward compatibility)
            manual_data_store[ticker_upper][entry_key] = {
                'ticker': ticker_upper,
                'data_type': 'key_metrics',
                'period': 'latest',
                'data': extracted_data['key_metrics']
            }
            # Save to database
            save_success = db_service.save_ai_extracted_data(
                ticker=ticker_upper,
                data_type='key_metrics',
                period='latest',
                data=extracted_data['key_metrics'],
                source='pdf_upload',
                extraction_method='llama_vision'
            )
            if save_success:
                db_save_results['saved'] += 1
                # Verify the save by reading it back
                saved_data = db_service.get_ai_extracted_data(ticker_upper, 'key_metrics')
                if saved_data and 'latest' in saved_data:
                    db_save_results['verified'] += 1
                    db_save_results['details'].append(f"Key Metrics: Saved and verified ✓")
                else:
                    db_save_results['details'].append(f"Key Metrics: Saved but verification failed ⚠")
            else:
                db_save_results['failed'] += 1
                db_save_results['details'].append(f"Key Metrics: Save failed ✗")
            updated_periods += 1
        
        # Add database save results to extraction details
        extraction_details['database_save'] = db_save_results
        logger.info(f"Database save results for {ticker_upper}: {db_save_results['saved']} saved, {db_save_results['verified']} verified, {db_save_results['failed']} failed")
        
        # Add database save feedback to message
        db_feedback = ""
        if db_save_results['saved'] > 0:
            if db_save_results['verified'] == db_save_results['saved']:
                db_feedback = f"\n\n✅ Database: All {db_save_results['saved']} data period(s) saved and verified successfully for {ticker_upper}."
            elif db_save_results['verified'] > 0:
                db_feedback = f"\n\n⚠️ Database: {db_save_results['saved']} period(s) saved, {db_save_results['verified']} verified, {db_save_results['failed']} failed for {ticker_upper}."
            else:
                db_feedback = f"\n\n⚠️ Database: {db_save_results['saved']} period(s) saved but verification incomplete for {ticker_upper}."
        elif db_save_results['failed'] > 0:
            db_feedback = f"\n\n❌ Database: Failed to save {db_save_results['failed']} data period(s) for {ticker_upper}."
        
        # Create appropriate message with specific feedback
        if updated_periods == 0:
            # Build detailed error message
            error_parts = []
            
            # Llama-only mode: Check if Ollama is running
            llama_url = os.getenv("LLAMA_API_URL", "http://localhost:11434")
            if extraction_error_type == "validation_error":
                error_parts.append(f"PDF text validation failed: {extraction_error}")
            elif extraction_error_type == "json_parse_error":
                error_parts.append(f"LLM returned invalid JSON format: {extraction_error}")
            elif extraction_error_type == "llm_api_error":
                if "api key" in extraction_error.lower() or "authentication" in extraction_error.lower():
                    error_parts.append(f"API authentication failed: {extraction_error}")
                elif "rate limit" in extraction_error.lower() or "quota" in extraction_error.lower():
                    error_parts.append(f"API rate limit exceeded: {extraction_error}")
                else:
                    error_parts.append(f"LLM API error: {extraction_error}")
            elif extraction_error:
                error_parts.append(f"Extraction error: {extraction_error}")
            
            # Analyze what went wrong with specific diagnostics
            if total_periods == 0:
                diagnostic_parts = []
                
                # Check if PDF contains financial keywords
                if extraction_details.get("pdf_contains_financial_data"):
                    keywords_info = extraction_details.get("financial_keywords_detected", {})
                    keyword_summary = ", ".join([f"{k}: {v} matches" for k, v in keywords_info.items()])
                    diagnostic_parts.append(f"PDF text analysis: Financial keywords detected ({keyword_summary}), but LLM did not extract structured data.")
                else:
                    diagnostic_parts.append("PDF text analysis: No financial keywords detected. The PDF may not contain standard financial statements.")
                
                # Check what LLM returned
                provider_name = extraction_details.get("llm_provider", "unknown").upper()
                if llm_response_analysis:
                    diagnostic_parts.append(f"LLM response analysis ({provider_name}): {'; '.join(llm_response_analysis)}")
                
                # Check raw LLM response
                if raw_llm_response:
                    preview = raw_llm_response[:500].replace('\n', ' ').replace('\r', ' ')
                    provider_name = extraction_details.get("llm_provider", "unknown").upper()
                    diagnostic_parts.append(f"LLM raw response preview ({provider_name}): {preview}...")
                
                # Check structure
                provider_name = extraction_details.get("llm_provider", "unknown").upper()
                if income_statement == {} and balance_sheet == {} and cashflow == {} and not key_metrics:
                    diagnostic_parts.append(f"LLM ({provider_name}) returned empty objects for all financial statement types.")
                else:
                    diagnostic_parts.append(f"LLM ({provider_name}) returned partial structure: Income Statement ({extraction_details['income_statement_periods']} periods), Balance Sheet ({extraction_details['balance_sheet_periods']} periods), Cash Flow ({extraction_details['cashflow_periods']} periods), Key Metrics ({'Yes' if extraction_details.get('has_key_metrics') else 'No'})")
                
                # Add actionable advice
                provider_name = extraction_details.get("llm_provider", "unknown").upper()
                if extraction_details.get("pdf_contains_financial_data") and total_periods == 0:
                    # Llama-only mode: All extractions use Llama
                    # Textract-based extraction troubleshooting
                    textract_enabled = extraction_details.get("textract_enabled", False)
                    
                    if textract_enabled:
                        diagnostic_parts.append("RECOMMENDATION: PDF contains financial data but Textract extraction failed.")
                        diagnostic_parts.append("Troubleshooting: (1) Check AWS Textract IAM permissions, (2) Verify AWS credentials, (3) Ensure PDF has complete financial statements, (4) Verify document format matches 10-K/annual report structure")
                    else:
                        diagnostic_parts.append("RECOMMENDATION: PDF contains financial data but local extraction failed.")
                        diagnostic_parts.append("Troubleshooting: (1) Enable Textract (USE_TEXTRACT=true), (2) Configure AWS credentials, (3) Ensure PDF has complete financial statements")
                elif not extraction_details.get("pdf_contains_financial_data"):
                    diagnostic_parts.append("RECOMMENDATION: Upload a document with complete financial statements (10-K filing, annual report, or quarterly report with Income Statement, Balance Sheet, and Cash Flow sections).")
                
                error_parts.extend(diagnostic_parts)
            
            # Check PDF text quality
            if extraction_details["pdf_text_length"] < 500:
                error_parts.append(f"PDF text is very short ({extraction_details['pdf_text_length']} characters). The PDF may be image-based or corrupted.")
            elif extraction_details["pdf_text_length"] < 1000:
                error_parts.append(f"PDF text is short ({extraction_details['pdf_text_length']} characters). The document may not contain complete financial statements.")
            
            if not error_parts:
                error_parts.append("No financial data could be extracted. The PDF may not contain standard financial statements or the format may not be recognized.")
            
            # Format diagnostics with better structure
            if len(error_parts) > 1:
                error_message = "\n".join([f"• {part}" for part in error_parts])
            else:
                error_message = error_parts[0] if error_parts else "Unknown error"
            message = f"PDF processed successfully! Extracted {updated_periods} data period(s) for {ticker_upper}.\n\nDiagnostics:\n{error_message}{db_feedback}"
        else:
            message = f"PDF processed successfully! Extracted {updated_periods} data period(s) for {ticker_upper}. The analysis will be updated automatically.{db_feedback}"
        
        return ManualDataResponse(
            success=True,
            message=message,
            updated_periods=updated_periods,
            extracted_data=extracted_data,  # Return extracted data for UI display
            extraction_details=extraction_details  # Return detailed extraction information
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors and return a user-friendly message
        logger.error(f"Unexpected error in upload_pdf for {ticker.upper() if 'ticker' in locals() else 'unknown'}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while processing the PDF: {str(e)}")


@router.get("/pdf-job-status/{job_id}", response_model=PDFJobStatusResponse)
async def get_pdf_job_status(job_id: int):
    """
    Get the status of a PDF processing job
    Poll this endpoint to check progress
    """
    from app.database.db_service import DatabaseService
    db_service = DatabaseService(db_path="stock_analysis.db")
    
    job = db_service.get_pdf_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"PDF job {job_id} not found")
    
    return PDFJobStatusResponse(**job)


@router.post("/upload-pdf-sync", response_model=ManualDataResponse)
async def upload_pdf_sync(
    ticker: str = Query(..., description="Stock ticker symbol"),
    file: UploadFile = File(..., description="PDF file to upload")
):
    """
    Upload a PDF financial statement and extract data using LLM (synchronous - for backward compatibility)
    This endpoint processes the PDF immediately and returns results
    For long documents, use /upload-pdf instead which returns a job ID
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read PDF content
        try:
            pdf_bytes = await file.read()
        except Exception as read_error:
            logger.error(f"Error reading PDF file: {read_error}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=400, detail=f"Failed to read PDF file: {str(read_error)}")
        
        if len(pdf_bytes) == 0:
            raise HTTPException(status_code=400, detail="PDF file is empty")
        
        if len(pdf_bytes) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="PDF file too large (max 50MB)")
        
        ticker_upper = ticker.upper()
        
        # Extract text and data from PDF (with OCR fallback for image-based PDFs)
        extractor = PDFExtractor()
        try:
            pdf_text = extractor.extract_text_from_pdf(pdf_bytes, use_ocr=True)
        except Exception as e:
            error_msg = str(e)
            if "OCR" in error_msg and "not installed" in error_msg:
                raise HTTPException(
                    status_code=400, 
                    detail=f"{error_msg}. For scanned PDFs, install OCR dependencies: pip install pytesseract pdf2image Pillow, and install Tesseract OCR from https://github.com/tesseract-ocr/tesseract"
                )
            raise HTTPException(status_code=400, detail=f"Failed to extract text from PDF: {error_msg}")
        
        if not pdf_text or len(pdf_text.strip()) < 100:
            raise HTTPException(
                status_code=400, 
                detail="Could not extract text from PDF. File may be corrupted or image-based. OCR was attempted but may need Tesseract OCR installed. See server logs for details."
            )
        
        # Llama-only mode: Check if Ollama is available
        import os
        logger.info(f"Using Textract for PDF extraction")
        
        # Use LLM to extract financial data
        extraction_error = None
        extraction_error_type = None
        updated_periods = 0  # Initialize early to avoid reference errors
        extraction_details = {
            "pdf_text_length": len(pdf_text),
            "llm_provider": "textract" if extractor.use_textract else "local",
            "extraction_method": None,
            "error_type": None,
            "error_message": None,
            "textract_enabled": extractor.use_textract if hasattr(extractor, 'use_textract') else False
        }
        
        raw_llm_response = None
        try:
            logger.info(f"Starting LLM extraction for {ticker_upper} using Llama-only mode")
            # Use per-page processing for better results on large PDFs (concurrent processing)
            extracted_data, raw_llm_response = await extractor.extract_financial_data_per_page(pdf_bytes, ticker_upper)
            logger.info(f"LLM extraction completed successfully for {ticker_upper} (concurrent per-page processing)")
            extraction_details["extraction_method"] = "textract" if extractor.use_textract else "local_extraction"
            
            # Record activity for auto-stop after processing completes
            if extractor.auto_start_ec2 and extractor._ec2_manager:
                extractor._ec2_manager.record_activity()
                logger.info("Activity recorded for EC2 auto-stop monitoring")
            if raw_llm_response:
                extraction_details["raw_llm_response_preview"] = raw_llm_response[:2000] if len(raw_llm_response) > 2000 else raw_llm_response
                extraction_details["raw_llm_response_length"] = len(raw_llm_response)
        except ValueError as e:
            # PDF text validation errors
            extraction_error = str(e)
            extraction_error_type = "validation_error"
            extraction_details["error_type"] = "validation_error"
            extraction_details["error_message"] = str(e)
            logger.error(f"PDF validation error for {ticker_upper}: {e}")
            extracted_data = {
                "income_statement": {},
                "balance_sheet": {},
                "cashflow": {},
                "key_metrics": {}
            }
        except json.JSONDecodeError as e:
            # JSON parsing errors
            extraction_error = f"Failed to parse LLM response as JSON: {str(e)}"
            extraction_error_type = "json_parse_error"
            extraction_details["error_type"] = "json_parse_error"
            extraction_details["error_message"] = str(e)
            logger.error(f"JSON parsing error for {ticker_upper}: {e}")
            extracted_data = {
                "income_statement": {},
                "balance_sheet": {},
                "cashflow": {},
                "key_metrics": {}
            }
        except Exception as e:
            # Other LLM API errors
            extraction_error = str(e)
            extraction_error_type = "llm_api_error"
            extraction_details["error_type"] = "llm_api_error"
            extraction_details["error_message"] = str(e)
            logger.error(f"LLM extraction failed for {ticker_upper}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Return empty structure but still indicate success
            extracted_data = {
                "income_statement": {},
                "balance_sheet": {},
                "cashflow": {},
                "key_metrics": {}
            }
        
        # Analyze PDF text for financial keywords to diagnose issues
        pdf_text_lower = pdf_text.lower()
        financial_keywords = {
            "income_statement": ["revenue", "net income", "operating income", "ebit", "income before tax", "earnings", "profit", "sales"],
            "balance_sheet": ["total assets", "total liabilities", "stockholder equity", "shareholder equity", "cash and cash equivalents", "total debt"],
            "cash_flow": ["operating cash flow", "cash from operations", "capital expenditures", "capex", "free cash flow", "financing activities"],
            "dates": ["2024", "2023", "2022", "fiscal year", "year ended", "quarter ended", "period ended"]
        }
        
        # Analyze extracted data to determine why it might be empty
        income_statement = extracted_data.get('income_statement', {})
        balance_sheet = extracted_data.get('balance_sheet', {})
        cashflow = extracted_data.get('cashflow', {})
        key_metrics = extracted_data.get('key_metrics', {})
        
        total_periods = (
            (len(income_statement) if isinstance(income_statement, dict) else 0) +
            (len(balance_sheet) if isinstance(balance_sheet, dict) else 0) +
            (len(cashflow) if isinstance(cashflow, dict) else 0) +
            (1 if key_metrics and isinstance(key_metrics, dict) and len(key_metrics) > 0 else 0)
        )
        
        extraction_details["income_statement_periods"] = len(income_statement) if isinstance(income_statement, dict) else 0
        extraction_details["balance_sheet_periods"] = len(balance_sheet) if isinstance(balance_sheet, dict) else 0
        extraction_details["cashflow_periods"] = len(cashflow) if isinstance(cashflow, dict) else 0
        extraction_details["has_key_metrics"] = bool(key_metrics and isinstance(key_metrics, dict) and len(key_metrics) > 0)
        extraction_details["total_periods_found"] = total_periods
        
        # Analyze what the LLM actually returned
        llm_response_analysis = extraction_details.get("llm_response_analysis", [])
        if not llm_response_analysis:
            llm_response_analysis = []
        
        if raw_llm_response:
            extraction_details["raw_llm_response_length"] = len(raw_llm_response)
            # Check if LLM returned empty objects
            if raw_llm_response.strip().startswith('{'):
                try:
                    parsed = json.loads(raw_llm_response)
                    for key, value in parsed.items():
                        if isinstance(value, dict):
                            if len(value) == 0:
                                llm_response_analysis.append(f"LLM returned empty {key} object")
                            else:
                                llm_response_analysis.append(f"LLM returned {key} with {len(value)} items (but no valid periods extracted)")
                        elif isinstance(value, list):
                            llm_response_analysis.append(f"LLM returned {key} as array with {len(value)} items")
                        else:
                            llm_response_analysis.append(f"LLM returned {key} as {type(value).__name__}")
                except:
                    llm_response_analysis.append(f"LLM response is not valid JSON structure")
            
            # Show preview of what LLM said
            preview = raw_llm_response[:1000] if len(raw_llm_response) > 1000 else raw_llm_response
            extraction_details["raw_llm_response_preview"] = preview
            extraction_details["llm_response_analysis"] = llm_response_analysis
        
        # Check for financial keywords in PDF
        found_keywords = {}
        for category, keywords in financial_keywords.items():
            matches = [kw for kw in keywords if kw in pdf_text_lower]
            if matches:
                found_keywords[category] = len(matches)
        
        extraction_details["financial_keywords_detected"] = found_keywords
        extraction_details["pdf_contains_financial_data"] = len(found_keywords) > 0
        
        # Log extracted data for debugging
        logger.info(f"Extracted data for {ticker_upper}: {json.dumps(extracted_data, indent=2, default=str)}")
        logger.info(f"Extracted data keys: {list(extracted_data.keys())}")
        logger.info(f"Income statement periods: {len(income_statement) if isinstance(income_statement, dict) else 0}")
        logger.info(f"Balance sheet periods: {len(balance_sheet) if isinstance(balance_sheet, dict) else 0}")
        logger.info(f"Cashflow periods: {len(cashflow) if isinstance(cashflow, dict) else 0}")
        
        # Note: raw_llm_response is already set from the extraction call above
        # If it wasn't set, try to get it from extraction_details
        if not raw_llm_response and extraction_details.get("raw_llm_response_preview"):
            # Try to reconstruct from preview if available
            raw_llm_response = extraction_details.get("raw_llm_response_preview", "")
        
        if total_periods == 0 and not extraction_error and not raw_llm_response:
            # Fallback: serialize extracted_data if we don't have raw response
            raw_llm_response = json.dumps(extracted_data, indent=2, default=str)
            logger.warning(f"LLM returned data structure but no periods extracted. Using serialized extracted_data as fallback.")
            if len(raw_llm_response) > 0:
                extraction_details["raw_llm_response_preview"] = raw_llm_response[:1000]  # First 1000 chars for debugging
        
        # Store extracted data in both in-memory store (for backward compatibility) and database
        if ticker_upper not in manual_data_store:
            manual_data_store[ticker_upper] = {}
        
        # Also save to database for persistence
        from app.database.db_service import DatabaseService
        db_service = DatabaseService(db_path="stock_analysis.db")
        
        updated_periods = 0
        db_save_results = {
            'saved': 0,
            'failed': 0,
            'verified': 0,
            'details': []
        }
        
        # Process income statement data
        if income_statement and isinstance(income_statement, dict):
            for period, data in income_statement.items():
                entry_key = f"income_statement_{period}"
                # Store in-memory (backward compatibility)
                manual_data_store[ticker_upper][entry_key] = {
                    'ticker': ticker_upper,
                    'data_type': 'income_statement',
                    'period': period,
                    'data': data
                }
                # Save to database
                save_success = db_service.save_ai_extracted_data(
                    ticker=ticker_upper,
                    data_type='income_statement',
                    period=period,
                    data=data,
                    source='pdf_upload',
                    extraction_method='llama_vision'
                )
                if save_success:
                    db_save_results['saved'] += 1
                    # Verify the save by reading it back
                    saved_data = db_service.get_ai_extracted_data(ticker_upper, 'income_statement')
                    if saved_data and period in saved_data:
                        db_save_results['verified'] += 1
                        db_save_results['details'].append(f"Income Statement {period}: Saved and verified ✓")
                    else:
                        db_save_results['details'].append(f"Income Statement {period}: Saved but verification failed ⚠")
                else:
                    db_save_results['failed'] += 1
                    db_save_results['details'].append(f"Income Statement {period}: Save failed ✗")
                updated_periods += 1
        
        # Process balance sheet data
        if balance_sheet and isinstance(balance_sheet, dict):
            for period, data in balance_sheet.items():
                entry_key = f"balance_sheet_{period}"
                # Store in-memory (backward compatibility)
                manual_data_store[ticker_upper][entry_key] = {
                    'ticker': ticker_upper,
                    'data_type': 'balance_sheet',
                    'period': period,
                    'data': data
                }
                # Save to database
                save_success = db_service.save_ai_extracted_data(
                    ticker=ticker_upper,
                    data_type='balance_sheet',
                    period=period,
                    data=data,
                    source='pdf_upload',
                    extraction_method='llama_vision'
                )
                if save_success:
                    db_save_results['saved'] += 1
                    # Verify the save by reading it back
                    saved_data = db_service.get_ai_extracted_data(ticker_upper, 'balance_sheet')
                    if saved_data and period in saved_data:
                        db_save_results['verified'] += 1
                        db_save_results['details'].append(f"Balance Sheet {period}: Saved and verified ✓")
                    else:
                        db_save_results['details'].append(f"Balance Sheet {period}: Saved but verification failed ⚠")
                else:
                    db_save_results['failed'] += 1
                    db_save_results['details'].append(f"Balance Sheet {period}: Save failed ✗")
                updated_periods += 1
        
        # Process cash flow data
        if cashflow and isinstance(cashflow, dict):
            for period, data in cashflow.items():
                entry_key = f"cashflow_{period}"
                # Store in-memory (backward compatibility)
                manual_data_store[ticker_upper][entry_key] = {
                    'ticker': ticker_upper,
                    'data_type': 'cashflow',
                    'period': period,
                    'data': data
                }
                # Save to database
                save_success = db_service.save_ai_extracted_data(
                    ticker=ticker_upper,
                    data_type='cashflow',
                    period=period,
                    data=data,
                    source='pdf_upload',
                    extraction_method='llama_vision'
                )
                if save_success:
                    db_save_results['saved'] += 1
                    # Verify the save by reading it back
                    saved_data = db_service.get_ai_extracted_data(ticker_upper, 'cashflow')
                    if saved_data and period in saved_data:
                        db_save_results['verified'] += 1
                        db_save_results['details'].append(f"Cash Flow {period}: Saved and verified ✓")
                    else:
                        db_save_results['details'].append(f"Cash Flow {period}: Saved but verification failed ⚠")
                else:
                    db_save_results['failed'] += 1
                    db_save_results['details'].append(f"Cash Flow {period}: Save failed ✗")
                updated_periods += 1
        
        # Process key metrics
        if 'key_metrics' in extracted_data and extracted_data['key_metrics']:
            # Store key metrics with a special period
            entry_key = "key_metrics_latest"
            # Store in-memory (backward compatibility)
            manual_data_store[ticker_upper][entry_key] = {
                'ticker': ticker_upper,
                'data_type': 'key_metrics',
                'period': 'latest',
                'data': extracted_data['key_metrics']
            }
            # Save to database
            save_success = db_service.save_ai_extracted_data(
                ticker=ticker_upper,
                data_type='key_metrics',
                period='latest',
                data=extracted_data['key_metrics'],
                source='pdf_upload',
                extraction_method='llama_vision'
            )
            if save_success:
                db_save_results['saved'] += 1
                # Verify the save by reading it back
                saved_data = db_service.get_ai_extracted_data(ticker_upper, 'key_metrics')
                if saved_data and 'latest' in saved_data:
                    db_save_results['verified'] += 1
                    db_save_results['details'].append(f"Key Metrics: Saved and verified ✓")
                else:
                    db_save_results['details'].append(f"Key Metrics: Saved but verification failed ⚠")
            else:
                db_save_results['failed'] += 1
                db_save_results['details'].append(f"Key Metrics: Save failed ✗")
            updated_periods += 1
        
        # Add database save results to extraction details
        extraction_details['database_save'] = db_save_results
        logger.info(f"Database save results for {ticker_upper}: {db_save_results['saved']} saved, {db_save_results['verified']} verified, {db_save_results['failed']} failed")
        
        # Add database save feedback to message
        db_feedback = ""
        if db_save_results['saved'] > 0:
            if db_save_results['verified'] == db_save_results['saved']:
                db_feedback = f"\n\n✅ Database: All {db_save_results['saved']} data period(s) saved and verified successfully for {ticker_upper}."
            elif db_save_results['verified'] > 0:
                db_feedback = f"\n\n⚠️ Database: {db_save_results['saved']} period(s) saved, {db_save_results['verified']} verified, {db_save_results['failed']} failed for {ticker_upper}."
            else:
                db_feedback = f"\n\n⚠️ Database: {db_save_results['saved']} period(s) saved but verification incomplete for {ticker_upper}."
        elif db_save_results['failed'] > 0:
            db_feedback = f"\n\n❌ Database: Failed to save {db_save_results['failed']} data period(s) for {ticker_upper}."
        
        # Create appropriate message with specific feedback
        if updated_periods == 0:
            # Build detailed error message
            error_parts = []
            
            # Llama-only mode: Check if Ollama is running
            llama_url = os.getenv("LLAMA_API_URL", "http://localhost:11434")
            if extraction_error_type == "validation_error":
                error_parts.append(f"PDF text validation failed: {extraction_error}")
            elif extraction_error_type == "json_parse_error":
                error_parts.append(f"LLM returned invalid JSON format: {extraction_error}")
            elif extraction_error_type == "llm_api_error":
                if "api key" in extraction_error.lower() or "authentication" in extraction_error.lower():
                    error_parts.append(f"API authentication failed: {extraction_error}")
                elif "rate limit" in extraction_error.lower() or "quota" in extraction_error.lower():
                    error_parts.append(f"API rate limit exceeded: {extraction_error}")
                else:
                    error_parts.append(f"LLM API error: {extraction_error}")
            elif extraction_error:
                error_parts.append(f"Extraction error: {extraction_error}")
            
            # Analyze what went wrong with specific diagnostics
            if total_periods == 0:
                diagnostic_parts = []
                
                # Check if PDF contains financial keywords
                if extraction_details.get("pdf_contains_financial_data"):
                    keywords_info = extraction_details.get("financial_keywords_detected", {})
                    keyword_summary = ", ".join([f"{k}: {v} matches" for k, v in keywords_info.items()])
                    diagnostic_parts.append(f"PDF text analysis: Financial keywords detected ({keyword_summary}), but LLM did not extract structured data.")
                else:
                    diagnostic_parts.append("PDF text analysis: No financial keywords detected. The PDF may not contain standard financial statements.")
                
                # Check what LLM returned
                provider_name = extraction_details.get("llm_provider", "unknown").upper()
                if llm_response_analysis:
                    diagnostic_parts.append(f"LLM response analysis ({provider_name}): {'; '.join(llm_response_analysis)}")
                
                # Check raw LLM response
                if raw_llm_response:
                    preview = raw_llm_response[:500].replace('\n', ' ').replace('\r', ' ')
                    provider_name = extraction_details.get("llm_provider", "unknown").upper()
                    diagnostic_parts.append(f"LLM raw response preview ({provider_name}): {preview}...")
                
                # Check structure
                provider_name = extraction_details.get("llm_provider", "unknown").upper()
                if income_statement == {} and balance_sheet == {} and cashflow == {} and not key_metrics:
                    diagnostic_parts.append(f"LLM ({provider_name}) returned empty objects for all financial statement types.")
                else:
                    diagnostic_parts.append(f"LLM ({provider_name}) returned partial structure: Income Statement ({extraction_details['income_statement_periods']} periods), Balance Sheet ({extraction_details['balance_sheet_periods']} periods), Cash Flow ({extraction_details['cashflow_periods']} periods), Key Metrics ({'Yes' if extraction_details.get('has_key_metrics') else 'No'})")
                
                # Add actionable advice
                provider_name = extraction_details.get("llm_provider", "unknown").upper()
                if extraction_details.get("pdf_contains_financial_data") and total_periods == 0:
                    # Llama-only mode: All extractions use Llama
                    # Textract-based extraction troubleshooting
                    textract_enabled = extraction_details.get("textract_enabled", False)
                    
                    if textract_enabled:
                        diagnostic_parts.append("RECOMMENDATION: PDF contains financial data but Textract extraction failed.")
                        diagnostic_parts.append("Troubleshooting: (1) Check AWS Textract IAM permissions, (2) Verify AWS credentials, (3) Ensure PDF has complete financial statements, (4) Verify document format matches 10-K/annual report structure")
                    else:
                        diagnostic_parts.append("RECOMMENDATION: PDF contains financial data but local extraction failed.")
                        diagnostic_parts.append("Troubleshooting: (1) Enable Textract (USE_TEXTRACT=true), (2) Configure AWS credentials, (3) Ensure PDF has complete financial statements")
                elif not extraction_details.get("pdf_contains_financial_data"):
                    diagnostic_parts.append("RECOMMENDATION: Upload a document with complete financial statements (10-K filing, annual report, or quarterly report with Income Statement, Balance Sheet, and Cash Flow sections).")
                
                error_parts.extend(diagnostic_parts)
            
            # Check PDF text quality
            if extraction_details["pdf_text_length"] < 500:
                error_parts.append(f"PDF text is very short ({extraction_details['pdf_text_length']} characters). The PDF may be image-based or corrupted.")
            elif extraction_details["pdf_text_length"] < 1000:
                error_parts.append(f"PDF text is short ({extraction_details['pdf_text_length']} characters). The document may not contain complete financial statements.")
            
            if not error_parts:
                error_parts.append("No financial data could be extracted. The PDF may not contain standard financial statements or the format may not be recognized.")
            
            # Format diagnostics with better structure
            if len(error_parts) > 1:
                error_message = "\n".join([f"• {part}" for part in error_parts])
            else:
                error_message = error_parts[0] if error_parts else "Unknown error"
            message = f"PDF processed successfully! Extracted {updated_periods} data period(s) for {ticker_upper}.\n\nDiagnostics:\n{error_message}{db_feedback}"
        else:
            message = f"PDF processed successfully! Extracted {updated_periods} data period(s) for {ticker_upper}. The analysis will be updated automatically.{db_feedback}"
        
        return ManualDataResponse(
            success=True,
            message=message,
            updated_periods=updated_periods,
            extracted_data=extracted_data,  # Return extracted data for UI display
            extraction_details=extraction_details  # Return detailed extraction information
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Unexpected error in upload_pdf for {ticker}: {e}")
        logger.error(f"Traceback: {error_traceback}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.get("/check-ai-data/{ticker}")
async def check_ai_data(ticker: str):
    """
    Check if AI-extracted financial data exists for a ticker
    Returns information about available data and suggests uploading PDF if missing
    """
    try:
        from app.database.db_service import DatabaseService
        db_service = DatabaseService(db_path="stock_analysis.db")
        
        has_data = db_service.has_ai_extracted_data(ticker)
        ai_data = db_service.get_ai_extracted_data(ticker) if has_data else {}
        
        # Count periods
        income_periods = len(ai_data.get('income_statement', {}))
        balance_periods = len(ai_data.get('balance_sheet', {}))
        cashflow_periods = len(ai_data.get('cashflow', {}))
        has_key_metrics = 'key_metrics' in ai_data and bool(ai_data['key_metrics'])
        
        return {
            "ticker": ticker.upper(),
            "has_ai_data": has_data,
            "data_summary": {
                "income_statement_periods": income_periods,
                "balance_sheet_periods": balance_periods,
                "cashflow_periods": cashflow_periods,
                "has_key_metrics": has_key_metrics
            },
            "suggestion": "Upload a PDF financial statement to extract missing data" if not has_data else "AI-extracted data is available and will be used in analysis"
        }
    except Exception as e:
        logger.error(f"Error checking AI data for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking AI data: {str(e)}")


@router.get("/quote/{ticker}", response_model=QuoteResponse)
async def get_quote(ticker: str):
    """
    Get quick quote for a ticker (price and basic info)
    """
    try:
        data_fetcher = DataFetcher()
        company_data = await data_fetcher.fetch_company_data(ticker)
        
        if not company_data:
            raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
        
        return QuoteResponse(
            ticker=ticker.upper(),
            companyName=company_data.company_name,
            currentPrice=company_data.current_price,
            marketCap=company_data.market_cap,
            sector=company_data.sector,
            industry=company_data.industry
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", response_model=CompareResponse)
async def compare_stocks(request: CompareRequest):
    """
    Compare multiple stocks side-by-side
    """
    try:
        analyses = []
        for ticker in request.tickers:
            # Fetch data
            data_fetcher = DataFetcher()
            company_data = await data_fetcher.fetch_company_data(ticker)
            
            if not company_data:
                continue
            
            # Apply manual data if available (in-memory store - backward compatibility)
            if ticker.upper() in manual_data_store:
                manual_data = manual_data_store[ticker.upper()]
                _apply_manual_data(company_data, manual_data)
            
            # Also load AI-extracted data from database
            try:
                from app.database.db_service import DatabaseService
                db_service = DatabaseService(db_path="stock_analysis.db")
                ai_data = db_service.get_ai_extracted_data(ticker)
                
                if ai_data:
                    # Apply AI-extracted data to company_data
                    _apply_ai_extracted_data(company_data, ai_data)
                    logger.info(f"Loaded AI-extracted data from database for {ticker}")
            except Exception as e:
                logger.warning(f"Error loading AI-extracted data from database for {ticker}: {e}")
                # Continue without AI data if database load fails
            
            # Get risk-free rate
            risk_free_rate = data_fetcher.get_risk_free_rate()
            
            # Calculate intrinsic value
            intrinsic_calc = IntrinsicValueCalculator(company_data, risk_free_rate)
            valuation_result = intrinsic_calc.calculate()
            
            # Analyze financial health
            health_analyzer = FinancialHealthAnalyzer(company_data)
            health_result = health_analyzer.analyze()
            
            # Analyze business quality
            quality_analyzer = BusinessQualityAnalyzer(company_data)
            quality_result = quality_analyzer.analyze()
            
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
            
            # Build analysis
            from datetime import datetime
            from dataclasses import asdict
            import math
            
            # Convert dataclass to dict for Pydantic, handling NaN values
            valuation_dict = asdict(valuation_result.breakdown)
            # Replace NaN with 0.0 for Pydantic validation
            for key, value in valuation_dict.items():
                if isinstance(value, float) and math.isnan(value):
                    valuation_dict[key] = 0.0
            
            analysis = StockAnalysis(
                ticker=ticker.upper(),
                companyName=company_data.company_name,
                currentPrice=company_data.current_price,
                fairValue=valuation_result.fair_value,
                marginOfSafety=margin_result.margin_of_safety,
                upsidePotential=margin_result.upside_potential,
                priceToIntrinsicValue=margin_result.price_to_intrinsic_value,
                recommendation=margin_result.recommendation,
                recommendationReasoning=margin_result.reasoning,
                valuation=valuation_dict,
                financialHealth=health_result,
                businessQuality=quality_result,
                timestamp=datetime.now()
            )
            
            analyses.append(analysis)
        
        return CompareResponse(analyses=analyses)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BatchAnalysisRequest(BaseModel):
    tickers: ListType[str]
    exchange_name: str = "Custom"  # Kept for backward compatibility but not used in UI
    skip_existing: bool = True


@router.post("/batch-analyze")
async def batch_analyze_stocks(request: BatchAnalysisRequest):
    """
    Analyze multiple stocks in batch with rate limiting
    Returns summary with results
    """
    # Import here to avoid circular import
    from app.api.batch_analysis import BatchAnalyzer
    
    try:
        if not request.tickers or len(request.tickers) == 0:
            raise HTTPException(status_code=400, detail="Tickers list cannot be empty")
        
        if len(request.tickers) > 1000:
            raise HTTPException(status_code=400, detail="Maximum 1000 tickers per batch")
        
        # Create batch analyzer
        analyzer = BatchAnalyzer(
            max_concurrent=5,
            requests_per_minute=30,
            results_dir="batch_results",
            use_database=True,
            use_dynamodb=None,  # Auto-detect from env
            dynamodb_table="stock-analyses",
            dynamodb_region="us-east-1"
        )
        
        # Run analysis
        from datetime import date
        analysis_date = date.today().isoformat()
        
        summary = await analyzer.analyze_ticker_list(
            tickers=request.tickers,
            exchange_name=request.exchange_name,
            resume=True,
            skip_existing=request.skip_existing,
            analysis_date=analysis_date
        )
        
        return {
            "success": True,
            "summary": summary,
            "message": f"Batch analysis completed. Processed {summary.get('successful', 0)} tickers successfully, {summary.get('failed', 0)} failed."
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is (they'll be handled by exception handler with CORS)
        raise
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error in batch_analyze_stocks: {str(e)}")
        print(f"Traceback:\n{error_traceback}")
        # Raise as HTTPException so it gets CORS headers
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")


@router.get("/batch-results")
async def get_batch_results(
    exchange: str = Query(..., description="Exchange name"),
    analysis_date: Optional[str] = Query(None, description="Analysis date (YYYY-MM-DD), defaults to today")
):
    """
    Get batch analysis results sorted by fair value/share price percentage (lowest to highest)
    Returns list of tickers with their analysis data
    """
    try:
        from datetime import date
        from app.database.db_service import DatabaseService
        import os
        
        if analysis_date is None:
            analysis_date = date.today().isoformat()
        
        # Initialize database service
        use_dynamodb = os.getenv('USE_DYNAMODB', 'false').lower() == 'true'
        if use_dynamodb:
            from app.database.dynamodb_service import DynamoDBService
            db_service = DynamoDBService(
                table_name="stock-analyses",
                region="us-east-1"
            )
        else:
            db_service = DatabaseService(db_path="stock_analysis.db")
        
        # Get all analyses for this exchange and date
        print(f"Fetching batch results for exchange: {exchange}, date: {analysis_date}")
        analyses = db_service.get_exchange_analyses(exchange, analysis_date)
        print(f"Found {len(analyses)} analyses for exchange '{exchange}'")
        
        # Debug: If no results, try to see what exchanges exist
        if len(analyses) == 0:
            print(f"Warning: No analyses found for exchange '{exchange}' on {analysis_date}")
            if not use_dynamodb:
                # Try to see what exchanges exist in the database
                from app.database.models import StockAnalysis
                session = db_service.get_session()
                try:
                    from sqlalchemy import distinct
                    existing_exchanges = session.query(distinct(StockAnalysis.exchange)).filter(
                        StockAnalysis.analysis_date == analysis_date,
                        StockAnalysis.status == 'success'
                    ).all()
                    exchanges_list = [e[0] for e in existing_exchanges if e[0]]
                    print(f"Available exchanges in database for {analysis_date}: {exchanges_list}")
                    
                    # If exchange is 'Custom' and no results, try getting all analyses for today (in case exchange wasn't set)
                    if exchange.lower() == 'custom':
                        print("Trying to get all analyses for today (exchange may be NULL or different)")
                        all_analyses = session.query(StockAnalysis).filter(
                            StockAnalysis.analysis_date == analysis_date,
                            StockAnalysis.status == 'success'
                        ).all()
                        print(f"Found {len(all_analyses)} total analyses for date {analysis_date}")
                        # Filter to only include those with NULL exchange or 'Custom' exchange
                        filtered_analyses = [
                            a for a in all_analyses 
                            if not a.exchange or a.exchange.lower() == 'custom'
                        ]
                        if len(filtered_analyses) > 0:
                            analyses = [a.to_dict() for a in filtered_analyses]
                            print(f"Using {len(analyses)} analyses (NULL or Custom exchange)")
                        else:
                            # If still nothing, use all analyses for today
                            analyses = [a.to_dict() for a in all_analyses]
                            print(f"Using all {len(analyses)} analyses for today (ignoring exchange filter)")
                except Exception as e:
                    print(f"Error checking available exchanges: {e}")
                finally:
                    session.close()
        
        # Calculate fair value percentage and sort
        results = []
        for analysis in analyses:
            current_price = analysis.get('current_price')
            fair_value = analysis.get('fair_value')
            
            # Skip if missing essential data
            if not current_price or not fair_value or current_price <= 0:
                continue
                
            fair_value_pct = (fair_value / current_price) * 100
            
            # Extract company name from analysis_data if not in top level
            company_name = analysis.get('company_name')
            if not company_name and analysis.get('analysis_data'):
                analysis_data = analysis.get('analysis_data', {})
                if isinstance(analysis_data, dict):
                    company_name = analysis_data.get('companyName') or analysis_data.get('company_name')
            
            # Fallback to ticker if no company name found
            if not company_name:
                company_name = analysis.get('ticker', 'N/A')
            
            results.append({
                'ticker': analysis.get('ticker'),
                'company_name': company_name,
                'current_price': float(current_price),
                'fair_value': float(fair_value),
                'fair_value_pct': round(fair_value_pct, 2),
                'margin_of_safety_pct': float(analysis.get('margin_of_safety_pct')) if analysis.get('margin_of_safety_pct') is not None else None,
                'recommendation': analysis.get('recommendation'),
                'financial_health_score': float(analysis.get('financial_health_score')) if analysis.get('financial_health_score') is not None else None,
                'business_quality_score': float(analysis.get('business_quality_score')) if analysis.get('business_quality_score') is not None else None,
            })
        
        # Sort by fair_value_pct (lowest to highest - best deals first)
        results.sort(key=lambda x: x['fair_value_pct'] if x['fair_value_pct'] is not None else float('inf'))
        
        return {
            'exchange': exchange,
            'analysis_date': analysis_date,
            'total': len(results),
            'results': results
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")


# Watchlist endpoints
@router.get("/watchlist")
async def get_watchlist():
    """Get all stocks in the watchlist - optimized for fast loading"""
    try:
        from app.database.db_service import DatabaseService
        from datetime import date
        db_service = DatabaseService(db_path="stock_analysis.db")
        
        watchlist_items = db_service.get_watchlist()
        today = date.today().isoformat()
        
        # Batch fetch all analysis data in one query for better performance
        tickers = [item['ticker'] for item in watchlist_items]
        latest_analyses = {}
        
        if tickers:
            try:
                # Use efficient batch query method
                latest_analyses = db_service.get_latest_analyses_batch(tickers)
            except Exception as e:
                logger.warning(f"Error batch fetching analysis data: {e}")
                latest_analyses = {}
        
        # Enrich items with cached analysis data only (no live API calls for performance)
        enriched_items = []
        for item in watchlist_items:
            ticker = item['ticker']
            latest_analysis = latest_analyses.get(ticker)
            
            # Determine cache status
            cache_status = "missing"
            needs_refresh = True
            
            if latest_analysis:
                analysis_date = latest_analysis.get('analysis_date')
                if analysis_date == today:
                    cache_status = "fresh"
                    needs_refresh = False
                else:
                    cache_status = "stale"
                    needs_refresh = True
                
                # Update item with essential analysis data only
                item['current_price'] = latest_analysis.get('current_price')
                item['fair_value'] = latest_analysis.get('fair_value')
                item['margin_of_safety_pct'] = latest_analysis.get('margin_of_safety_pct')
                item['recommendation'] = latest_analysis.get('recommendation')
                item['last_analyzed_at'] = latest_analysis.get('analyzed_at')
                item['analysis_date'] = analysis_date
                item['financial_health_score'] = latest_analysis.get('financial_health_score')
                item['business_quality_score'] = latest_analysis.get('business_quality_score')
            
            # Add cache information
            item['cache_info'] = {
                'status': cache_status,
                'needs_refresh': needs_refresh,
                'last_updated': latest_analysis.get('analysis_date') if latest_analysis else None,
                'is_today': latest_analysis.get('analysis_date') == today if latest_analysis else False
            }
            
            # Note: Removed live price fetching for performance
            # Live prices will be fetched on individual stock view or manual refresh
            
            enriched_items.append(item)
        
        logger.info(f"Watchlist loaded: {len(enriched_items)} items (optimized - no live API calls)")
        return {"items": enriched_items, "total": len(enriched_items)}
        
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist/live-prices")
async def get_watchlist_live_prices():
    """Get live prices for all watchlist items - separate endpoint for performance"""
    try:
        from app.database.db_service import DatabaseService
        import concurrent.futures
        import functools
        
        db_service = DatabaseService(db_path="stock_analysis.db")
        
        watchlist_items = db_service.get_watchlist()
        tickers = [item['ticker'] for item in watchlist_items]
        
        live_prices = {}
        yahoo_client = YahooFinanceClient()
        
        # Create a wrapper function with timeout for individual ticker calls
        def get_quote_with_timeout(ticker, timeout_seconds=20):
            """Get quote with a timeout to prevent hanging"""
            try:
                import signal
                import time
                
                start_time = time.time()
                result = yahoo_client.get_quote(ticker)
                end_time = time.time()
                
                # Log timing for debugging
                duration = end_time - start_time
                logger.info(f"Quote for {ticker} took {duration:.2f} seconds")
                
                return result
            except Exception as e:
                logger.warning(f"Timeout or error getting quote for {ticker}: {e}")
                return {
                    'error': 'Timeout or API error',
                    'error_detail': f'Request for {ticker} failed: {str(e)}',
                    'symbol': ticker
                }
        
        # Process tickers in parallel with a reasonable timeout
        max_workers = min(4, len(tickers))  # Limit concurrent requests to avoid overwhelming API
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_ticker = {
                executor.submit(get_quote_with_timeout, ticker): ticker 
                for ticker in tickers
            }
            
            # Collect results with overall timeout
            for future in concurrent.futures.as_completed(future_to_ticker, timeout=45):
                ticker = future_to_ticker[future]
                try:
                    quote = future.result(timeout=25)  # Individual result timeout
                    
                    if quote:
                        if quote.get('success'):
                            # Successful quote
                            live_prices[ticker] = {
                                'price': quote.get('price'),
                                'company_name': quote.get('company_name', ticker),
                                'success': True,
                                'comment': _format_api_attempts_comment(quote.get('api_attempts', []), success=True)
                            }
                            # Add warning if company info was partially unavailable
                            if quote.get('info_warning'):
                                live_prices[ticker]['comment'] += f" Warning: {quote.get('info_warning')}"
                        else:
                            # Quote returned with error details
                            live_prices[ticker] = {
                                'error': quote.get('error', 'Unknown error'),
                                'success': False,
                                'comment': _format_api_attempts_comment(quote.get('api_attempts', []), success=False)
                            }
                    else:
                        # This shouldn't happen with the new implementation, but keep as fallback
                        live_prices[ticker] = {
                            'error': 'No data returned',
                            'success': False,
                            'comment': 'Yahoo Finance API returned empty response - ticker may not exist or be delisted'
                        }
                        
                except concurrent.futures.TimeoutError:
                    logger.warning(f"Timeout getting live price for {ticker}")
                    live_prices[ticker] = {
                        'error': 'Timeout',
                        'success': False,
                        'comment': f'Request for {ticker} timed out after 25 seconds - Yahoo Finance API may be slow or rate-limited'
                    }
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"Error in future result for {ticker}: {error_msg}")
                    live_prices[ticker] = {
                        'error': 'Processing error',
                        'success': False,
                        'comment': f'Error processing request for {ticker}: {error_msg}'
                    }
        
        # Handle any tickers that weren't processed (shouldn't happen with proper timeout handling)
        for ticker in tickers:
            if ticker not in live_prices:
                live_prices[ticker] = {
                    'error': 'Not processed',
                    'success': False,
                    'comment': f'Request for {ticker} was not completed within the timeout period'
                }
        
        logger.info(f"Live prices completed for {len(live_prices)} tickers")
        return {"live_prices": live_prices}
        
    except Exception as e:
        logger.error(f"Error getting live prices: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlist/{ticker}")
async def add_to_watchlist(
    ticker: str,
    company_name: Optional[str] = Query(None),
    exchange: Optional[str] = Query(None),
    notes: Optional[str] = Query(None),
    auto_detect_business_type: bool = Query(True, description="Automatically detect business type using AI")
):
    """Add a stock to the watchlist"""
    try:
        from app.database.db_service import DatabaseService
        db_service = DatabaseService(db_path="stock_analysis.db")
        
        # Try to get company name and info from API if not provided
        company_info = {}
        if not company_name:
            try:
                yahoo_client = YahooFinanceClient()
                loop = asyncio.get_event_loop()
                quote = await loop.run_in_executor(None, yahoo_client.get_quote, ticker.upper())
                if quote:
                    company_name = quote.get('company_name')
                    company_info = {
                        'company_name': company_name,
                        'sector': quote.get('sector'),
                        'industry': quote.get('industry'),
                        'description': quote.get('long_business_summary') or quote.get('business_summary', ''),
                        'business_summary': quote.get('long_business_summary') or quote.get('business_summary', '')
                    }
            except Exception as e:
                logger.warning(f"Could not get company name for {ticker}: {e}")
        
        # Auto-detect business type if enabled
        detected_business_type = None
        if auto_detect_business_type and company_info:
            try:
                from app.ai.business_type_detector import BusinessTypeDetector
                detector = BusinessTypeDetector()
                detected_business_type = detector.detect_with_fallback(
                    company_info=company_info,
                    sector=company_info.get('sector'),
                    industry=company_info.get('industry')
                )
                logger.info(f"Auto-detected business type for {ticker}: {detected_business_type.value}")
            except Exception as e:
                logger.warning(f"Error in auto-detecting business type for {ticker}: {e}")
        
        success = db_service.add_to_watchlist(
            ticker=ticker.upper(),
            company_name=company_name,
            exchange=exchange,
            notes=notes
        )
        
        response = {
            "success": True,
            "message": f"{ticker.upper()} added to watchlist"
        }
        
        if detected_business_type:
            response["detected_business_type"] = detected_business_type.value
            response["message"] += f" (Auto-detected business type: {detected_business_type.value.replace('_', ' ').title()})"
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to watchlist: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/watchlist/{ticker}")
async def remove_from_watchlist(ticker: str):
    """Remove a stock from the watchlist"""
    try:
        from app.database.db_service import DatabaseService
        db_service = DatabaseService(db_path="stock_analysis.db")
        
        success = db_service.remove_from_watchlist(ticker.upper())
        
        if success:
            return {"success": True, "message": f"{ticker.upper()} removed from watchlist"}
        else:
            raise HTTPException(status_code=404, detail="Stock not found in watchlist")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from watchlist: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist/{ticker}")
async def get_watchlist_item(ticker: str, force_refresh: bool = Query(False, description="Force refresh analysis data")):
    """Get detailed information for a watchlist item with smart caching"""
    try:
        from app.database.db_service import DatabaseService
        from datetime import date, datetime
        db_service = DatabaseService(db_path="stock_analysis.db")
        
        # Get watchlist item
        watchlist_item = db_service.get_watchlist_item(ticker.upper())
        if not watchlist_item:
            raise HTTPException(status_code=404, detail="Stock not found in watchlist")
        
        # Check if we need to refresh analysis data
        should_refresh_analysis = force_refresh
        analysis_cache_status = "fresh"
        
        if not force_refresh:
            # Check if analysis exists for today
            today = date.today().isoformat()
            existing_analysis = db_service.get_analysis(ticker.upper(), today)
            
            if not existing_analysis or existing_analysis.get('status') != 'success':
                # No analysis for today, check latest analysis
                latest_analysis = db_service.get_latest_analysis(ticker.upper())
                if latest_analysis:
                    # Check if latest analysis is from today
                    analysis_date = latest_analysis.get('analysis_date')
                    if analysis_date != today:
                        should_refresh_analysis = True
                        analysis_cache_status = "stale"
                        logger.info(f"Analysis for {ticker} is from {analysis_date}, will refresh")
                    else:
                        analysis_cache_status = "fresh"
                else:
                    should_refresh_analysis = True
                    analysis_cache_status = "missing"
                    logger.info(f"No analysis found for {ticker}, will refresh")
        
        # Get or refresh analysis data
        if should_refresh_analysis:
            logger.info(f"Refreshing analysis for {ticker} (cache_status: {analysis_cache_status})")
            try:
                # Run new analysis
                analysis = await _analyze_stock_with_progress(ticker.upper())
                
                # Save to database
                from datetime import date
                db_service.save_analysis(
                    ticker=ticker.upper(),
                    analysis_date=date.today().isoformat(),
                    analysis_data=analysis.model_dump(mode='json'),
                    # Extract key fields for indexing
                    current_price=analysis.currentPrice,
                    fair_value=analysis.fairValue,
                    margin_of_safety_pct=analysis.marginOfSafety,
                    recommendation=analysis.recommendation,
                    financial_health_score=analysis.financialHealthScore,
                    business_quality_score=analysis.businessQualityScore,
                    management_quality_score=analysis.managementQualityScore,
                    market_cap=analysis.marketCap,
                    sector=analysis.sector,
                    industry=analysis.industry,
                    pe_ratio=analysis.priceRatios.pe if analysis.priceRatios else None,
                    pb_ratio=analysis.priceRatios.pb if analysis.priceRatios else None,
                    ps_ratio=analysis.priceRatios.ps if analysis.priceRatios else None,
                    revenue_growth_1y=analysis.growthMetrics.revenueGrowth1Y if analysis.growthMetrics else None,
                    earnings_growth_1y=analysis.growthMetrics.earningsGrowth1Y if analysis.growthMetrics else None,
                    exchange=analysis.exchange,
                    company_name=analysis.companyName,
                    currency=analysis.currency
                )
                
                # Update watchlist item with latest analysis data
                db_service.update_watchlist_item(
                    ticker=ticker.upper(),
                    current_price=analysis.currentPrice,
                    fair_value=analysis.fairValue,
                    margin_of_safety_pct=analysis.marginOfSafety,
                    recommendation=analysis.recommendation,
                    last_analyzed_at=datetime.utcnow()
                )
                
                latest_analysis = analysis.model_dump(mode='json')
                analysis_cache_status = "refreshed"
                
            except Exception as e:
                logger.error(f"Error refreshing analysis for {ticker}: {e}")
                # Fall back to latest cached analysis if available
                latest_analysis = db_service.get_latest_analysis(ticker.upper())
                if latest_analysis:
                    analysis_cache_status = "refresh_failed_using_cache"
                else:
                    analysis_cache_status = "refresh_failed_no_cache"
                    latest_analysis = None
        else:
            # Use cached analysis
            latest_analysis = db_service.get_latest_analysis(ticker.upper())
        
        # Get all AI-extracted financial data
        ai_data = db_service.get_ai_extracted_data(ticker.upper())
        
        # Transform key_metrics structure: flatten 'latest' period for frontend
        if 'key_metrics' in ai_data and 'latest' in ai_data['key_metrics']:
            ai_data['key_metrics'] = ai_data['key_metrics']['latest']
        
        # Get current quote (always fresh for price updates)
        current_quote = None
        price_error = None
        try:
            # Try Yahoo Finance first
            yahoo_client = YahooFinanceClient()
            loop = asyncio.get_event_loop()
            current_quote = await loop.run_in_executor(None, yahoo_client.get_quote, ticker.upper())
            
            # If Yahoo Finance fails, try backup sources
            if not current_quote:
                logger.debug(f"Yahoo Finance failed for {ticker}, trying backup sources...")
                from app.data.backup_clients import BackupDataFetcher
                backup_fetcher = BackupDataFetcher()
                
                backup_price = backup_fetcher.get_current_price(ticker)
                if backup_price:
                    backup_info = backup_fetcher.get_company_info(ticker)
                    current_quote = {
                        'ticker': ticker.upper(),
                        'price': backup_price,
                        'companyName': backup_info.get('companyName', ticker.upper()) if backup_info else ticker.upper()
                    }
                    logger.info(f"Got quote from backup source for {ticker}")
                else:
                    price_error = "Price data not available from any source"
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Could not get quote for {ticker}: {error_msg}")
            if '429' in error_msg or 'rate limit' in error_msg.lower():
                price_error = "Price API rate limited - please try again later"
            elif 'timeout' in error_msg.lower():
                price_error = "Price API timeout - please try again"
            else:
                price_error = "Price data unavailable - API may be temporarily unavailable"
        
        return {
            "watchlist_item": watchlist_item,
            "latest_analysis": latest_analysis,
            "ai_extracted_data": ai_data,
            "current_quote": current_quote,
            "price_error": price_error,
            "cache_info": {
                "status": analysis_cache_status,
                "last_updated": latest_analysis.get('analysis_date') if latest_analysis else None,
                "is_today": latest_analysis.get('analysis_date') == date.today().isoformat() if latest_analysis else False,
                "needs_refresh": analysis_cache_status in ["stale", "missing", "refresh_failed_no_cache"]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting watchlist item: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/watchlist/{ticker}")
async def update_watchlist_item(
    ticker: str,
    notes: Optional[str] = None
):
    """Update watchlist item (currently only notes)"""
    try:
        from app.database.db_service import DatabaseService
        db_service = DatabaseService(db_path="stock_analysis.db")
        
        # Handle string "null" from query parameters - convert to None
        if notes is not None and notes.lower() == "null":
            notes = None
        
        success = db_service.update_watchlist_item(
            ticker=ticker.upper(),
            notes=notes
        )
        
        if success:
            return {"success": True, "message": f"{ticker.upper()} updated"}
        else:
            raise HTTPException(status_code=404, detail="Stock not found in watchlist")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating watchlist item: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-assign-business-type/{ticker}")
async def auto_assign_business_type(ticker: str):
    """
    Auto-assign business type using AI-powered detection
    Uses AWS Bedrock or OpenAI to analyze company information and determine the most appropriate valuation model
    """
    try:
        from app.data.data_fetcher import DataFetcher, YahooFinanceClient
        from app.ai.business_type_detector import BusinessTypeDetector
        from app.config.analysis_weights import AnalysisWeightPresets
        
        # Try to fetch company information
        yahoo_client = YahooFinanceClient()
        loop = asyncio.get_event_loop()
        
        quote = None
        try:
            quote = await loop.run_in_executor(None, yahoo_client.get_quote, ticker.upper())
        except Exception as e:
            logger.warning(f"Could not get quote for {ticker}: {e}")
        
        # Prepare company info for AI detection (with fallback for missing data)
        if quote:
            company_info = {
                'company_name': quote.get('company_name', ticker.upper()),
                'sector': quote.get('sector'),
                'industry': quote.get('industry'),
                'description': quote.get('long_business_summary') or quote.get('business_summary', ''),
                'business_summary': quote.get('long_business_summary') or quote.get('business_summary', '')
            }
        else:
            # Fallback: use minimal info when Yahoo Finance is unavailable
            logger.info(f"Yahoo Finance unavailable for {ticker}, using minimal company info")
            company_info = {
                'company_name': ticker.upper(),
                'sector': None,
                'industry': None,
                'description': f"Company with ticker symbol {ticker.upper()}",
                'business_summary': f"Company with ticker symbol {ticker.upper()}"
            }
        
        # Use AI detector with fallback
        detector = BusinessTypeDetector()
        detected_business_type = detector.detect_with_fallback(
            company_info=company_info,
            sector=company_info.get('sector'),
            industry=company_info.get('industry')
        )
        
        # Get weights for the detected type
        weights = AnalysisWeightPresets.get_preset(detected_business_type)
        
        # Determine the source of detection
        data_source = "Yahoo Finance + AI" if quote else "Rule-based (Yahoo Finance unavailable)"
        
        return {
            "success": True,
            "ticker": ticker.upper(),
            "detected_business_type": detected_business_type.value,
            "business_type_display": detected_business_type.value.replace('_', ' ').title(),
            "weights": weights.to_dict(),
            "message": f"Auto-detected business type: {detected_business_type.value.replace('_', ' ').title()}",
            "data_source": data_source,
            "company_info_available": quote is not None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in auto-assign business type for {ticker}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error auto-assigning business type: {str(e)}")
