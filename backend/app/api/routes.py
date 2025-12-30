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
from app.api.models import StockAnalysis, QuoteResponse, CompareRequest, CompareResponse, MissingDataInfo, ManualDataEntry, ManualDataResponse, DataQualityWarning, GrowthMetrics, PriceRatios
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

# Test route to verify router is working
@router.get("/test-batch-route")
async def test_batch_route():
    return {"message": "Batch route test - router is working"}

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
            
            # Debug logging
            logger.info(f"Analysis complete for {ticker}. Error: {analysis_error}, Result: {analysis_result is not None}")
            
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
        llama_api_url = os.getenv("LLAMA_API_URL", "http://localhost:11434")
        logger.info(f"Using Llama-only mode for PDF extraction (Ollama URL: {llama_api_url})")
        
        # Use LLM to extract financial data
        extraction_error = None
        extraction_error_type = None
        updated_periods = 0  # Initialize early to avoid reference errors
        extraction_details = {
            "pdf_text_length": len(pdf_text),
            "llm_provider": "llama",  # Llama-only mode
            "has_api_key": True,  # Llama is always available if Ollama is running
            "extraction_method": None,
            "error_type": None,
            "error_message": None,
            "llama_api_url": extractor.llama_api_url,
            "llama_model": extractor.llama_model
        }
        
        raw_llm_response = None
        try:
            logger.info(f"Starting LLM extraction for {ticker_upper} using Llama-only mode")
            # Use per-page processing for better results on large PDFs (concurrent processing)
            extracted_data, raw_llm_response = await extractor.extract_financial_data_per_page(pdf_bytes, ticker_upper)
            logger.info(f"LLM extraction completed successfully for {ticker_upper} (concurrent per-page processing)")
            extraction_details["extraction_method"] = "llm_per_page"
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
        
        # Store extracted data in manual_data_store
        if ticker_upper not in manual_data_store:
            manual_data_store[ticker_upper] = {}
        
        updated_periods = 0
        
        # Process income statement data
        if income_statement and isinstance(income_statement, dict):
            for period, data in income_statement.items():
                entry_key = f"income_statement_{period}"
                manual_data_store[ticker_upper][entry_key] = {
                    'ticker': ticker_upper,
                    'data_type': 'income_statement',
                    'period': period,
                    'data': data
                }
                updated_periods += 1
        
        # Process balance sheet data
        if balance_sheet and isinstance(balance_sheet, dict):
            for period, data in balance_sheet.items():
                entry_key = f"balance_sheet_{period}"
                manual_data_store[ticker_upper][entry_key] = {
                    'ticker': ticker_upper,
                    'data_type': 'balance_sheet',
                    'period': period,
                    'data': data
                }
                updated_periods += 1
        
        # Process cash flow data
        if cashflow and isinstance(cashflow, dict):
            for period, data in cashflow.items():
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
                    # Llama-only mode: All extractions use Llama
                    llama_url = extraction_details.get("llama_api_url", "http://localhost:11434")
                    llama_model = extraction_details.get("llama_model", "llava:7b")
                    diagnostic_parts.append(f"RECOMMENDATION: PDF contains financial data but Llama extraction failed. Ensure Ollama is running at {llama_url} and model {llama_model} is available. Try: (1) Ensure PDF has complete financial statements with clear labels, (2) Check if PDF is a scanned/image-based document (OCR may be needed), (3) Verify the document format matches standard 10-K/annual report structure, (4) Verify Ollama is running: 'ollama serve' and model is available: 'ollama pull {llama_model}'")
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
            message = f"PDF processed successfully! Extracted {updated_periods} data period(s) for {ticker_upper}.\n\nDiagnostics:\n{error_message}"
        else:
            message = f"PDF processed successfully! Extracted {updated_periods} data period(s) for {ticker_upper}. The analysis will be updated automatically."
        
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
