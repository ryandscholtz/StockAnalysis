'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { stockApi, WatchlistItemDetail } from '@/lib/api'
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

export default function TickerPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [ticker, setTicker] = useState<string>('')
  
  const [watchlistData, setWatchlistData] = useState<WatchlistItemDetail | null>(null)
  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState<string>('')
  const [progress, setProgress] = useState<{ step: number; total: number; task: string } | null>(null)
  const [analysisWeights, setAnalysisWeights] = useState<AnalysisWeights | null>(null)
  const [businessType, setBusinessType] = useState<string | null>(null)
  const [showWeightsConfig, setShowWeightsConfig] = useState(false)
  const [showModelDropdown, setShowModelDropdown] = useState(false)
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [modelPresets, setModelPresets] = useState<any>({})
  const [financialData, setFinancialData] = useState<any>({
    ticker: '',
    financial_data: {},
    has_data: false
  })
  const [showManualEntry, setShowManualEntry] = useState(false)
  const [showPDFUpload, setShowPDFUpload] = useState(false)

  // Get ticker from URL parameters or hash
  useEffect(() => {
    const tickerParam = searchParams.get('symbol') || searchParams.get('ticker')
    if (tickerParam) {
      setTicker(tickerParam.toUpperCase())
    } else if (typeof window !== 'undefined') {
      // Check hash for ticker
      const hash = window.location.hash.replace('#', '')
      if (hash) {
        setTicker(hash.toUpperCase())
      }
    }
  }, [searchParams])

  useEffect(() => {
    if (ticker) {
      loadWatchlistData()
      loadFinancialData()
      fetchAvailableModels()
    }
  }, [ticker])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showModelDropdown) {
        const target = event.target as HTMLElement
        if (!target.closest('[data-model-dropdown]')) {
          setShowModelDropdown(false)
        }
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showModelDropdown])

  const fetchAvailableModels = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/analysis-presets`)
      
      if (response.ok) {
        const data = await response.json()
        if (data && data.presets && data.business_types) {
          setAvailableModels(data.business_types)
          setModelPresets(data.presets)
        }
      }
    } catch (error) {
      console.error('Error fetching models:', error)
      // Fallback models
      setAvailableModels(['default', 'growth_company', 'mature_company', 'asset_heavy', 'distressed_company'])
    }
  }

  const handleModelChange = async (newModel: string) => {
    setBusinessType(newModel)
    setShowModelDropdown(false)
    
    // Update analysis weights based on the selected model
    if (modelPresets[newModel]) {
      setAnalysisWeights(modelPresets[newModel])
    }
    
    // Re-run analysis with new model
    await loadAnalysis(true)
  }

  const getModelDisplayName = (modelKey: string) => {
    return modelKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const normalizeTicker = (t: string): string => {
    // Only strip exchange prefix like "NYSE: AAPL" -> "AAPL"
    // Keep dots as-is (e.g. PPE.XJSE, BP.L, AAPL.TO)
    return t.replace(/^[A-Z]+:\s*/i, '').toUpperCase()
  }

  const loadFinancialData = async () => {
    console.log('🔄 loadFinancialData called for ticker:', ticker);
    try {
      const normalizedTicker = normalizeTicker(ticker)
      console.log('📡 Attempting to load financial data for:', normalizedTicker);
      const result = await stockApi.getFinancialData(normalizedTicker)
      console.log('✅ Financial data loaded successfully:', result);
      setFinancialData(result)
    } catch (err: any) {
      // Silently fail - financial data is optional for display
      console.debug('Could not load financial data:', err)
      console.log('🔄 Setting fallback financial data structure');
      // Set empty financial data so components still render
      setFinancialData({
        ticker: normalizeTicker(ticker),
        financial_data: {},
        metadata: {},
        has_data: false
      })
    }
  }

  const loadWatchlistData = async (forceRefresh: boolean = false) => {
    try {
      const result = await stockApi.getWatchlistItem(ticker, forceRefresh)
      setWatchlistData(result)
      
      // If we got fresh analysis data, update the analysis state
      if (result?.latest_analysis && !analyzing) {
        setAnalysis(result.latest_analysis)
        if (result.latest_analysis.analysisWeights) {
          setAnalysisWeights(result.latest_analysis.analysisWeights)
        }
        if (result.latest_analysis.businessType) {
          setBusinessType(result.latest_analysis.businessType)
        }
      }
      
      // Set loading to false after successfully loading data
      setLoading(false)
    } catch (err: any) {
      console.error('Error loading watchlist data:', err)
      // Set loading to false even on error
      setLoading(false)
      // Set error state if needed
      if (err?.code === 'ERR_NETWORK' || err?.code === 'ECONNREFUSED' || err?.message?.includes('Cannot connect')) {
        setError(err?.message || 'Cannot connect to backend server')
      }
    }
  }

  const loadAnalysis = async (forceRefresh: boolean = false) => {
    try {
      setLoading(true)
      setError('')
      setProgress(null)
      
      // Try to get existing analysis first
      const normalizedTicker = normalizeTicker(ticker)
      const data = await stockApi.analyzeStock(
        normalizedTicker, 
        (update) => {
          if (update.type === 'progress') {
            setProgress({
              step: update.step || 0,
              total: update.total || 8,
              task: update.task || ''
            })
          }
        }, 
        undefined, 
        forceRefresh,
        businessType,
        analysisWeights
      )
      setAnalysis(data)
      // Update weights and business type from response
      if (data.analysisWeights) {
        setAnalysisWeights(data.analysisWeights)
      }
      if (data.businessType) {
        setBusinessType(data.businessType)
      }
      
      // Update watchlist and stored financial data with latest analysis
      await Promise.all([loadWatchlistData(), loadFinancialData()])
    } catch (err: any) {
      console.error('Analysis error:', err)
      // Use formatted error message (from api.ts interceptor)
      setError(err?.message || 'Failed to load analysis')
    } finally {
      setLoading(false)
      setAnalyzing(false)
      setProgress(null)
    }
  }

  const handleRunAnalysis = async () => {
    setAnalyzing(true)
    setError('')
    await loadAnalysis(true)
  }

  const handleRemoveFromWatchlist = async () => {
    if (!confirm(`Remove ${ticker} from watchlist?`)) {
      return
    }

    try {
      await stockApi.removeFromWatchlist(ticker)
      router.push('/watchlist')
    } catch (err: any) {
      // Use formatted error message (from api.ts interceptor)
      alert(err?.message || 'Failed to remove from watchlist')
      console.error('Error removing from watchlist:', err)
    }
  }

  const getRecommendationColor = (recommendation?: string) => {
    switch (recommendation) {
      case 'Strong Buy':
        return '#10b981'
      case 'Buy':
        return '#3b82f6'
      case 'Hold':
        return '#f59e0b'
      case 'Avoid':
        return '#ef4444'
      default:
        return '#6b7280'
    }
  }

  if (!ticker) {
    return (
      <div className="container" style={{ padding: '40px 20px' }}>
        <div style={{
          padding: '20px',
          backgroundColor: '#fef3c7',
          border: '1px solid #f59e0b',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h2 style={{ fontSize: '18px', fontWeight: '600', color: '#92400e', marginBottom: '12px' }}>
            No Ticker Specified
          </h2>
          <p style={{ color: '#92400e', marginBottom: '16px' }}>
            Please provide a ticker symbol using ?ticker=SYMBOL or #SYMBOL in the URL.
          </p>
          <button
            onClick={() => router.push('/watchlist')}
            style={{
              padding: '10px 20px',
              backgroundColor: '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            Go to Watchlist
          </button>
        </div>
      </div>
    )
  }

  if (loading || analyzing) {
    return (
      <div className="container" style={{ padding: '40px 20px' }}>
        <div style={{ marginBottom: '20px' }}>
          <button
            onClick={() => router.push('/watchlist')}
            style={{
              padding: '8px 16px',
              backgroundColor: '#f3f4f6',
              color: '#374151',
              border: 'none',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer',
              marginBottom: '16px'
            }}
          >
            ← Back to Watchlist
          </button>
          <h1 style={{ fontSize: '32px', fontWeight: '700', color: '#111827', margin: 0 }}>
            {ticker}
          </h1>
        </div>

        <div style={{ 
          maxWidth: '600px', 
          margin: '40px auto',
          background: 'white',
          padding: '24px',
          borderRadius: '8px',
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)'
        }}>
          <h2 style={{ fontSize: '24px', marginBottom: '20px', textAlign: 'center' }}>
            {analyzing ? 'Analyzing...' : 'Loading...'}
          </h2>
          
          {progress && (
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
          )}
          
          <p style={{ 
            fontSize: '16px', 
            color: '#111827',
            fontWeight: '500',
            margin: 0,
            textAlign: 'center'
          }}>
            {progress?.task || 'Initializing...'}
          </p>
        </div>
      </div>
    )
  }

  if (error && !analysis && !watchlistData) {
    return (
      <div className="container" style={{ padding: '40px 20px' }}>
        <div style={{
          padding: '12px 16px',
          backgroundColor: '#fee2e2',
          border: '1px solid #ef4444',
          borderRadius: '6px',
          color: '#991b1b',
          marginBottom: '20px'
        }}>
          ❌ {error}
        </div>
        <button
          onClick={() => router.push('/watchlist')}
          style={{
            padding: '10px 20px',
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: '500',
            cursor: 'pointer'
          }}
        >
          Back to Watchlist
        </button>
      </div>
    )
  }

  // Prefer analysis company name (from MarketStack API) over stored watchlist name
  const companyName = analysis?.companyName || watchlistData?.watchlist_item?.company_name || ticker
  const rawPrice = analysis?.currentPrice || watchlistData?.current_quote?.currentPrice || watchlistData?.watchlist_item?.current_price
  // Hide price if it's exactly 1.0 (placeholder value when price cannot be fetched)
  const currentPrice = (rawPrice && Math.abs(rawPrice - 1.0) > 0.01) ? rawPrice : null
  const priceError = watchlistData?.price_error || null
  const recommendation = analysis?.recommendation || watchlistData?.watchlist_item?.recommendation

  return (
    <div className="container" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <button
          onClick={() => router.push('/watchlist')}
          style={{
            padding: '8px 16px',
            backgroundColor: '#f3f4f6',
            color: '#374151',
            border: 'none',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: '500',
            cursor: 'pointer',
            marginBottom: '16px'
          }}
        >
          ← Back to Watchlist
        </button>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
          <div>
            <div style={{ marginBottom: '8px' }}>
              <h1 style={{ fontSize: '36px', fontWeight: '700', color: '#111827', margin: 0 }}>
                {companyName} ({ticker})
              </h1>
            </div>
            {currentPrice ? (
              <div>
                <p style={{ fontSize: '20px', color: '#6b7280', margin: 0 }}>
                  Current Price: {formatPrice(currentPrice, analysis?.currency)}
                  {analysis?.currency && analysis.currency !== 'USD' && (
                    <span style={{ fontSize: '14px', marginLeft: '8px', color: '#9ca3af' }}>
                      ({analysis.currency})
                    </span>
                  )}
                </p>
                {/* Cache Status Indicator - moved below price */}
                {watchlistData?.cache_info && (
                  <div style={{
                    padding: '6px 10px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: '500',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    marginTop: '6px',
                    backgroundColor: watchlistData.cache_info.status === 'fresh' ? '#dcfce7' : 
                                    watchlistData.cache_info.status === 'stale' ? '#fef3c7' : '#fee2e2',
                    color: watchlistData.cache_info.status === 'fresh' ? '#166534' : 
                           watchlistData.cache_info.status === 'stale' ? '#92400e' : '#991b1b'
                  }}>
                    {watchlistData.cache_info.status === 'fresh' && '✅ Fresh'}
                    {watchlistData.cache_info.status === 'stale' && '⏰ Stale'}
                    {watchlistData.cache_info.status === 'missing' && '❌ No Data'}
                    {watchlistData.cache_info.status === 'refreshed' && '🔄 Refreshed'}
                    {watchlistData.cache_info.last_updated && (
                      <span style={{ fontSize: '10px', opacity: 0.8 }}>
                        ({watchlistData.cache_info.last_updated})
                      </span>
                    )}
                  </div>
                )}
                {/* Recommendation Badge - moved below price */}
                {recommendation && (
                  <div style={{ marginTop: '8px' }}>
                    <span style={{
                      padding: '6px 16px',
                      borderRadius: '16px',
                      fontSize: '14px',
                      fontWeight: '600',
                      color: 'white',
                      backgroundColor: getRecommendationColor(recommendation)
                    }}>
                      {recommendation}
                    </span>
                  </div>
                )}
              </div>
            ) : priceError ? (
              <p style={{ fontSize: '16px', color: '#dc2626', margin: 0, marginTop: '8px' }}>
                ⚠️ {priceError}
              </p>
            ) : null}
          </div>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <button
              onClick={handleRunAnalysis}
              disabled={analyzing}
              style={{
                padding: '10px 20px',
                backgroundColor: '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: analyzing ? 'not-allowed' : 'pointer',
                opacity: analyzing ? 0.5 : 1
              }}
            >
              {analyzing ? 'Analyzing...' : 'Run Analysis'}
            </button>
            <button
              onClick={() => { setShowManualEntry(v => !v); setShowPDFUpload(false) }}
              style={{
                padding: '10px 20px',
                backgroundColor: showManualEntry ? '#f59e0b' : '#6b7280',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer'
              }}
            >
              📋 {showManualEntry ? 'Hide Manual Entry' : 'Enter Data'}
            </button>
            <button
              onClick={() => { setShowPDFUpload(v => !v); setShowManualEntry(false) }}
              style={{
                padding: '10px 20px',
                backgroundColor: showPDFUpload ? '#7c3aed' : '#6b7280',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer'
              }}
            >
              📄 {showPDFUpload ? 'Hide PDF Upload' : 'Upload PDF'}
            </button>
            <button
              onClick={handleRemoveFromWatchlist}
              style={{
                padding: '10px 20px',
                backgroundColor: '#fee2e2',
                color: '#991b1b',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer'
              }}
            >
              Remove from Watchlist
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '12px 16px',
          backgroundColor: '#fee2e2',
          border: '1px solid #ef4444',
          borderRadius: '6px',
          color: '#991b1b',
          marginBottom: '20px'
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Manual Data Entry Panel */}
      {showManualEntry && (
        <ManualDataEntry
          ticker={ticker}
          onDataAdded={() => {
            setShowManualEntry(false)
            loadFinancialData()
            loadAnalysis(true)
          }}
        />
      )}

      {/* PDF Upload Panel */}
      {showPDFUpload && (
        <PDFUpload
          ticker={ticker}
          onDataExtracted={() => {
            setShowPDFUpload(false)
            loadFinancialData()
            loadAnalysis(true)
          }}
        />
      )}

      {/* Stored financial data — always shown when data exists */}
      <FinancialDataDisplay
        ticker={ticker}
        financialData={financialData.financial_data || {}}
        metadata={financialData.metadata || {}}
      />

      {analysis ? (
        <>
          {/* Data Quality Warnings */}
          <DataQualityWarnings warnings={analysis.dataQualityWarnings} />
          
          {/* Show missing data prompt if needed */}
          {(analysis.fairValue === 0 || (analysis.missingData?.has_missing_data)) && (
            <MissingDataPrompt
              ticker={ticker}
              missingData={analysis.missingData || {
                income_statement: [],
                balance_sheet: [],
                cashflow: [],
                  key_metrics: [],
                  has_missing_data: true
                }}
                onDataAdded={() => {
                  // Force refresh to get new analysis with updated data
                  loadAnalysis(true)
                  loadWatchlistData()
                }}
              />
          )}

          {/* Analysis Components */}
          <AnalysisCard analysis={analysis} />
          <ValuationStatus analysis={analysis} />
          <ValuationChart analysis={analysis} />
          <PriceRatios priceRatios={analysis.priceRatios} />
          <GrowthMetrics growthMetrics={analysis.growthMetrics} currency={analysis.currency} />
          <FinancialHealth analysis={analysis} />
          <BusinessQuality analysis={analysis} />
        </>
      ) : (
        <>
          {/* No analysis yet - show PDF upload and prompt to run analysis */}
          <div style={{
            padding: '20px',
            backgroundColor: '#eff6ff',
            border: '1px solid #3b82f6',
            borderRadius: '8px',
            marginBottom: '32px'
          }}>
            <h2 style={{ fontSize: '18px', fontWeight: '600', color: '#1e40af', marginBottom: '12px' }}>
              No Analysis Available
            </h2>
            <p style={{ color: '#1e3a8a', marginBottom: '16px' }}>
              Run an analysis to see detailed valuation, financial health, and business quality metrics.
            </p>
            <button
              onClick={handleRunAnalysis}
              style={{
                padding: '10px 20px',
                backgroundColor: '#2563eb',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer'
              }}
            >
              Run Analysis
            </button>
          </div>
        </>
      )}
    </div>
  )
}