'use client'

import { useEffect, useState, useRef } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { stockApi, StockAnalysis } from '@/lib/api'
import { formatPrice } from '@/lib/currency'
import AnalysisCard from '@/components/AnalysisCard'
import MarginOfSafety from '@/components/MarginOfSafety'
import ValuationChart from '@/components/ValuationChart'
import FinancialHealth from '@/components/FinancialHealth'
import BusinessQuality from '@/components/BusinessQuality'
import GrowthMetrics from '@/components/GrowthMetrics'
import PriceRatios from '@/components/PriceRatios'
import MissingDataPrompt from '@/components/MissingDataPrompt'
import PDFUpload from '@/components/PDFUpload'
import DataQualityWarnings from '@/components/DataQualityWarnings'
import ExtractedDataViewer from '@/components/ExtractedDataViewer'
import AnalysisWeightsConfig, { AnalysisWeights } from '@/components/AnalysisWeightsConfig'
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
  const abortControllerRef = useRef<AbortController | null>(null)
  const isMountedRef = useRef(true)

  useEffect(() => {
    isMountedRef.current = true
    if (ticker) {
      loadAnalysis()
      loadWatchlistData()
    }
    
    return () => {
      isMountedRef.current = false
      // Abort any ongoing requests when component unmounts
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [ticker])

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
      console.log('Starting analysis for', normalizedTicker, '(original:', ticker, ')')
      const data = await stockApi.analyzeStock(
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
        console.log('Analysis complete:', data)
        setAnalysis(data)
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
        console.error('Analysis error:', err)
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
              <p style={{ fontSize: '20px', color: '#6b7280' }}>
                Current Price: {formatPrice(analysis.currentPrice, analysis.currency)}
                {analysis.currency && analysis.currency !== 'USD' && (
                  <span style={{ fontSize: '14px', marginLeft: '8px', color: '#9ca3af' }}>
                    ({analysis.currency})
                  </span>
                )}
              </p>
            ) : (
              <p style={{ fontSize: '16px', color: '#dc2626', marginTop: '8px' }}>
                ⚠️ Current price unavailable - Price API may be temporarily unavailable or rate limited
              </p>
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

      <AnalysisCard analysis={analysis} />
      <MarginOfSafety analysis={analysis} />
      <ValuationChart analysis={analysis} />
      <PriceRatios priceRatios={analysis.priceRatios} />
      <GrowthMetrics growthMetrics={analysis.growthMetrics} currency={analysis.currency} />
      <FinancialHealth analysis={analysis} />
      <BusinessQuality analysis={analysis} />
    </div>
  )
}

