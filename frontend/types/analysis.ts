export interface AnalysisWeights {
  dcf_weight: number
  epv_weight: number
  asset_weight: number
}

export interface MissingDataInfo {
  income_statement: string[]
  balance_sheet: string[]
  cashflow: string[]
  key_metrics: string[]
  has_missing_data: boolean
}

export interface StockAnalysis {
  ticker: string
  companyName: string
  currentPrice: number
  fairValue: number
  marginOfSafety: number
  upsidePotential: number
  priceToIntrinsicValue: number
  recommendation: 'Strong Buy' | 'Buy' | 'Hold' | 'Avoid'
  recommendationReasoning: string
  valuation: ValuationBreakdown
  financialHealth: FinancialHealth
  businessQuality: BusinessQuality
  managementQuality?: ManagementQuality
  growthMetrics?: GrowthMetrics
  priceRatios?: PriceRatios
  currency?: string
  financialCurrency?: string
  timestamp: string
  missingData?: MissingDataInfo
  dataQualityWarnings?: DataQualityWarning[]
  analysisWeights?: AnalysisWeights
  businessType?: string
  dataSource?: {
    price_source: string
    has_real_price: boolean
    api_available: boolean
    error?: string
  }
}

export interface ValuationBreakdown {
  dcf: number
  earningsPower: number
  assetBased: number
  weightedAverage: number
}

export interface FinancialHealth {
  score: number
  metrics: FinancialMetrics
}

export interface FinancialMetrics {
  debtToEquity: number
  currentRatio: number
  quickRatio: number
  interestCoverage: number
  roe: number
  roic: number
  roa: number
  fcfMargin: number
}

export interface BusinessQuality {
  score: number
  moatIndicators: string[]
  competitivePosition: string
}

export interface ManagementQuality {
  score: number
  strengths: string[]
  weaknesses: string[]
}

export interface GrowthMetrics {
  revenueGrowth1Y?: number | null
  revenueGrowth3Y?: number | null
  revenueGrowth5Y?: number | null
  earningsGrowth1Y?: number | null
  earningsGrowth3Y?: number | null
  earningsGrowth5Y?: number | null
  fcfGrowth1Y?: number | null
  fcfGrowth3Y?: number | null
  fcfGrowth5Y?: number | null
}

export interface PriceRatios {
  priceToEarnings?: number | null
  priceToBook?: number | null
  priceToSales?: number | null
  priceToFCF?: number | null
  enterpriseValueToEBITDA?: number | null
}

export interface DataQualityWarning {
  category: string  // 'assumption', 'missing_data', 'estimated'
  field: string
  message: string
  severity: string  // 'high', 'medium', 'low'
  assumed_value?: number | null
  actual_value?: number | null
}

