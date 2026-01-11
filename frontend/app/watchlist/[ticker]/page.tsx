'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
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

export default function WatchlistDetailPage() {
  const params = useParams()
  const router = useRouter()
  const ticker = (params.ticker as string)?.toUpperCase() || ''
  
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
    let normalized = t.replace(/^[A-Z]+:\s*/i, '')
    const exchangeSuffixes = ['.JO', '.L', '.TO', '.PA', '.DE', '.HK', '.SS', '.SZ', '.T', '.AS', '.BR', '.MX', '.SA', '.SW', '.VI', '.ST', '.OL', '.CO', '.HE', '.IC', '.LS', '.MC', '.MI', '.NX', '.TA', '.TW', '.V', '.WA']
    const hasExchangeSuffix = exchangeSuffixes.some(suffix => normalized.toUpperCase().endsWith(suffix))
    
    if (hasExchangeSuffix) {
      const parts = normalized.split('.')
      if (parts.length > 1) {
        const lastPart = parts[parts.length - 1]
        if (lastPart.length <= 3 && /^[A-Z]{2,3}$/i.test(lastPart)) {
          const mainPart = parts.slice(0, -1).join('-')
          normalized = `${mainPart}.${lastPart}`
        } else {
          normalized = normalized.replace(/\./g, '-')
        }
      }
    } else {
      normalized = normalized.replace(/\./g, '-')
    }
    
    return normalized.toUpperCase()
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
      
      // Update watchlist with latest analysis data
      await loadWatchlistData()
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
    await loadAnalysis()
  }

  const handleRefreshData = async () => {
    setLoading(true)
    setError('')
    try {
      // Force refresh both watchlist data and analysis
      await loadWatchlistData(true)
      // loadWatchlistData now handles setLoading(false) internally
    } catch (err: any) {
      console.error('Refresh error:', err)
      setError(err?.message || 'Failed to refresh data')
      setLoading(false) // Ensure loading is set to false on error
    }
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
            {/* Show current business type and weights info - now clickable */}
            {analysis?.businessType && (
              <div style={{ position: 'relative', display: 'inline-block' }} data-model-dropdown>
                <p 
                  style={{ 
                    fontSize: '14px', 
                    color: '#6b7280', 
                    marginTop: '8px', 
                    margin: 0,
                    cursor: 'pointer',
                    padding: '4px 8px',
                    borderRadius: '4px',
                    backgroundColor: showModelDropdown ? '#f3f4f6' : 'transparent',
                    border: showModelDropdown ? '1px solid #d1d5db' : '1px solid transparent',
                    transition: 'all 0.2s ease'
                  }}
                  onClick={() => setShowModelDropdown(!showModelDropdown)}
                  onMouseEnter={(e) => {
                    if (!showModelDropdown) {
                      e.currentTarget.style.backgroundColor = '#f9fafb'
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!showModelDropdown) {
                      e.currentTarget.style.backgroundColor = 'transparent'
                    }
                  }}
                >
                  Business Type: <strong>{getModelDisplayName(analysis.businessType)}</strong>
                  {analysis.analysisWeights && (
                    <span style={{ marginLeft: '12px' }}>
                      (DCF: {(analysis.analysisWeights.dcf_weight * 100).toFixed(0)}%, 
                      EPV: {(analysis.analysisWeights.epv_weight * 100).toFixed(0)}%, 
                      Asset: {(analysis.analysisWeights.asset_weight * 100).toFixed(0)}%)
                    </span>
                  )}
                  <span style={{ marginLeft: '8px', fontSize: '12px' }}>
                    {showModelDropdown ? '▲' : '▼'}
                  </span>
                </p>
                
                {/* Model Selection Dropdown */}
                {showModelDropdown && (
                  <div style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    zIndex: 1000,
                    backgroundColor: 'white',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                    minWidth: '280px',
                    maxHeight: '300px',
                    overflowY: 'auto',
                    marginTop: '4px'
                  }}>
                    <div style={{ padding: '8px 0' }}>
                      <div style={{ 
                        padding: '8px 12px', 
                        fontSize: '12px', 
                        fontWeight: '600', 
                        color: '#6b7280',
                        borderBottom: '1px solid #e5e7eb'
                      }}>
                        Select Valuation Model
                      </div>
                      {availableModels.map((model) => (
                        <div
                          key={model}
                          style={{
                            padding: '10px 12px',
                            cursor: 'pointer',
                            fontSize: '14px',
                            backgroundColor: model === analysis.businessType ? '#eff6ff' : 'transparent',
                            color: model === analysis.businessType ? '#1d4ed8' : '#374151',
                            borderLeft: model === analysis.businessType ? '3px solid #2563eb' : '3px solid transparent'
                          }}
                          onClick={() => handleModelChange(model)}
                          onMouseEnter={(e) => {
                            if (model !== analysis.businessType) {
                              e.currentTarget.style.backgroundColor = '#f9fafb'
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (model !== analysis.businessType) {
                              e.currentTarget.style.backgroundColor = 'transparent'
                            }
                          }}
                        >
                          <div style={{ fontWeight: '500', marginBottom: '2px' }}>
                            {getModelDisplayName(model)}
                          </div>
                          {modelPresets[model] && (
                            <div style={{ fontSize: '12px', color: '#6b7280' }}>
                              DCF: {(modelPresets[model].dcf_weight * 100).toFixed(0)}%, 
                              EPV: {(modelPresets[model].epv_weight * 100).toFixed(0)}%, 
                              Asset: {(modelPresets[model].asset_weight * 100).toFixed(0)}%
                            </div>
                          )}
                        </div>
                      ))}
                      <div style={{ 
                        padding: '8px 12px', 
                        fontSize: '12px', 
                        color: '#6b7280',
                        borderTop: '1px solid #e5e7eb',
                        backgroundColor: '#f9fafb'
                      }}>
                        💡 Click a model to re-run analysis with new weights
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            {/* Refresh Button */}
            <button
              onClick={handleRefreshData}
              disabled={loading || analyzing}
              style={{
                padding: '10px 20px',
                backgroundColor: '#059669',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: (loading || analyzing) ? 'not-allowed' : 'pointer',
                opacity: (loading || analyzing) ? 0.5 : 1,
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              🔄 {loading ? 'Refreshing...' : 'Refresh Data'}
            </button>
            
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

      {/* Analysis Configuration Section - Moved to top for prominence */}
      <div style={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        borderRadius: '16px',
        padding: '24px',
        marginBottom: '24px',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.12)',
        border: '1px solid rgba(255, 255, 255, 0.1)'
      }}>
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: showWeightsConfig ? '20px' : '0'
        }}>
          <div>
            <h2 style={{ 
              fontSize: '20px', 
              fontWeight: '700', 
              color: 'white',
              margin: '0 0 8px 0',
              display: 'flex',
              alignItems: 'center',
              gap: '10px'
            }}>
              ⚙️ Analysis Configuration
            </h2>
            <p style={{ 
              fontSize: '14px', 
              color: 'rgba(255, 255, 255, 0.8)',
              margin: 0
            }}>
              {showWeightsConfig 
                ? 'Customize valuation weights and business model parameters'
                : `Current Model: ${(() => {
                    const currentModel = businessType || analysis?.businessType || 'default';
                    return getModelDisplayName(currentModel);
                  })()} • Click to configure analysis parameters`
              }
            </p>
          </div>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            {/* Current model indicator when config is closed */}
            {!showWeightsConfig && analysis?.analysisWeights && (
              <div style={{
                background: 'rgba(255, 255, 255, 0.15)',
                backdropFilter: 'blur(10px)',
                borderRadius: '8px',
                padding: '8px 12px',
                fontSize: '12px',
                color: 'white',
                fontWeight: '500'
              }}>
                DCF: {(analysis.analysisWeights.dcf_weight * 100).toFixed(0)}% • 
                EPV: {(analysis.analysisWeights.epv_weight * 100).toFixed(0)}% • 
                Asset: {(analysis.analysisWeights.asset_weight * 100).toFixed(0)}%
              </div>
            )}
            <button
              onClick={() => setShowWeightsConfig(!showWeightsConfig)}
              style={{
                padding: '12px 20px',
                background: showWeightsConfig 
                  ? 'rgba(239, 68, 68, 0.9)' 
                  : 'rgba(255, 255, 255, 0.15)',
                backdropFilter: 'blur(10px)',
                color: 'white',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                borderRadius: '10px',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: '600',
                whiteSpace: 'nowrap',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                transition: 'all 0.3s ease',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.1)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.15)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = '0 4px 16px rgba(0, 0, 0, 0.1)'
              }}
            >
              {showWeightsConfig ? '✕ Close Configuration' : '🎯 Configure Analysis'}
            </button>
          </div>
        </div>

        {/* Enhanced Analysis Weights Configuration */}
        {showWeightsConfig && (
          <div style={{
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(20px)',
            borderRadius: '12px',
            padding: '24px',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
          }}>
            <AnalysisWeightsConfig
              onWeightsChange={(weights, bt) => {
                setAnalysisWeights(weights)
                setBusinessType(bt)
              }}
              initialBusinessType={analysis?.businessType || undefined}
              initialWeights={analysis?.analysisWeights || undefined}
              ticker={ticker}
            />
            <div style={{ 
              marginTop: '20px', 
              display: 'flex', 
              gap: '12px',
              paddingTop: '20px',
              borderTop: '1px solid #e5e7eb'
            }}>
              <button
                onClick={() => {
                  setShowWeightsConfig(false)
                  loadAnalysis(true) // Re-run analysis with new weights
                }}
                style={{
                  padding: '12px 24px',
                  background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '10px',
                  cursor: 'pointer',
                  fontSize: '16px',
                  fontWeight: '600',
                  boxShadow: '0 4px 16px rgba(16, 185, 129, 0.3)',
                  transition: 'all 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 6px 20px rgba(16, 185, 129, 0.4)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = '0 4px 16px rgba(16, 185, 129, 0.3)'
                }}
              >
                🚀 Apply & Re-analyze
              </button>
              <button
                onClick={() => {
                  setShowWeightsConfig(false)
                  setAnalysisWeights(null)
                  setBusinessType(null)
                }}
                style={{
                  padding: '12px 24px',
                  background: 'linear-gradient(135deg, #6b7280 0%, #4b5563 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '10px',
                  cursor: 'pointer',
                  fontSize: '16px',
                  fontWeight: '600',
                  boxShadow: '0 4px 16px rgba(107, 114, 128, 0.3)',
                  transition: 'all 0.3s ease'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 6px 20px rgba(107, 114, 128, 0.4)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = '0 4px 16px rgba(107, 114, 128, 0.3)'
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Financial Summary Card */}
      {financialData?.financial_data?.key_metrics?.latest && (
        <div style={{
          background: 'white',
          borderRadius: '12px',
          padding: '24px',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
          marginBottom: '24px',
          border: '1px solid #e5e7eb'
        }}>
          <h2 style={{ 
            fontSize: '20px', 
            fontWeight: '600', 
            marginBottom: '20px', 
            color: '#111827',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            📊 Key Financial Metrics
          </h2>
          
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
            gap: '16px' 
          }}>
            {/* P/E Ratio */}
            {financialData.financial_data.key_metrics.latest.pe_ratio && (
              <div style={{
                padding: '16px',
                background: '#f8fafc',
                borderRadius: '8px',
                border: '1px solid #e2e8f0'
              }}>
                <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '4px', fontWeight: '500' }}>
                  P/E Ratio
                </div>
                <div style={{ 
                  fontSize: '24px', 
                  fontWeight: '700', 
                  color: financialData.financial_data.key_metrics.latest.pe_ratio < 20 ? '#10b981' : 
                         financialData.financial_data.key_metrics.latest.pe_ratio < 30 ? '#3b82f6' : '#f59e0b'
                }}>
                  {financialData.financial_data.key_metrics.latest.pe_ratio.toFixed(1)}
                </div>
              </div>
            )}

            {/* P/B Ratio */}
            {financialData.financial_data.key_metrics.latest.pb_ratio && (
              <div style={{
                padding: '16px',
                background: '#f8fafc',
                borderRadius: '8px',
                border: '1px solid #e2e8f0'
              }}>
                <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '4px', fontWeight: '500' }}>
                  P/B Ratio
                </div>
                <div style={{ 
                  fontSize: '24px', 
                  fontWeight: '700', 
                  color: financialData.financial_data.key_metrics.latest.pb_ratio < 2 ? '#10b981' : 
                         financialData.financial_data.key_metrics.latest.pb_ratio < 4 ? '#3b82f6' : '#f59e0b'
                }}>
                  {financialData.financial_data.key_metrics.latest.pb_ratio.toFixed(1)}
                </div>
              </div>
            )}

            {/* ROE */}
            {financialData.financial_data.key_metrics.latest.roe && (
              <div style={{
                padding: '16px',
                background: '#f8fafc',
                borderRadius: '8px',
                border: '1px solid #e2e8f0'
              }}>
                <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '4px', fontWeight: '500' }}>
                  Return on Equity
                </div>
                <div style={{ 
                  fontSize: '24px', 
                  fontWeight: '700', 
                  color: financialData.financial_data.key_metrics.latest.roe > 0.15 ? '#10b981' : 
                         financialData.financial_data.key_metrics.latest.roe > 0.10 ? '#3b82f6' : '#f59e0b'
                }}>
                  {(financialData.financial_data.key_metrics.latest.roe * 100).toFixed(1)}%
                </div>
              </div>
            )}

            {/* Debt-to-Equity */}
            {financialData.financial_data.key_metrics.latest.debt_to_equity !== undefined && (
              <div style={{
                padding: '16px',
                background: '#f8fafc',
                borderRadius: '8px',
                border: '1px solid #e2e8f0'
              }}>
                <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '4px', fontWeight: '500' }}>
                  Debt-to-Equity
                </div>
                <div style={{ 
                  fontSize: '24px', 
                  fontWeight: '700', 
                  color: financialData.financial_data.key_metrics.latest.debt_to_equity < 0.5 ? '#10b981' : 
                         financialData.financial_data.key_metrics.latest.debt_to_equity < 1.0 ? '#3b82f6' : '#f59e0b'
                }}>
                  {financialData.financial_data.key_metrics.latest.debt_to_equity.toFixed(2)}
                </div>
              </div>
            )}

            {/* Market Cap */}
            {financialData.financial_data.key_metrics.latest.market_cap && (
              <div style={{
                padding: '16px',
                background: '#f8fafc',
                borderRadius: '8px',
                border: '1px solid #e2e8f0'
              }}>
                <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '4px', fontWeight: '500' }}>
                  Market Cap
                </div>
                <div style={{ fontSize: '24px', fontWeight: '700', color: '#374151' }}>
                  ${(financialData.financial_data.key_metrics.latest.market_cap / 1e12).toFixed(2)}T
                </div>
              </div>
            )}

            {/* Current Ratio */}
            {financialData.financial_data.key_metrics.latest.current_ratio && (
              <div style={{
                padding: '16px',
                background: '#f8fafc',
                borderRadius: '8px',
                border: '1px solid #e2e8f0'
              }}>
                <div style={{ fontSize: '12px', color: '#64748b', marginBottom: '4px', fontWeight: '500' }}>
                  Current Ratio
                </div>
                <div style={{ 
                  fontSize: '24px', 
                  fontWeight: '700', 
                  color: financialData.financial_data.key_metrics.latest.current_ratio > 2 ? '#10b981' : 
                         financialData.financial_data.key_metrics.latest.current_ratio > 1 ? '#3b82f6' : '#f59e0b'
                }}>
                  {financialData.financial_data.key_metrics.latest.current_ratio.toFixed(2)}
                </div>
              </div>
            )}
          </div>
        </div>
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
              ticker={ticker}
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
              ticker={ticker}
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
            ticker={ticker}
            financialData={financialData?.financial_data}
            onDataUpdate={() => {
              loadFinancialData()
              loadAnalysis(true) // Refresh analysis when data is updated
            }}
          />
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

      {/* Show extracted data if available */}
      {watchlistData?.ai_extracted_data && (
        <ExtractedDataViewer
          data={watchlistData.ai_extracted_data}
          ticker={ticker}
        />
      )}

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
