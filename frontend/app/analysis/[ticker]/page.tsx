'use client'

import { useEffect, useState, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { stockApi } from '@/lib/api'
import { StockAnalysis } from '@/types/analysis'
import { formatPrice } from '@/lib/currency'
import AnalysisCard from '@/components/AnalysisCard'
import ValuationStatus from '@/components/ValuationStatus'
import ValuationChart from '@/components/ValuationChart'
import FinancialHealth from '@/components/FinancialHealth'
import BusinessQuality from '@/components/BusinessQuality'
import GrowthMetrics from '@/components/GrowthMetrics'
import PriceRatios from '@/components/PriceRatios'
import MissingDataPrompt from '@/components/MissingDataPrompt'
import PDFUpload from '@/components/PDFUpload'
import DataQualityWarnings from '@/components/DataQualityWarnings'
import ExtractedDataViewer from '@/components/ExtractedDataViewer'
import AnalysisWeightsConfig from '@/components/AnalysisWeightsConfig'
import FinancialDataDisplay from '@/components/FinancialDataDisplay'
import ManualDataEntry from '@/components/ManualDataEntry'
import { AnalysisWeights } from '@/types/analysis'
import { WatchlistItemDetail } from '@/lib/api'

export default function AnalysisPage() {
  const params = useParams()
  const router = useRouter()
  const ticker = params.ticker as string

  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState<{ step: number; total: number; task: string } | null>(null)
  const [watchlistData, setWatchlistData] = useState<WatchlistItemDetail | null>(null)
  const [analysisWeights, setAnalysisWeights] = useState<AnalysisWeights | null>(null)
  const [businessType, setBusinessType] = useState<string | null>(null)
  const [showWeightsConfig, setShowWeightsConfig] = useState(false)
  const [financialData, setFinancialData] = useState<any>({
    ticker: '',
    financial_data: {},
    has_data: false
  })
  const [showManualEntry, setShowManualEntry] = useState(false)
  const [showPDFUpload, setShowPDFUpload] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)
  const isMountedRef = useRef(true)

  useEffect(() => {
    isMountedRef.current = true
    if (ticker) {
      loadAnalysis()
      loadWatchlistData()
      loadFinancialData()
    }
    
    return () => {
      isMountedRef.current = false
      // Abort any ongoing requests when component unmounts
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [ticker])

  const loadFinancialData = async () => {
    console.log('🔄 loadFinancialData called for ticker:', ticker);
    try {
      const normalizedTicker = normalizeTicker(ticker)
      console.log('📡 Attempting to load financial data for:', normalizedTicker);
      const result = await stockApi.getFinancialData(normalizedTicker)
      console.log('✅ Financial data loaded successfully:', result);
      if (isMountedRef.current) {
        setFinancialData(result)
      }
    } catch (err: any) {
      // Silently fail - financial data is optional for display
      console.debug('Could not load financial data:', err)
      console.log('🔄 Setting fallback financial data structure');
      // Set empty financial data so components still render
      if (isMountedRef.current) {
        setFinancialData({ 
          ticker: normalizeTicker(ticker), 
          financial_data: {}, 
          has_data: false 
        })
      }
    }
  }

  const loadWatchlistData = async () => {
    try {
      const normalizedTicker = normalizeTicker(ticker)
      const result = await stockApi.getWatchlistItem(normalizedTicker)
      if (isMountedRef.current) {
        setWatchlistData(result)
      }
    } catch (err: any) {
      // Silently fail - watchlist data is optional
      console.debug('Could not load watchlist data:', err)
    }
  }

  // Normalize ticker: remove exchange prefix (e.g., "NYSE: BRK.B" -> "BRK-B")
  // Preserve international exchange suffixes (e.g., "MRF.JO" -> "MRF.JO")
  const normalizeTicker = (t: string): string => {
    // Remove exchange prefix (NYSE:, NASDAQ:, etc.)
    let normalized = t.replace(/^[A-Z]+:\s*/i, '')
    
    // Common international exchange suffixes to preserve
    const exchangeSuffixes = ['.JO', '.L', '.TO', '.PA', '.DE', '.HK', '.SS', '.SZ', '.T', '.AS', '.BR', '.MX', '.SA', '.SW', '.VI', '.ST', '.OL', '.CO', '.HE', '.IC', '.LS', '.MC', '.MI', '.NX', '.TA', '.TW', '.V', '.WA']
    
    // Check if ticker ends with an exchange suffix
    const hasExchangeSuffix = exchangeSuffixes.some(suffix => normalized.toUpperCase().endsWith(suffix))
    
    if (hasExchangeSuffix) {
      // Preserve the dot before the exchange suffix
      // Only replace dots that are NOT part of an exchange suffix
      const parts = normalized.split('.')
      if (parts.length > 1) {
        const lastPart = parts[parts.length - 1]
        // If last part looks like an exchange code (2-3 letters), preserve it
        if (lastPart.length <= 3 && /^[A-Z]{2,3}$/i.test(lastPart)) {
          // Keep the last dot, replace others with hyphens
          const mainPart = parts.slice(0, -1).join('-')
          normalized = `${mainPart}.${lastPart}`
        } else {
          // Not an exchange suffix, replace all dots
          normalized = normalized.replace(/\./g, '-')
        }
      }
    } else {
      // No exchange suffix, replace dots with hyphens for yfinance compatibility (BRK.B -> BRK-B)
      normalized = normalized.replace(/\./g, '-')
    }
    
    return normalized.toUpperCase()
  }

  const loadAnalysis = async (forceRefresh: boolean = false) => {
    console.log(`🔄 loadAnalysis called with forceRefresh=${forceRefresh}`);
    
    // Abort any previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    
    // Create new abort controller for this request
    const controller = new AbortController()
    abortControllerRef.current = controller
    
    setLoading(true)
    setError(null)
    setProgress(null)
    
    try {
      const normalizedTicker = normalizeTicker(ticker)
      console.log('🎯 Starting analysis for', normalizedTicker, '(original:', ticker, ')')
      console.log('📊 forceRefresh:', forceRefresh, 'businessType:', businessType, 'analysisWeights:', analysisWeights);
      
      // For force refresh, use simple endpoint without progress to ensure compatibility
      // with our Lambda handler that doesn't support streaming
      const data = forceRefresh 
        ? await stockApi.analyzeStock(
            normalizedTicker, 
            undefined, // No progress callback for refresh to use simple endpoint
            controller.signal, 
            forceRefresh,
            businessType,
            analysisWeights
          )
        : await stockApi.analyzeStock(
            normalizedTicker, 
            (update) => {
              // Only update if component is still mounted and request not aborted
              if (isMountedRef.current && !controller.signal.aborted) {
                console.log('Progress callback received:', update)
                if (update.type === 'progress') {
                  setProgress({
                    step: update.step || 0,
                    total: update.total || 8,
                    task: update.task || ''
                  })
                }
              }
            }, 
            controller.signal, 
            forceRefresh,
            businessType,
            analysisWeights
          )
      
      // Only update state if component is still mounted and request not aborted
      if (isMountedRef.current && !controller.signal.aborted) {
        console.log('✅ Analysis complete - NEW DATA:', data)
        console.log('💰 New current price:', data.currentPrice)
        console.log('🎯 New fair value:', data.fairValue)
        console.log('📊 Data source:', data.dataSource)
        
        console.log('🔄 Updating analysis state...')
        setAnalysis(data)
        console.log('✅ Analysis state updated!')
        
        // Update weights and business type from response
        if (data.analysisWeights) {
          setAnalysisWeights(data.analysisWeights)
        }
        if (data.businessType) {
          setBusinessType(data.businessType)
        }
      }
    } catch (err: any) {
      // Ignore abort errors (expected when component unmounts or new request starts)
      if (err.name === 'AbortError' || controller.signal.aborted) {
        console.log('Analysis request was aborted (expected)')
        return
      }
      
      // Only show error if component is still mounted
      if (isMountedRef.current) {
        console.error('❌ Analysis error:', err)
        // Use formatted error message (from api.ts interceptor)
        setError(err.message || 'Failed to load analysis')
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false)
        setProgress(null)
      }
    }
  }

  if (loading) {
    return (
      <div className="container">
        <div className="loading">
          <h2 style={{ fontSize: '24px', marginBottom: '20px' }}>Analyzing {ticker}...</h2>
          
          {progress && (
            <div style={{ 
              maxWidth: '600px', 
              margin: '0 auto',
              background: 'white',
              padding: '24px',
              borderRadius: '8px',
              boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)'
            }}>
              <div style={{ marginBottom: '16px' }}>
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  marginBottom: '8px',
                  fontSize: '14px',
                  color: '#6b7280'
                }}>
                  <span>Step {progress.step} of {progress.total || 8}</span>
                  <span>{Math.round((progress.step / (progress.total || 8)) * 100)}%</span>
                </div>
                <div style={{
                  width: '100%',
                  height: '8px',
                  background: '#e5e7eb',
                  borderRadius: '4px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${(progress.step / (progress.total || 8)) * 100}%`,
                    height: '100%',
                    background: '#2563eb',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>
              
              <p style={{ 
                fontSize: '16px', 
                color: '#111827',
                fontWeight: '500',
                margin: 0
              }}>
                {progress.task}
              </p>
            </div>
          )}
          
          {!progress && (
            <p style={{ marginTop: '8px', fontSize: '14px', color: '#9ca3af' }}>
              Initializing analysis...
            </p>
          )}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container">
        <div className="error">
          <h2>Error</h2>
          <p>{error}</p>
          <button
            className="btn btn-primary"
            onClick={() => router.push('/')}
            style={{ marginTop: '16px' }}
          >
            Back to Search
          </button>
        </div>
      </div>
    )
  }

  if (!analysis) {
    return null
  }

  return (
    <div className="container">
      <div style={{ marginBottom: '20px' }}>
        <button
          onClick={() => router.push('/')}
          style={{
            background: 'none',
            border: 'none',
            color: '#2563eb',
            cursor: 'pointer',
            fontSize: '16px',
            marginBottom: '20px'
          }}
        >
          ← Back to Search
        </button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h1 style={{ fontSize: '36px', marginBottom: '8px' }}>
              {analysis.companyName} ({analysis.ticker})
            </h1>
            {/* Show price if valid, or show message if not available */}
            {analysis.currentPrice && Math.abs(analysis.currentPrice - 1.0) > 0.01 ? (
              <div>
                <p style={{ fontSize: '20px', color: '#6b7280' }}>
                  Current Price: {formatPrice(analysis.currentPrice, analysis.currency)}
                  {analysis.currency && analysis.currency !== 'USD' && (
                    <span style={{ fontSize: '14px', marginLeft: '8px', color: '#9ca3af' }}>
                      ({analysis.currency})
                    </span>
                  )}
                  {analysis.dataSource?.price_source && (
                    <span style={{ fontSize: '12px', marginLeft: '8px', color: '#10b981' }}>
                      (Source: {analysis.dataSource.price_source})
                    </span>
                  )}
                </p>
                {/* Cache status indicator */}
                {(analysis as any).cacheInfo && (
                  <div style={{ marginTop: '8px' }}>
                    {(analysis as any).cacheInfo.cached ? (
                      <div style={{ 
                        display: 'inline-flex', 
                        alignItems: 'center', 
                        gap: '8px',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        background: (analysis as any).cacheInfo.is_stale ? '#fef3c7' : '#f0fdf4',
                        color: (analysis as any).cacheInfo.is_stale ? '#92400e' : '#166534',
                        border: `1px solid ${(analysis as any).cacheInfo.is_stale ? '#fbbf24' : '#86efac'}`
                      }}>
                        <span>
                          {(analysis as any).cacheInfo.is_stale ? '⚠️ Stale Data' : '✅ Cached Data'}
                        </span>
                        <span>
                          (Age: {(analysis as any).cacheInfo.age_minutes} min)
                        </span>
                        {(analysis as any).cacheInfo.fallback_reason && (
                          <span style={{ fontStyle: 'italic' }}>
                            - Using cached data due to API limits
                          </span>
                        )}
                      </div>
                    ) : (
                      <div style={{ 
                        display: 'inline-flex', 
                        alignItems: 'center', 
                        gap: '8px',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        background: '#f0fdf4',
                        color: '#166534',
                        border: '1px solid #86efac'
                      }}>
                        <span>🔄 Fresh Data</span>
                        <span>({(analysis as any).cacheInfo.fetched_at})</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ marginTop: '8px' }}>
                <p style={{ fontSize: '16px', color: '#dc2626', marginBottom: '8px' }}>
                  ⚠️ Current price unavailable
                </p>
                {analysis.dataSource?.error && analysis.dataSource.error.includes('rate limit') ? (
                  <div style={{ 
                    background: '#fff3cd', 
                    border: '1px solid #ffeaa7', 
                    borderRadius: '6px', 
                    padding: '12px',
                    fontSize: '14px',
                    color: '#856404'
                  }}>
                    <p style={{ margin: '0 0 8px 0', fontWeight: '600' }}>
                      📊 MarketStack API Limit Reached
                    </p>
                    <p style={{ margin: '0 0 8px 0' }}>
                      {analysis.dataSource.error.includes('monthly') 
                        ? 'The monthly usage limit (100 requests) has been exceeded.'
                        : 'The API has reached its hourly rate limit.'}
                    </p>
                    <p style={{ margin: '0', fontSize: '12px' }}>
                      💡 {analysis.dataSource.error.includes('monthly')
                        ? 'Upgrade to a paid MarketStack plan or wait until next month for the limit to reset.'
                        : 'Try again in about 1 hour, or upgrade to a paid MarketStack plan for higher limits.'}
                    </p>
                  </div>
                ) : (
                  <p style={{ fontSize: '14px', color: '#6b7280' }}>
                    Price data temporarily unavailable. Please try refreshing in a few minutes.
                  </p>
                )}
              </div>
            )}
            {/* Show current business type and weights info */}
            {analysis.businessType && (
              <p style={{ fontSize: '14px', color: '#6b7280', marginTop: '8px' }}>
                Business Type: <strong>{analysis.businessType.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</strong>
                {analysis.analysisWeights && (
                  <span style={{ marginLeft: '12px' }}>
                    (DCF: {(analysis.analysisWeights.dcf_weight * 100).toFixed(0)}%, 
                    EPV: {(analysis.analysisWeights.epv_weight * 100).toFixed(0)}%, 
                    Asset: {(analysis.analysisWeights.asset_weight * 100).toFixed(0)}%)
                  </span>
                )}
              </p>
            )}
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <button
              onClick={() => setShowWeightsConfig(!showWeightsConfig)}
              style={{
                padding: '10px 20px',
                background: showWeightsConfig ? '#dc2626' : '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '600',
                whiteSpace: 'nowrap',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              {showWeightsConfig 
                ? '✕ Close Config' 
                : (() => {
                    const currentModel = businessType || analysis.businessType;
                    const modelName = currentModel 
                      ? currentModel.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
                      : 'Default';
                    return `⚙️ ${modelName} Model`;
                  })()}
            </button>
            <button
              onClick={() => {
                console.log('🔄 Refresh Data button clicked!');
                console.log('Current analysis state before refresh:', analysis);
                loadAnalysis(true);
              }}
              disabled={loading}
              style={{
                padding: '10px 20px',
                background: loading ? '#9ca3af' : ((analysis as any).cacheInfo?.is_stale ? '#f59e0b' : '#10b981'),
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                fontWeight: '600',
                whiteSpace: 'nowrap',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              {loading 
                ? '🔄 Refreshing...' 
                : (analysis as any).cacheInfo?.is_stale 
                  ? '⚠️ Refresh Stale Data' 
                  : '🔄 Refresh Data'}
            </button>
          </div>
        </div>
      </div>

      {/* Analysis Weights Configuration */}
      {showWeightsConfig && (
        <div style={{ marginBottom: '24px' }}>
          <AnalysisWeightsConfig
            onWeightsChange={(weights, bt) => {
              setAnalysisWeights(weights)
              setBusinessType(bt)
            }}
            initialBusinessType={analysis.businessType || undefined}
            initialWeights={analysis.analysisWeights || undefined}
            ticker={ticker}
          />
          <div style={{ marginTop: '16px', display: 'flex', gap: '12px' }}>
            <button
              onClick={() => {
                setShowWeightsConfig(false)
                loadAnalysis(true) // Re-run analysis with new weights
              }}
              style={{
                padding: '12px 24px',
                background: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '16px',
                fontWeight: '600'
              }}
            >
              Re-analyze with New Weights
            </button>
            <button
              onClick={() => {
                setShowWeightsConfig(false)
                setAnalysisWeights(null)
                setBusinessType(null)
              }}
              style={{
                padding: '12px 24px',
                background: '#6b7280',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '16px',
                fontWeight: '600'
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Show data quality warnings first */}
      <DataQualityWarnings warnings={analysis.dataQualityWarnings} />
      
      {/* Show extracted data if available */}
      {watchlistData?.ai_extracted_data && (
        <ExtractedDataViewer
          data={watchlistData.ai_extracted_data}
          ticker={analysis.ticker}
        />
      )}
      
      {/* Show missing data prompt if fair value is 0 or if data is missing */}
      {(analysis.fairValue === 0 || (analysis.missingData?.has_missing_data)) && (
        <>
          <PDFUpload
            ticker={analysis.ticker}
            onDataExtracted={() => {
              // Reload analysis and watchlist data after PDF data is extracted
              loadAnalysis()
              loadWatchlistData()
            }}
          />
          <MissingDataPrompt
            ticker={analysis.ticker}
            missingData={analysis.missingData || {
              income_statement: [],
              balance_sheet: [],
              cashflow: [],
              key_metrics: [],
              has_missing_data: true
            }}
            onDataAdded={() => {
              // Reload analysis after data is added (force refresh to get new analysis)
              loadAnalysis(true)
            }}
          />
        </>
      )}

      {/* Add Financial Data Section */}
      <div style={{ 
        marginBottom: '24px', 
        border: '1px solid #e5e7eb', 
        borderRadius: '8px', 
        padding: '24px',
        backgroundColor: 'white',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
      }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'flex-start',
          marginBottom: '16px'
        }}>
          <div>
            <h2 style={{ 
              margin: '0 0 8px 0', 
              fontSize: '20px', 
              color: '#111827',
              fontWeight: '600'
            }}>
              📊 Add Financial Data
            </h2>
            <p style={{ 
              margin: '0', 
              fontSize: '14px', 
              color: '#6b7280' 
            }}>
              Add financial statement data to enable fair value calculations
            </p>
          </div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              onClick={() => setShowManualEntry(!showManualEntry)}
              style={{
                padding: '10px 20px',
                backgroundColor: showManualEntry ? '#dc2626' : '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              {showManualEntry ? '✕ Close' : '✏️ Add data manually'}
            </button>
            <button
              onClick={() => setShowPDFUpload(!showPDFUpload)}
              style={{
                padding: '10px 20px',
                backgroundColor: showPDFUpload ? '#dc2626' : '#059669',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              {showPDFUpload ? '✕ Close' : '📄 Upload financial statements'}
            </button>
          </div>
        </div>

        {/* Manual Data Entry */}
        {showManualEntry && (
          <div style={{ 
            padding: '20px', 
            backgroundColor: '#f9fafb', 
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
            marginBottom: '16px'
          }}>
            <ManualDataEntry 
              ticker={analysis.ticker}
              onDataAdded={() => {
                loadFinancialData()
                loadAnalysis(true) // Refresh analysis when data is added
                setShowManualEntry(false) // Close after adding data
              }}
            />
          </div>
        )}

        {/* PDF Upload */}
        {showPDFUpload && (
          <div style={{ 
            padding: '20px', 
            backgroundColor: '#f9fafb', 
            borderRadius: '8px',
            border: '1px solid #e5e7eb',
            marginBottom: '16px'
          }}>
            <PDFUpload
              ticker={analysis.ticker}
              onDataExtracted={() => {
                loadAnalysis()
                loadWatchlistData()
                setShowPDFUpload(false) // Close after uploading
              }}
            />
          </div>
        )}

        {/* Financial Data Display - Always Visible */}
        <div style={{ 
          padding: '20px', 
          backgroundColor: '#f9fafb', 
          borderRadius: '8px',
          border: '1px solid #e5e7eb'
        }}>
          <h3 style={{ 
            margin: '0 0 16px 0', 
            fontSize: '16px', 
            color: '#374151',
            fontWeight: '600'
          }}>
            Current Financial Data
          </h3>
          <FinancialDataDisplay 
            ticker={analysis.ticker}
            financialData={financialData?.financial_data}
            onDataUpdate={() => {
              loadFinancialData()
              loadAnalysis(true) // Refresh analysis when data is updated
            }}
          />
        </div>
      </div>
      
      <AnalysisCard analysis={analysis} />
      <ValuationStatus analysis={analysis} />
      <ValuationChart analysis={analysis} />
      <PriceRatios priceRatios={analysis.priceRatios} />
      <GrowthMetrics growthMetrics={analysis.growthMetrics} currency={analysis.currency} />
      <FinancialHealth analysis={analysis} />
      <BusinessQuality analysis={analysis} />
    </div>
  )
}

