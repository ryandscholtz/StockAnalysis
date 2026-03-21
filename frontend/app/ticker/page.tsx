'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { stockApi, WatchlistItemDetail, QuoteResponse } from '@/lib/api'
import { StockAnalysis } from '@/types/analysis'
import { formatPrice, inferCurrencyFromTicker } from '@/lib/currency'
import { useCurrency } from '@/lib/useCurrency'
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
  const [marketQuote, setMarketQuote] = useState<QuoteResponse | null>(null)
  const [showLocal, setShowLocal] = useState(true)
  const { preferredCurrency, convert, prefetchRates } = useCurrency()

  // Private company URL params (set by watchlist navigation)
  const privatePrice = searchParams.get('price') ? parseFloat(searchParams.get('price')!) : undefined
  const privateCurrency = searchParams.get('currency') || undefined
  const privateCompanyName = searchParams.get('company_name') || undefined
  const privateSector = searchParams.get('sector') || undefined

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
      const priv = ticker.startsWith('PRIVATE#')
      loadWatchlistData()
      loadFinancialData()
      fetchAvailableModels()
      if (!priv) loadMarketQuote()
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

  // Pre-fetch FX rate for the ticker's local currency
  // Compute displayCurrency inline here (same logic as below) so this hook stays before conditional returns
  useEffect(() => {
    const storedCcy = watchlistData?.watchlist_item?.currency
    const localCcy = ticker.startsWith('PRIVATE#')
      ? (searchParams.get('currency') || storedCcy || analysis?.currency)
      : (analysis?.currency || storedCcy || inferCurrencyFromTicker(ticker, marketQuote?.exchange))
    if (localCcy) {
      prefetchRates([localCcy], preferredCurrency)
    }
  }, [watchlistData, analysis, ticker, marketQuote, preferredCurrency, prefetchRates, searchParams])

  const fetchAvailableModels = async () => {
    // P/E weight is implicit: pe = 1 - dcf - epv - asset
    const fallbackPresets = {
      'default':            { dcf_weight: 0.40, epv_weight: 0.20, asset_weight: 0.10 }, // pe=0.30
      'high_growth':        { dcf_weight: 0.60, epv_weight: 0.20, asset_weight: 0.05 }, // pe=0.15
      'growth_company':     { dcf_weight: 0.50, epv_weight: 0.15, asset_weight: 0.10 }, // pe=0.25
      'mature_company':     { dcf_weight: 0.35, epv_weight: 0.20, asset_weight: 0.10 }, // pe=0.35
      'cyclical':           { dcf_weight: 0.25, epv_weight: 0.35, asset_weight: 0.15 }, // pe=0.25
      'asset_heavy':        { dcf_weight: 0.20, epv_weight: 0.25, asset_weight: 0.45 }, // pe=0.10
      'distressed_company': { dcf_weight: 0.10, epv_weight: 0.15, asset_weight: 0.70 }, // pe=0.05
      'bank':               { dcf_weight: 0.20, epv_weight: 0.35, asset_weight: 0.15 }, // pe=0.30
      'reit':               { dcf_weight: 0.30, epv_weight: 0.15, asset_weight: 0.45 }, // pe=0.10
      'insurance':          { dcf_weight: 0.20, epv_weight: 0.40, asset_weight: 0.15 }, // pe=0.25
      'utility':            { dcf_weight: 0.40, epv_weight: 0.30, asset_weight: 0.10 }, // pe=0.20
      'technology':         { dcf_weight: 0.50, epv_weight: 0.20, asset_weight: 0.05 }, // pe=0.25
      'healthcare':         { dcf_weight: 0.45, epv_weight: 0.25, asset_weight: 0.05 }, // pe=0.25
      'retail':             { dcf_weight: 0.40, epv_weight: 0.20, asset_weight: 0.10 }, // pe=0.30
      'energy':             { dcf_weight: 0.25, epv_weight: 0.40, asset_weight: 0.20 }, // pe=0.15
    }
    const fallbackTypes = Object.keys(fallbackPresets)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/analysis-presets`)
      if (response.ok) {
        const data = await response.json()
        if (data && data.presets && data.business_types) {
          setAvailableModels(data.business_types)
          setModelPresets(data.presets)
          return
        }
      }
    } catch (error) {
      console.error('Error fetching models:', error)
    }
    // API unavailable or returned unexpected shape — use hardcoded fallback
    setAvailableModels(fallbackTypes)
    setModelPresets(fallbackPresets)
  }

  const handleModelChange = async (newModel: string) => {
    if (newModel === 'automatic') {
      // Let the backend auto-select the best preset (clears the override)
      setBusinessType(null)
      setAnalysisWeights(null)
      await loadAnalysis(false, null, null)
      return
    }
    const newWeights = modelPresets[newModel] ?? null
    setBusinessType(newModel)
    if (newWeights) setAnalysisWeights(newWeights)
    // Use cached financial data (no force refresh) — only the weights change.
    // Pass new values directly since React state updates aren't visible yet.
    await loadAnalysis(false, newModel, newWeights)
  }

  const getModelDisplayName = (modelKey: string) => {
    return modelKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const normalizeTicker = (t: string): string => {
    // Preserve PRIVATE# prefix for private companies
    if (t.startsWith('PRIVATE#')) return t
    // Only strip exchange prefix like "NYSE: AAPL" -> "AAPL"
    // Keep dots as-is (e.g. PPE.XJSE, BP.L, AAPL.TO)
    return t.replace(/^[A-Z]+:\s*/i, '').toUpperCase()
  }

  const loadFinancialData = async () => {
    try {
      const normalizedTicker = normalizeTicker(ticker)
      const result = await stockApi.getFinancialData(normalizedTicker)
      setFinancialData(result)
      // Hydrate the analysis panel from the cached result if not already set
      if (result.latest_analysis && !analyzing) {
        setAnalysis(result.latest_analysis)
      }
    } catch (err: any) {
      console.debug('Could not load financial data:', err)
      setFinancialData({
        ticker: normalizeTicker(ticker),
        financial_data: {},
        metadata: {},
        has_data: false
      })
    }
  }

  const loadMarketQuote = async () => {
    try {
      const q = await stockApi.getQuote(normalizeTicker(ticker))
      setMarketQuote(q)
    } catch {
      // non-fatal — Other Metrics just won't show
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

  const loadAnalysis = async (
    forceRefresh: boolean = false,
    overrideBusinessType?: string | null,
    overrideWeights?: AnalysisWeights | null
  ) => {
    try {
      setLoading(true)
      setError('')
      setProgress(null)

      // Try to get existing analysis first
      const normalizedTicker = normalizeTicker(ticker)
      const isPrivateCompany = normalizedTicker.startsWith('PRIVATE#')
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
        overrideBusinessType !== undefined ? overrideBusinessType : businessType,
        overrideWeights !== undefined ? overrideWeights : analysisWeights,
        isPrivateCompany ? {
          priceOverride: privatePrice,
          companyName: privateCompanyName,
          currency: privateCurrency,
          sector: privateSector,
        } : undefined
      )
      setAnalysis(data)
      // Sync preset from the backend response — always resolve to a real preset so
      // the dropdown never stays on "Automatic". Backend auto-selects when none given.
      const resolvedPreset = data.businessType || data.recommendedPreset || 'default'
      setBusinessType(resolvedPreset)
      const resolvedWeights = data.analysisWeights || modelPresets[resolvedPreset] || null
      if (resolvedWeights) setAnalysisWeights(resolvedWeights)
      
      // Update watchlist, stored financial data, and live quote with latest analysis
      await Promise.all([loadWatchlistData(), loadFinancialData(), loadMarketQuote()])
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
      case 'AI Conflict':
        return '#f97316'
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
              backgroundColor: 'var(--bg-hover)',
              color: 'var(--text-secondary)',
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
          <h1 style={{ fontSize: '32px', fontWeight: '700', color: 'var(--text-primary)', margin: 0 }}>
            {ticker}
          </h1>
        </div>

        <div style={{
          maxWidth: '600px',
          margin: '40px auto',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          padding: '32px 24px',
          borderRadius: '10px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.12)'
        }}>
          <h2 style={{ fontSize: '22px', fontWeight: '600', marginBottom: '24px', textAlign: 'center', color: 'var(--text-primary)' }}>
            {analyzing ? 'Analysing...' : 'Loading...'}
          </h2>

          {progress && (
            <div style={{ marginBottom: '16px' }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: '8px',
                fontSize: '13px',
                color: 'var(--text-muted)'
              }}>
                <span>Step {progress.step} of {progress.total || 8}</span>
                <span>{Math.round((progress.step / (progress.total || 8)) * 100)}%</span>
              </div>
              <div style={{
                width: '100%',
                height: '6px',
                background: 'var(--bg-hover)',
                borderRadius: '3px',
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${(progress.step / (progress.total || 8)) * 100}%`,
                  height: '100%',
                  background: 'var(--color-primary)',
                  transition: 'width 0.3s ease'
                }} />
              </div>
            </div>
          )}

          <p style={{
            fontSize: '14px',
            color: 'var(--text-muted)',
            fontWeight: '500',
            margin: 0,
            textAlign: 'center'
          }}>
            {progress?.task || 'Initialising...'}
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

  const isPrivateCompany = ticker.startsWith('PRIVATE#')

  // Prefer analysis company name (from MarketStack API) over stored watchlist name
  const companyName = analysis?.companyName || privateCompanyName || watchlistData?.watchlist_item?.company_name || ticker

  // For private companies: stored/URL price is authoritative (no market feed).
  // For public companies: analysis price > live quote > stored price.
  const storedWatchlistPrice = watchlistData?.watchlist_item?.current_price
  const rawPrice = isPrivateCompany
    ? (storedWatchlistPrice || privatePrice || analysis?.currentPrice)
    : (analysis?.currentPrice || watchlistData?.current_quote?.currentPrice || storedWatchlistPrice)
  // Hide price if it's exactly 1.0 (placeholder value when price cannot be fetched)
  const currentPrice = (rawPrice && Math.abs(rawPrice - 1.0) > 0.01) ? rawPrice : null
  const priceError = watchlistData?.price_error || null

  // For private companies: the URL-supplied or watchlist-stored currency is authoritative.
  // Analysis may have stored 'USD' as a default before private params were wired through.
  const storedWatchlistCurrency = watchlistData?.watchlist_item?.currency
  const displayCurrency = isPrivateCompany
    ? (privateCurrency || storedWatchlistCurrency || analysis?.currency)
    : (analysis?.currency || storedWatchlistCurrency || inferCurrencyFromTicker(ticker, marketQuote?.exchange))

  // Formatter for analysis monetary values — converts from analysis.currency to the active display currency
  const analysisCurrency = analysis?.currency || displayCurrency || 'USD'
  const targetCurrency = showLocal ? analysisCurrency : (preferredCurrency || analysisCurrency)
  const fmtAnalysisPrice = (amount: number | null | undefined): string => {
    if (amount == null || isNaN(amount as number) || !isFinite(amount as number)) return '-'
    if (analysisCurrency === targetCurrency) return formatPrice(amount, targetCurrency)
    const converted = convert(amount, analysisCurrency, targetCurrency)
    return converted != null ? formatPrice(converted, targetCurrency) : formatPrice(amount, analysisCurrency)
  }

  // Worst-of recommendation for the header badge (most cautious of model vs AI)
  const recSeverity = (rec?: string | null): number => {
    const map: Record<string, number> = { 'Strong Buy': 1, 'Buy': 2, 'Hold': 3, 'Reduce': 4, 'Avoid': 5 }
    return rec ? (map[rec] ?? 0) : 0
  }
  const modelRec = analysis?.modelRecommendation ?? (analysis?.recommendation !== 'AI Conflict' ? analysis?.recommendation : null)
    ?? watchlistData?.latest_analysis?.modelRecommendation
    ?? watchlistData?.watchlist_item?.recommendation ?? null
  const aiRec = analysis?.aiRecommendation ?? watchlistData?.latest_analysis?.aiRecommendation ?? null
  const recommendation = (() => {
    if (!modelRec && !aiRec) return null
    if (!modelRec) return aiRec
    if (!aiRec) return modelRec
    return recSeverity(modelRec) >= recSeverity(aiRec) ? modelRec : aiRec
  })()

  // Incomplete financial data: some core sections have data but at least one is missing
  const hasIncompleteFinancialData = (() => {
    const fd = financialData?.financial_data || {}
    const coreSections = ['income_statement', 'balance_sheet', 'cashflow']
    const someHaveData = coreSections.some(k => fd[k] && Object.keys(fd[k]).length > 0)
    const someAreMissing = coreSections.some(k => !fd[k] || Object.keys(fd[k] || {}).length === 0)
    return someHaveData && someAreMissing
  })()

  return (
    <div className="container" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <button
          onClick={() => router.push('/watchlist')}
          style={{
            padding: '8px 16px',
            backgroundColor: 'var(--bg-hover)',
            color: 'var(--text-secondary)',
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
            <div style={{ marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
              <h1 style={{ fontSize: '36px', fontWeight: '700', color: 'var(--text-primary)', margin: 0 }}>
                {companyName} ({ticker.startsWith('PRIVATE#') ? ticker.slice('PRIVATE#'.length) : ticker})
              </h1>
              {ticker.startsWith('PRIVATE#') && (
                <span style={{ padding: '4px 12px', borderRadius: '10px', fontSize: '13px', fontWeight: '700', color: '#7c3aed', backgroundColor: 'rgba(124,58,237,0.12)', border: '1px solid rgba(124,58,237,0.3)', letterSpacing: '0.03em', whiteSpace: 'nowrap' }}>
                  PRIVATE COMPANY
                </span>
              )}
            </div>
            {currentPrice ? (
              <div>
                <p style={{ fontSize: '20px', color: '#6b7280', margin: 0, display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                  <span>
                    {isPrivateCompany ? 'Stored Price' : 'Current Price'}:{' '}
                    {(() => {
                      if (showLocal || !displayCurrency) return formatPrice(currentPrice, displayCurrency)
                      const converted = convert(currentPrice, displayCurrency)
                      // Fall back to local price while rate is loading
                      return converted != null
                        ? formatPrice(converted, preferredCurrency)
                        : formatPrice(currentPrice, displayCurrency)
                    })()}
                  </span>
                  {marketQuote?.exchange && (
                    <span style={{ fontSize: '14px', color: '#9ca3af' }}>
                      · {marketQuote.exchange}
                    </span>
                  )}
                  {marketQuote?.sector && (
                    <span style={{ fontSize: '14px', color: '#9ca3af' }}>
                      · {marketQuote.sector}
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
                {/* Recommendation + Incomplete Data badges */}
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '8px', alignItems: 'center' }}>
                  {modelRec && (
                    <span style={{
                      padding: '5px 14px',
                      borderRadius: '16px',
                      fontSize: '13px',
                      fontWeight: '600',
                      color: 'white',
                      backgroundColor: getRecommendationColor(modelRec),
                      opacity: 0.85,
                    }}>
                      Model: {modelRec}
                    </span>
                  )}
                  {aiRec && (
                    <span style={{
                      padding: '5px 14px',
                      borderRadius: '16px',
                      fontSize: '13px',
                      fontWeight: '600',
                      color: 'white',
                      backgroundColor: getRecommendationColor(aiRec),
                      opacity: 0.85,
                    }}>
                      AI Analyst: {aiRec}
                    </span>
                  )}
                  {recommendation && (modelRec || aiRec) && (
                    <span style={{
                      padding: '6px 16px',
                      borderRadius: '16px',
                      fontSize: '14px',
                      fontWeight: '700',
                      color: 'white',
                      backgroundColor: getRecommendationColor(recommendation),
                      boxShadow: '0 0 0 2px white, 0 0 0 3px ' + getRecommendationColor(recommendation),
                    }}>
                      Overall: {recommendation}
                    </span>
                  )}
                  {hasIncompleteFinancialData && (
                    <span style={{
                      padding: '5px 12px',
                      borderRadius: '16px',
                      fontSize: '13px',
                      fontWeight: '500',
                      color: '#92400e',
                      backgroundColor: '#fef3c7',
                      border: '1px solid #fde68a',
                    }}>
                      ⚠ Incomplete Financial Data
                    </span>
                  )}
                </div>
              </div>
            ) : priceError ? (
              <p style={{ fontSize: '16px', color: '#dc2626', margin: 0, marginTop: '8px' }}>
                ⚠️ {priceError}
              </p>
            ) : null}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
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
            {/* Currency toggle — far right, below action buttons */}
            {displayCurrency && displayCurrency.toUpperCase() !== preferredCurrency.toUpperCase() && (
              <div style={{ display: 'flex', borderRadius: '6px', border: '1px solid var(--border-input)', overflow: 'hidden', fontSize: '13px' }}>
                {([true, false] as const).map(local => (
                  <button
                    key={String(local)}
                    onClick={() => setShowLocal(local)}
                    style={{
                      padding: '5px 14px',
                      border: 'none',
                      cursor: 'pointer',
                      fontWeight: showLocal === local ? '600' : '400',
                      backgroundColor: showLocal === local ? 'var(--color-primary)' : 'var(--bg-surface)',
                      color: showLocal === local ? 'white' : 'var(--text-muted)',
                    }}
                  >
                    {local ? displayCurrency : preferredCurrency}
                  </button>
                ))}
              </div>
            )}
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
            loadAnalysis(false)
          }}
        />
      )}

      {analysis ? (
        <>
          {/* Data Quality Warnings */}
          <DataQualityWarnings warnings={analysis.dataQualityWarnings} />

          {/* Show missing data prompt if needed */}
          {(!analysis.fairValue || analysis.fairValue === 0 || (analysis.missingData?.has_missing_data)) && (
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
          <AnalysisCard analysis={analysis} fmtPrice={fmtAnalysisPrice} />

          {/* Other Metrics — live market data, positioned just below Key Metrics */}
          {marketQuote && (() => {
            const currency = marketQuote.currency || analysis.currency || 'USD'
            const fmtPrice = (v?: number | null) =>
              v != null ? formatPrice(v, currency) : '—'
            const fmtNum = (v?: number | null, decimals = 2) =>
              v != null && isFinite(v) ? v.toFixed(decimals) : '—'
            const fmtLarge = (v?: number | null) => {
              if (v == null) return '—'
              if (v >= 1e12) return `${currency} ${(v / 1e12).toFixed(2)}T`
              if (v >= 1e9)  return `${currency} ${(v / 1e9).toFixed(2)}B`
              if (v >= 1e6)  return `${currency} ${(v / 1e6).toFixed(2)}M`
              return `${currency} ${v.toLocaleString()}`
            }
            const fmtVol = (v?: number | null) => {
              if (v == null) return '—'
              if (v >= 1e9) return `${(v / 1e9).toFixed(1)}B`
              if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`
              if (v >= 1e3) return `${(v / 1e3).toFixed(0)}K`
              return v.toFixed(0)
            }

            const metrics = [
              { label: 'Market Cap',     value: fmtLarge(marketQuote.marketCap) },
              { label: 'Forward P/E',    value: fmtNum(marketQuote.forwardPE) },
              { label: 'Dividend Yield', value: marketQuote.dividendYield != null ? `${marketQuote.dividendYield.toFixed(2)}%` : '—' },
              { label: 'Trailing EPS',   value: fmtPrice(marketQuote.eps) },
              { label: 'Beta',           value: fmtNum(marketQuote.beta) },
              { label: '52W High',       value: fmtPrice(marketQuote.week52High) },
              { label: '52W Low',        value: fmtPrice(marketQuote.week52Low) },
              { label: 'Volume',         value: fmtVol(marketQuote.volume) },
            ]

            const hasAny = metrics.some(m => m.value !== '—')
            if (!hasAny) return null

            return (
              <div className="card">
                <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '20px', color: 'var(--text-primary)' }}>
                  Other Metrics
                </h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '16px' }}>
                  {metrics.map(({ label, value }) => value !== '—' && (
                    <div key={label} style={{
                      padding: '16px',
                      background: 'var(--bg-surface-subtle)',
                      borderRadius: '6px',
                      border: '1px solid var(--border-default)',
                    }}>
                      <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '8px' }}>{label}</div>
                      <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--text-primary)', fontFamily: 'monospace' }}>{value}</div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })()}

          <ValuationStatus analysis={analysis} />

          {/* AI Commentary */}
          {analysis.aiCommentary && (
            <div style={{
              backgroundColor: 'var(--bg-surface, #fff)',
              border: '1px solid var(--border-default, #e5e7eb)',
              borderRadius: '12px',
              padding: '24px',
              marginBottom: '24px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                <span style={{ fontSize: '18px' }}>🤖</span>
                <h2 style={{ fontSize: '18px', fontWeight: '700', margin: 0, color: 'var(--text-primary, #111827)' }}>
                  AI Analysis
                </h2>
                <span style={{
                  fontSize: '11px',
                  padding: '2px 8px',
                  borderRadius: '10px',
                  backgroundColor: 'var(--bg-hover, #f3f4f6)',
                  color: 'var(--text-muted, #6b7280)',
                  fontWeight: '500',
                }}>
                  Claude Haiku
                </span>
              </div>
              <div style={{
                fontSize: '14px',
                lineHeight: '1.75',
                color: 'var(--text-secondary, #374151)',
                whiteSpace: 'pre-wrap',
              }}>
                {analysis.aiCommentary}
              </div>
            </div>
          )}

          <ValuationChart
            analysis={analysis}
            availablePresets={availableModels}
            currentPreset={businessType}
            onPresetChange={handleModelChange}
            fmtPrice={fmtAnalysisPrice}
          />

          {/* Stored financial data — below valuation breakdown */}
          <FinancialDataDisplay
            ticker={ticker}
            financialData={financialData.financial_data || {}}
            metadata={financialData.metadata || {}}
            financialCurrency={financialData.financial_currency}
            onPeriodDeleted={loadFinancialData}
          />
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