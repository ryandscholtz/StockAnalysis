from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ValuationBreakdown(BaseModel):
    dcf: float
    earningsPower: float
    assetBased: float
    weightedAverage: float


class FinancialMetrics(BaseModel):
    debtToEquity: float
    currentRatio: float
    quickRatio: float
    interestCoverage: float
    roe: float
    roic: float
    roa: float
    fcfMargin: float


class GrowthMetrics(BaseModel):
    """Growth rates for key financial metrics"""
    revenueGrowth1Y: Optional[float] = None  # 1-year revenue growth
    revenueGrowth3Y: Optional[float] = None  # 3-year CAGR
    revenueGrowth5Y: Optional[float] = None  # 5-year CAGR
    earningsGrowth1Y: Optional[float] = None  # 1-year earnings growth
    earningsGrowth3Y: Optional[float] = None  # 3-year CAGR
    earningsGrowth5Y: Optional[float] = None  # 5-year CAGR
    fcfGrowth1Y: Optional[float] = None  # 1-year FCF growth
    fcfGrowth3Y: Optional[float] = None  # 3-year CAGR
    fcfGrowth5Y: Optional[float] = None  # 5-year CAGR


class PriceRatios(BaseModel):
    """Price-to-X valuation ratios"""
    priceToEarnings: Optional[float] = None  # P/E ratio
    priceToBook: Optional[float] = None  # P/B ratio
    priceToSales: Optional[float] = None  # P/S ratio
    priceToFCF: Optional[float] = None  # P/FCF ratio
    enterpriseValueToEBITDA: Optional[float] = None  # EV/EBITDA


class FinancialHealth(BaseModel):
    score: float
    metrics: FinancialMetrics


class BusinessQuality(BaseModel):
    score: float
    moatIndicators: List[str]
    competitivePosition: str


class ManagementQuality(BaseModel):
    score: float
    strengths: List[str]
    weaknesses: List[str]


class MissingDataInfo(BaseModel):
    """Information about missing financial data"""
    income_statement: List[str] = []
    balance_sheet: List[str] = []
    cashflow: List[str] = []
    key_metrics: List[str] = []
    has_missing_data: bool = False


class DataQualityWarning(BaseModel):
    """Data quality warning about assumptions or missing data"""
    category: str  # 'assumption', 'missing_data', 'estimated'
    field: str
    message: str
    severity: str  # 'high', 'medium', 'low'
    assumed_value: Optional[float] = None
    actual_value: Optional[float] = None


class AnalysisWeights(BaseModel):
    """Valuation weights configuration - determines how much each valuation method contributes to the final fair value"""
    # Valuation weights (must sum to 1.0)
    dcf_weight: float = 0.40
    epv_weight: float = 0.40
    asset_weight: float = 0.20


class BankMetrics(BaseModel):
    """Bank-specific metrics"""
    net_interest_margin: float
    return_on_equity: float
    return_on_assets: float
    tier_1_capital_ratio: Optional[float] = None
    loan_loss_provision_ratio: Optional[float] = None
    efficiency_ratio: Optional[float] = None
    loan_to_deposit_ratio: Optional[float] = None
    non_performing_loans_ratio: Optional[float] = None


class REITMetrics(BaseModel):
    """REIT-specific metrics"""
    funds_from_operations: Optional[float] = None
    adjusted_funds_from_operations: Optional[float] = None
    ffo_per_share: Optional[float] = None
    affo_per_share: Optional[float] = None
    net_asset_value: Optional[float] = None
    dividend_yield: Optional[float] = None
    payout_ratio: Optional[float] = None
    occupancy_rate: Optional[float] = None


class InsuranceMetrics(BaseModel):
    """Insurance-specific metrics"""
    combined_ratio: Optional[float] = None
    loss_ratio: Optional[float] = None
    expense_ratio: Optional[float] = None
    return_on_equity: float
    return_on_assets: float
    reserve_adequacy: Optional[float] = None
    investment_yield: Optional[float] = None


class StockAnalysis(BaseModel):
    ticker: str
    companyName: str
    currentPrice: float
    fairValue: float
    marginOfSafety: float
    upsidePotential: float
    priceToIntrinsicValue: float
    recommendation: str  # 'Strong Buy' | 'Buy' | 'Hold' | 'Avoid'
    recommendationReasoning: str
    valuation: ValuationBreakdown
    financialHealth: FinancialHealth
    businessQuality: BusinessQuality
    managementQuality: Optional[ManagementQuality] = None
    growthMetrics: Optional[GrowthMetrics] = None
    priceRatios: Optional[PriceRatios] = None
    currency: Optional[str] = None  # Trading currency
    financialCurrency: Optional[str] = None  # Financial statement currency
    timestamp: datetime
    missingData: Optional[MissingDataInfo] = None  # Information about missing data
    dataQualityWarnings: Optional[List[DataQualityWarning]] = None  # Warnings about assumptions
    businessType: Optional[str] = None  # Detected or user-selected business type
    analysisWeights: Optional[AnalysisWeights] = None  # Weights used for this analysis
    bankMetrics: Optional[BankMetrics] = None  # Bank-specific metrics (if applicable)
    reitMetrics: Optional[REITMetrics] = None  # REIT-specific metrics (if applicable)
    insuranceMetrics: Optional[InsuranceMetrics] = None  # Insurance-specific metrics (if applicable)


class QuoteResponse(BaseModel):
    ticker: str
    companyName: str
    currentPrice: float
    marketCap: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    currency: Optional[str] = None


class CompareRequest(BaseModel):
    tickers: List[str]


class CompareResponse(BaseModel):
    analyses: List[StockAnalysis]


class SearchResult(BaseModel):
    ticker: str
    companyName: str
    exchange: str


class SearchResponse(BaseModel):
    results: List[SearchResult]


class ManualDataEntry(BaseModel):
    """Manual data entry for missing financial information"""
    ticker: str
    data_type: str  # 'income_statement', 'balance_sheet', 'cashflow'
    period: str  # Date/period identifier (e.g., '2024-12-31')
    data: Dict[str, float]  # Key-value pairs of financial metrics


class ManualDataResponse(BaseModel):
    """Response after manual data entry"""
    success: bool
    message: str
    updated_periods: int
    extracted_data: Optional[dict] = None  # Include extracted data for UI display
    extraction_details: Optional[dict] = None  # Detailed information about extraction


class PDFJobResponse(BaseModel):
    """Response when PDF upload is accepted for processing"""
    success: bool
    job_id: int
    message: str
    ticker: str
    filename: Optional[str] = None
    total_pages: int = 0


class PDFJobStatusResponse(BaseModel):
    """Response for PDF job status polling"""
    job_id: int
    ticker: str
    status: str  # running, completed, failed, cancelled
    total_pages: int
    pages_processed: int
    current_page: int
    current_task: Optional[str] = None
    progress_pct: float
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[dict] = None  # Final result when completed
    extraction_details: Optional[dict] = None  # Detailed extraction info


class AnalysisWeightsRequest(BaseModel):
    """Request to set analysis weights"""
    business_type: Optional[str] = None  # Use preset for this business type
    weights: Optional[AnalysisWeights] = None  # Manual weights (overrides preset)