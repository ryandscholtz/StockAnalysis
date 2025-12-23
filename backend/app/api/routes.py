"""
API routes for stock analysis
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from typing import List, AsyncGenerator
import json
import asyncio
import math
from app.api.models import StockAnalysis, QuoteResponse, CompareRequest, CompareResponse, MissingDataInfo, ManualDataEntry, ManualDataResponse, DataQualityWarning, GrowthMetrics, PriceRatios
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


async def _analyze_stock_with_progress(ticker: str, progress_tracker: ProgressTracker) -> StockAnalysis:
    """Internal function to perform analysis with progress tracking"""
    # Step 1: Fetch company data
    await progress_tracker.update(1, "Fetching company data and financial statements...")
    data_fetcher = DataFetcher()
    company_data = await data_fetcher.fetch_company_data(ticker)
    
    if not company_data:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker} not found")
    
    # Apply manual data if available
    if ticker.upper() in manual_data_store:
        manual_data = manual_data_store[ticker.upper()]
        _apply_manual_data(company_data, manual_data)
    
    # Log data availability for debugging
    print(f"\n=== Data Availability for {ticker} ===")
    print(f"Income statements: {len(company_data.income_statement)} periods")
    print(f"Balance sheets: {len(company_data.balance_sheet)} periods")
    print(f"Cash flow statements: {len(company_data.cashflow)} periods")
    if company_data.income_statement:
        first_period = list(company_data.income_statement.values())[0]
        if isinstance(first_period, dict):
            print(f"Income statement keys (sample): {list(first_period.keys())[:10]}")
    if company_data.cashflow:
        first_period = list(company_data.cashflow.values())[0]
        if isinstance(first_period, dict):
            print(f"Cash flow keys (sample): {list(first_period.keys())[:10]}")
    print("=" * 50)
    
    # Step 2: Get risk-free rate
    await progress_tracker.update(2, "Getting market data (risk-free rate)...")
    await asyncio.sleep(0.1)
    risk_free_rate = data_fetcher.get_risk_free_rate()
    
    # Step 3: Analyze financial health (needed for valuation)
    await progress_tracker.update(3, "Analyzing financial health and ratios...")
    await asyncio.sleep(0.1)
    health_analyzer = FinancialHealthAnalyzer(company_data)
    health_result = health_analyzer.analyze()
    
    # Step 4: Analyze business quality (needed for valuation)
    await progress_tracker.update(4, "Assessing business quality and competitive moats...")
    await asyncio.sleep(0.1)
    quality_analyzer = BusinessQualityAnalyzer(company_data)
    quality_result = quality_analyzer.analyze()
    
    # Step 5: Calculate DCF valuation (with quality scores for better accuracy)
    await progress_tracker.update(5, "Calculating Discounted Cash Flow (DCF) model...")
    await asyncio.sleep(0.1)
    intrinsic_calc = IntrinsicValueCalculator(company_data, risk_free_rate)
    valuation_result = intrinsic_calc.calculate(
        business_quality_score=quality_result.score,
        financial_health_score=health_result.score
    )
    
    # Step 6: Calculate margin of safety
    await progress_tracker.update(6, "Calculating margin of safety and investment recommendation...")
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
    
    # Step 7: Analyze management quality
    await progress_tracker.update(7, "Evaluating management quality...")
    await asyncio.sleep(0.1)
    management_analyzer = ManagementQualityAnalyzer(company_data)
    management_result = management_analyzer.analyze()
    
    # Step 8: Calculate growth metrics and price ratios
    await progress_tracker.update(8, "Calculating growth metrics and valuation ratios...")
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
    
    # Check for missing data
    missing = data_fetcher.data_agent.identify_missing_data(company_data)
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
    quality_analyzer = DataQualityAnalyzer(company_data)
    quality_warnings = quality_analyzer.analyze()
    data_quality_warnings = [DataQualityWarning(**w.__dict__) for w in quality_warnings] if quality_warnings else None
    
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
        managementQuality=management_result,
        growthMetrics=growth_metrics,
        priceRatios=price_ratios,
        currency=company_data.currency,
        financialCurrency=company_data.financial_currency,
        timestamp=datetime.now(),
        missingData=missing_data_info,
        dataQualityWarnings=data_quality_warnings
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


@router.get("/analyze/{ticker}")
async def analyze_stock(ticker: str, stream: bool = Query(False, description="Stream progress updates")):
    """
    Perform comprehensive stock analysis for a given ticker
    Use ?stream=true for progress updates via Server-Sent Events
    """
    # Normalize ticker: convert hyphens back to dots for international exchanges
    # Common exchange suffixes (e.g., MRF-JO -> MRF.JO for Johannesburg)
    exchange_suffixes = ['JO', 'L', 'TO', 'PA', 'DE', 'HK', 'SS', 'SZ', 'T', 'AS', 'BR', 'MX', 'SA', 'SW', 'VI', 'ST', 'OL', 'CO', 'HE', 'IC', 'LS', 'MC', 'MI', 'NX', 'TA', 'TW', 'V', 'WA']
    ticker_upper = ticker.upper()
    for suffix in exchange_suffixes:
        if ticker_upper.endswith(f'-{suffix}'):
            ticker = ticker_upper[:-len(suffix)-1] + '.' + suffix
            break
    if stream:
        # Stream progress via SSE
        async def generate() -> AsyncGenerator[str, None]:
            progress_queue = asyncio.Queue()
            progress_tracker = ProgressTracker(total_steps=8)
            
            async def progress_callback(update: dict):
                await progress_queue.put(update)
            
            progress_tracker.set_callback(progress_callback)
            
            # Send initial progress immediately
            initial_progress = {'type': 'progress', 'step': 0, 'total': 8, 'task': 'Initializing analysis...', 'progress': 0}
            yield f"data: {json.dumps(initial_progress)}\n\n"
            print(f"Sent initial progress: {initial_progress}")  # Debug log
            
            # Start analysis in background
            analysis_task = asyncio.create_task(
                _analyze_stock_with_progress(ticker, progress_tracker)
            )
            
            # Stream progress updates
            analysis_complete = False
            analysis_result = None
            analysis_error = None
            
            # Monitor analysis task
            async def monitor_analysis():
                nonlocal analysis_complete, analysis_result, analysis_error
                try:
                    analysis_result = await analysis_task
                    analysis_complete = True
                except Exception as e:
                    analysis_error = str(e)
                    analysis_complete = True
            
            monitor_task = asyncio.create_task(monitor_analysis())
            
            # Stream progress and wait for completion
            while not analysis_complete:
                try:
                    # Wait for progress update with timeout
                    update = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                    progress_json = json.dumps(update)
                    yield f"data: {progress_json}\n\n"
                except asyncio.TimeoutError:
                    # Check if analysis is complete
                    if analysis_complete:
                        break
                    continue
            
            # Wait for analysis to complete
            await monitor_task
            
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
        progress_tracker = ProgressTracker(total_steps=8)
        analysis = await _analyze_stock_with_progress(ticker, progress_tracker)
        return analysis


@router.post("/manual-data", response_model=ManualDataResponse)
async def add_manual_data(entry: ManualDataEntry):
    """
    Add manual financial data for a ticker
    This data will be used in subsequent analyses
    """
    try:
        ticker_upper = entry.ticker.upper()
        
        # Store manual data
        if ticker_upper not in manual_data_store:
            manual_data_store[ticker_upper] = {}
        
        # Create unique key for this entry
        entry_key = f"{entry.data_type}_{entry.period}"
        manual_data_store[ticker_upper][entry_key] = {
            'ticker': ticker_upper,
            'data_type': entry.data_type,
            'period': entry.period,
            'data': entry.data
        }
        
        # Count updated periods
        updated_periods = len(manual_data_store[ticker_upper])
        
        return ManualDataResponse(
            success=True,
            message=f"Manual data added successfully. {updated_periods} period(s) stored for {ticker_upper}.",
            updated_periods=updated_periods
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-pdf", response_model=ManualDataResponse)
async def upload_pdf(
    ticker: str = Query(..., description="Stock ticker symbol"),
    file: UploadFile = File(..., description="PDF file to upload")
):
    """
    Upload a PDF financial statement and extract data using LLM
    Supports annual reports, 10-K filings, quarterly reports, etc.
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
        
        ticker_upper = ticker.upper()
        
        # Extract text and data from PDF
        extractor = PDFExtractor()
        pdf_text = extractor.extract_text_from_pdf(pdf_bytes)
        
        if not pdf_text or len(pdf_text.strip()) < 100:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF. File may be corrupted or image-based.")
        
        # Use LLM to extract financial data
        extracted_data = extractor.extract_financial_data_with_llm(pdf_text, ticker_upper)
        
        # Store extracted data in manual_data_store
        if ticker_upper not in manual_data_store:
            manual_data_store[ticker_upper] = {}
        
        updated_periods = 0
        
        # Process income statement data
        if 'income_statement' in extracted_data and extracted_data['income_statement']:
            for period, data in extracted_data['income_statement'].items():
                entry_key = f"income_statement_{period}"
                manual_data_store[ticker_upper][entry_key] = {
                    'ticker': ticker_upper,
                    'data_type': 'income_statement',
                    'period': period,
                    'data': data
                }
                updated_periods += 1
        
        # Process balance sheet data
        if 'balance_sheet' in extracted_data and extracted_data['balance_sheet']:
            for period, data in extracted_data['balance_sheet'].items():
                entry_key = f"balance_sheet_{period}"
                manual_data_store[ticker_upper][entry_key] = {
                    'ticker': ticker_upper,
                    'data_type': 'balance_sheet',
                    'period': period,
                    'data': data
                }
                updated_periods += 1
        
        # Process cash flow data
        if 'cashflow' in extracted_data and extracted_data['cashflow']:
            for period, data in extracted_data['cashflow'].items():
                entry_key = f"cashflow_{period}"
                manual_data_store[ticker_upper][entry_key] = {
                    'ticker': ticker_upper,
                    'data_type': 'cashflow',
                    'period': period,
                    'data': data
                }
                updated_periods += 1
        
        # Process key metrics
        if 'key_metrics' in extracted_data and extracted_data['key_metrics']:
            # Store key metrics with a special period
            entry_key = "key_metrics_latest"
            manual_data_store[ticker_upper][entry_key] = {
                'ticker': ticker_upper,
                'data_type': 'key_metrics',
                'period': 'latest',
                'data': extracted_data['key_metrics']
            }
            updated_periods += 1
        
        return ManualDataResponse(
            success=True,
            message=f"PDF processed successfully! Extracted {updated_periods} data period(s) for {ticker_upper}. The analysis will be updated automatically.",
            updated_periods=updated_periods
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


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
