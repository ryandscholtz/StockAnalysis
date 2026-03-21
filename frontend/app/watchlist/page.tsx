'use client'

import { useState, useEffect, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { stockApi } from '@/lib/api'
import { formatPrice, inferCurrencyFromTicker } from '@/lib/currency'
import { useCurrency } from '@/lib/useCurrency'
import { useAuth } from '@/components/AuthProvider'
import { useSessionState } from '@/lib/useSessionState'
import {
  AnalysisFilterModal,
  AnalysisFilterState,
  EMPTY_ANALYSIS_FILTERS,
  FilterRange,
  RecFilterType,
  countActiveFilters,
  recMatches,
} from '@/components/AnalysisFilterModal'

type WatchlistFilterState = AnalysisFilterState
const EMPTY_FILTERS = EMPTY_ANALYSIS_FILTERS

interface WatchlistItem {
  ticker: string
  company_name?: string
  exchange?: string
  current_price?: number
  price_change?: number
  price_change_percent?: number
  recommendation?: string
  last_updated?: string
  currency?: string
  fair_value?: number
  margin_of_safety_pct?: number
  financial_health_score?: number
  business_quality_score?: number
  last_analyzed_at?: string
  analysis_date?: string
  pe_ratio?: number
  pb_ratio?: number
  ps_ratio?: number
  ev_to_ebitda?: number
  upside_potential?: number
  companyType?: string
  sector?: string
  modelRecommendation?: string
  aiRecommendation?: string
}

// Helpers for private companies
const isPrivate = (ticker: string) => ticker.startsWith('PRIVATE#')
const displayTicker = (ticker: string) => isPrivate(ticker) ? ticker.slice('PRIVATE#'.length) : ticker

// Simple loading spinner component
const LoadingSpinner = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '20px' }}>
    <div style={{
      width: '40px',
      height: '40px',
      border: '4px solid var(--bg-hover)',
      borderTop: '4px solid var(--color-primary)',
      borderRadius: '50%',
      animation: 'spin 1s linear infinite'
    }}></div>
    <style jsx>{`
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    `}</style>
  </div>
)

export default function WatchlistPage() {
  const router = useRouter()
  const { isAuthenticated, loading: authLoading } = useAuth()
  const [watchlistItems, setWatchlistItems] = useState<WatchlistItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [bulkAnalyzing, setBulkAnalyzing] = useState(false)
  const [bulkResult, setBulkResult] = useState<{ success: boolean; message: string } | null>(null)
  const [bulkProgress, setBulkProgress] = useState<{ current: number; total: number; ticker: string } | null>(null)
  const [sortBy, setSortBy] = useSessionState<'name' | 'undervalued'>('watchlist_sortBy', 'name')
  const [recommendationFilter, setRecommendationFilter] = useSessionState<string[]>('watchlist_recFilter', [])
  const [recFilterType, setRecFilterType] = useSessionState<RecFilterType>('watchlist_recFilterType', 'overall')
  const [filters, setFilters] = useSessionState<WatchlistFilterState>('watchlist_filters', EMPTY_FILTERS)
  const [filterOpen, setFilterOpen] = useState(false)
  const [selectedTickers, setSelectedTickers] = useState<Set<string>>(new Set())
  const [confirmRemoveOpen, setConfirmRemoveOpen] = useState(false)
  const [showLocal, setShowLocal] = useState(false)
  const { preferredCurrency, convert, prefetchRates } = useCurrency()

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace('/')
    }
  }, [isAuthenticated, authLoading, router])

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      loadWatchlist()
    }
  }, [isAuthenticated, authLoading])

  // Pre-fetch FX rates whenever data loads or preferred currency changes
  useEffect(() => {
    if (watchlistItems.length > 0) {
      const currencies = watchlistItems.map(i => i.currency || inferCurrencyFromTicker(i.ticker, i.exchange) || 'USD')
      prefetchRates(currencies, preferredCurrency)
    }
  }, [watchlistItems, preferredCurrency, prefetchRates])

  const loadWatchlist = async () => {
    try {
      setLoading(true)
      setError('')

      // Get watchlist from API
      const response = await stockApi.getWatchlist()
      let items = response?.items || []

      // Fallback: for items without analysis data (recommendation missing = backend enrichment
      // didn't run), fetch latest_analysis directly from the manual-data endpoint
      const needsEnrichment = items.filter(item => !item.recommendation)
      if (needsEnrichment.length > 0) {
        const enriched = await Promise.all(
          needsEnrichment.map(async (item) => {
            try {
              const data = await stockApi.getFinancialData(item.ticker)
              const la = (data?.latest_analysis as any)
              if (!la) return item
              return {
                ...item,
                current_price: la.currentPrice ?? la.current_price ?? item.current_price,
                currency: la.currency ?? item.currency,
                fair_value: la.fairValue ?? la.fair_value ?? item.fair_value,
                margin_of_safety_pct: la.marginOfSafety ?? la.margin_of_safety_pct ?? item.margin_of_safety_pct,
                modelRecommendation: la.modelRecommendation ?? (la.recommendation !== 'AI Conflict' ? la.recommendation : null) ?? item.modelRecommendation,
                aiRecommendation: la.aiRecommendation ?? item.aiRecommendation,
                recommendation: (() => {
                  const recSev = (r?: string | null) => ({ 'Strong Buy': 1, 'Buy': 2, 'Hold': 3, 'Reduce': 4, 'Avoid': 5 } as Record<string, number>)[r ?? ''] ?? 0
                  const m = la.modelRecommendation ?? (la.recommendation !== 'AI Conflict' ? la.recommendation : null)
                  const a = la.aiRecommendation ?? null
                  if (!m && !a) return item.recommendation
                  if (!m) return a
                  if (!a) return m
                  return recSev(m) >= recSev(a) ? m : a
                })(),
                pe_ratio:        la.priceRatios?.priceToEarnings ?? la.aiFinancialData?.keyMetrics?.pe_ratio ?? la.pe_ratio ?? item.pe_ratio,
                pb_ratio:        la.priceRatios?.priceToBook ?? null,
                ps_ratio:        la.priceRatios?.priceToSales ?? null,
                ev_to_ebitda:    la.priceRatios?.enterpriseValueToEBITDA ?? null,
                upside_potential: la.upsidePotential ?? null,
                last_analyzed_at: la.timestamp ?? item.last_analyzed_at,
              }
            } catch {
              return item
            }
          })
        )
        const enrichedByTicker = new Map(enriched.map(item => [item.ticker, item]))
        items = items.map(item => enrichedByTicker.get(item.ticker) ?? item)
      }

      setWatchlistItems(items)
    } catch (err: any) {
      console.error('Error loading watchlist:', err)
      setError(err?.message || 'Failed to load watchlist')
      
      // Fallback to default stocks if API fails
      setWatchlistItems([
        { ticker: 'AAPL', company_name: 'Apple Inc.', current_price: 150.00, currency: 'USD' },
        { ticker: 'GOOGL', company_name: 'Alphabet Inc.', current_price: 2800.00, currency: 'USD' },
        { ticker: 'MSFT', company_name: 'Microsoft Corporation', current_price: 380.00, currency: 'USD' },
        { ticker: 'TSLA', company_name: 'Tesla Inc.', current_price: 250.00, currency: 'USD' },
        { ticker: 'BEL.XJSE', company_name: 'Bell Equipment Ltd', current_price: 12.45, currency: 'ZAR' }
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleStockClick = (stock: WatchlistItem) => {
    if (isPrivate(stock.ticker)) {
      const params = new URLSearchParams({ symbol: stock.ticker })
      if (stock.current_price) params.set('price', String(stock.current_price))
      if (stock.currency) params.set('currency', stock.currency)
      if (stock.company_name) params.set('company_name', stock.company_name)
      if (stock.sector) params.set('sector', stock.sector)
      router.push(`/ticker?${params.toString()}`)
    } else {
      router.push(`/ticker?ticker=${stock.ticker}`)
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

  const getPriceChangeColor = (change?: number) => {
    if (!change) return 'var(--text-muted)'
    return change >= 0 ? '#10b981' : '#ef4444'
  }

  const runBulkAnalysis = async () => {
    if (watchlistItems.length === 0) {
      setBulkResult({ success: false, message: 'No stocks in watchlist to analyze.' })
      setTimeout(() => setBulkResult(null), 5000)
      return
    }
    setBulkAnalyzing(true)
    setBulkResult(null)
    setError('')
    const tickers = selectedTickers.size > 0
      ? watchlistItems.map((i) => i.ticker).filter((t) => selectedTickers.has(t))
      : watchlistItems.map((item) => item.ticker)
    setBulkProgress({ current: 0, total: tickers.length, ticker: '' })

    try {
      // Start the bulk job — Lambda fans out async invocations per ticker
      const { jobId, total } = await stockApi.startBulkAnalysis(tickers)

      // Poll for progress every 2 seconds
      await new Promise<void>((resolve) => {
        const poll = setInterval(async () => {
          try {
            const status = await stockApi.getBulkStatus(jobId)
            setBulkProgress({ current: status.completed + status.failed, total: status.total, ticker: '' })
            if (status.status === 'complete') {
              clearInterval(poll)
              setBulkProgress(null)
              setBulkAnalyzing(false)
              setBulkResult({
                success: status.failed === 0,
                message: `Completed: ${status.completed} analysed${status.failed > 0 ? `, ${status.failed} failed` : ''}.`,
              })
              setTimeout(() => setBulkResult(null), 6000)
              await loadWatchlist()
              resolve()
            }
          } catch {
            // keep polling on transient errors
          }
        }, 2000)
      })
    } catch (err: any) {
      setBulkProgress(null)
      setBulkAnalyzing(false)
      setBulkResult({ success: false, message: err?.message || 'Failed to start bulk analysis.' })
      setTimeout(() => setBulkResult(null), 6000)
    }
  }

  const removeSelected = async () => {
    if (selectedTickers.size === 0) return
    const tickers = [...selectedTickers]
    setConfirmRemoveOpen(false)
    await Promise.allSettled(tickers.map((t) => stockApi.removeFromWatchlist(t)))
    setSelectedTickers(new Set())
    await loadWatchlist()
  }

  const toggleSelect = (ticker: string, e: React.MouseEvent) => {
    e.stopPropagation()
    setSelectedTickers((prev) => {
      const next = new Set(prev)
      next.has(ticker) ? next.delete(ticker) : next.add(ticker)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedTickers.size === displayItems.length && displayItems.length > 0) {
      setSelectedTickers(new Set())
    } else {
      setSelectedTickers(new Set(displayItems.map((s) => s.ticker)))
    }
  }

  const getValuationDisplay = (stock: WatchlistItem): { text: string; color: string } | null => {
    const margin = stock.margin_of_safety_pct
    if (margin == null || margin === undefined || (typeof margin === 'number' && isNaN(margin))) return null
    const absMargin = Math.abs(margin)
    if (margin > 0) {
      if (absMargin > 30) return { text: `${absMargin.toFixed(0)}% Undervalued`, color: '#059669' }
      if (absMargin > 10) return { text: `${absMargin.toFixed(0)}% Undervalued`, color: '#0d9488' }
      return { text: `${absMargin.toFixed(0)}% Undervalued`, color: '#10b981' }
    }
    return { text: `${absMargin.toFixed(0)}% Overvalued`, color: '#dc2626' }
  }

  const activeFilterCount = useMemo(
    () => countActiveFilters(filters, recommendationFilter),
    [filters, recommendationFilter]
  )

  const displayItems = useMemo(() => {
    const inRange = (val: number | null | undefined, { min, max }: FilterRange): boolean => {
      if (min === '' && max === '') return true
      if (val == null || !isFinite(val)) return false
      if (min !== '' && val < parseFloat(min)) return false
      if (max !== '' && val > parseFloat(max)) return false
      return true
    }
    let items = recommendationFilter.length === 0
      ? watchlistItems
      : watchlistItems.filter((s) => {
          const val = recFilterType === 'model' ? s.modelRecommendation
                    : recFilterType === 'ai'    ? s.aiRecommendation
                    : s.recommendation
          return recMatches(val, recommendationFilter)
        })
    if (activeFilterCount > 0) {
      items = items.filter((s) =>
        inRange(s.pe_ratio,          filters.peRatio) &&
        inRange(s.pb_ratio,          filters.pbRatio) &&
        inRange(s.ps_ratio,          filters.psRatio) &&
        inRange(s.ev_to_ebitda,      filters.evToEbitda) &&
        inRange(s.margin_of_safety_pct, filters.marginOfSafety) &&
        inRange(s.upside_potential,  filters.upsidePotential) &&
        inRange(s.current_price,     filters.price) &&
        inRange(s.fair_value,        filters.fairValue)
      )
    }
    return [...items].sort((a, b) => {
      if (sortBy === 'undervalued') {
        return (b.margin_of_safety_pct ?? -Infinity) - (a.margin_of_safety_pct ?? -Infinity)
      }
      return (a.company_name || a.ticker).localeCompare(b.company_name || b.ticker)
    })
  }, [watchlistItems, sortBy, recommendationFilter, recFilterType, filters, activeFilterCount])

  if (authLoading || (!isAuthenticated && !authLoading)) {
    return (
      <div className="container" style={{ padding: '40px 20px', textAlign: 'center' }}>
        <LoadingSpinner />
      </div>
    )
  }

  if (loading) {
    return (
      <div className="container" style={{ padding: '40px 20px', textAlign: 'center' }}>
        <LoadingSpinner />
        <p style={{ marginTop: '20px', color: 'var(--text-muted)' }}>Loading your watchlist...</p>
      </div>
    )
  }

  return (
    <div className="container watchlist-page" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '36px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '8px' }}>
          Watchlist
        </h1>
        <p style={{ fontSize: '16px', color: 'var(--text-muted)' }}>
          Monitor and analyze your favorite stocks with real-time data and comprehensive financial metrics.
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div style={{
          padding: '12px 16px',
          backgroundColor: 'var(--status-error-bg)',
          border: '1px solid #ef4444',
          borderRadius: '6px',
          color: 'var(--status-error-text)',
          marginBottom: '20px'
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Watchlist Items */}
      <div
        className="watchlist-cards-box"
        style={{
          background: 'var(--bg-surface)',
          borderRadius: '12px',
          padding: '24px',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.15)',
          border: '1px solid var(--border-default)',
          marginBottom: '32px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: selectedTickers.size > 0 ? '12px' : '24px', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
            <h2 style={{ fontSize: '24px', fontWeight: '600', color: 'var(--text-primary)', margin: 0 }}>
              📊 Your Stocks
            </h2>
            <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-hover)', borderRadius: '8px', padding: '3px' }}>
              {(['name', 'undervalued'] as const).map(opt => (
                <button
                  key={opt}
                  onClick={() => setSortBy(opt)}
                  style={{
                    padding: '4px 12px',
                    borderRadius: '6px',
                    border: 'none',
                    fontSize: '13px',
                    fontWeight: '500',
                    cursor: 'pointer',
                    backgroundColor: sortBy === opt ? 'var(--bg-surface)' : 'transparent',
                    color: sortBy === opt ? 'var(--text-primary)' : 'var(--text-muted)',
                    boxShadow: sortBy === opt ? '0 1px 3px rgba(0,0,0,0.15)' : 'none',
                  }}
                >
                  {opt === 'name' ? 'Name' : '% Undervalued'}
                </button>
              ))}
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setFilterOpen(true)}
                style={{ position: 'relative', padding: '6px 14px', borderRadius: '6px', border: `1px solid ${activeFilterCount > 0 ? 'var(--color-primary)' : 'var(--border-input)'}`, backgroundColor: activeFilterCount > 0 ? 'var(--color-primary-bg)' : 'var(--bg-surface)', color: activeFilterCount > 0 ? 'var(--color-primary)' : 'var(--text-secondary)', fontSize: '13px', cursor: 'pointer', fontWeight: activeFilterCount > 0 ? '600' : '400', whiteSpace: 'nowrap' }}
              >
                ⚙ Filters
                {activeFilterCount > 0 && (
                  <span style={{ marginLeft: '6px', backgroundColor: 'var(--color-primary)', color: '#fff', borderRadius: '10px', fontSize: '11px', padding: '1px 6px', fontWeight: '700' }}>{activeFilterCount}</span>
                )}
              </button>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button
              onClick={runBulkAnalysis}
              disabled={bulkAnalyzing || watchlistItems.length === 0}
              style={{
                padding: '8px 16px',
                backgroundColor: bulkAnalyzing ? '#9ca3af' : '#7c3aed',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: bulkAnalyzing ? 'not-allowed' : 'pointer'
              }}
            >
              {bulkProgress
                ? `⏳ ${bulkProgress.current}/${bulkProgress.total} done`
                : bulkAnalyzing
                  ? '⏳ Starting…'
                  : selectedTickers.size > 0
                    ? `📈 Analyse ${selectedTickers.size} selected`
                    : '📈 Analyse all'}
            </button>
            <button
              onClick={loadWatchlist}
              style={{
                padding: '8px 16px',
                backgroundColor: 'var(--color-primary)',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer'
              }}
            >
              🔄 Refresh
            </button>
            <button
              onClick={() => router.push('/watchlist/add')}
              style={{
                padding: '8px 16px',
                backgroundColor: '#10b981',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer'
              }}
            >
              ➕ Add Stock
            </button>
          </div>
            </div>
            {/* Currency toggle — far right, below action buttons */}
            <div style={{ display: 'flex', gap: '4px', background: 'var(--bg-hover)', borderRadius: '8px', padding: '3px' }}>
              {([false, true] as const).map(local => (
                <button
                  key={String(local)}
                  onClick={() => setShowLocal(local)}
                  style={{
                    padding: '4px 12px',
                    borderRadius: '6px',
                    border: 'none',
                    fontSize: '13px',
                    fontWeight: '500',
                    cursor: 'pointer',
                    backgroundColor: showLocal === local ? 'var(--bg-surface)' : 'transparent',
                    color: showLocal === local ? 'var(--text-primary)' : 'var(--text-muted)',
                    boxShadow: showLocal === local ? '0 1px 3px rgba(0,0,0,0.15)' : 'none',
                  }}
                >
                  {local ? 'Local' : preferredCurrency}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Selection action bar */}
        {displayItems.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px', padding: selectedTickers.size > 0 ? '10px 14px' : '0 2px', borderRadius: '8px', backgroundColor: selectedTickers.size > 0 ? 'var(--bg-hover)' : 'transparent', border: selectedTickers.size > 0 ? '1px solid var(--border-default)' : 'none', transition: 'all 0.15s ease', flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', userSelect: 'none', fontSize: '13px', color: 'var(--text-secondary)', fontWeight: '500' }}>
              <input
                type="checkbox"
                checked={displayItems.length > 0 && selectedTickers.size === displayItems.length}
                ref={(el) => { if (el) el.indeterminate = selectedTickers.size > 0 && selectedTickers.size < displayItems.length }}
                onChange={toggleSelectAll}
                style={{ width: '16px', height: '16px', cursor: 'pointer', accentColor: 'var(--color-primary)' }}
              />
              {selectedTickers.size === 0 ? 'Select all' : selectedTickers.size === displayItems.length ? 'Deselect all' : `${selectedTickers.size} selected`}
            </label>
            {selectedTickers.size > 0 && (
              <button
                onClick={() => setConfirmRemoveOpen(true)}
                style={{ padding: '4px 12px', borderRadius: '6px', border: '1px solid #ef4444', backgroundColor: 'transparent', color: '#ef4444', fontSize: '12px', fontWeight: '600', cursor: 'pointer' }}
              >
                🗑 Remove {selectedTickers.size}
              </button>
            )}
          </div>
        )}

        {filterOpen && (
          <AnalysisFilterModal
            filters={filters}
            onChange={setFilters}
            onClose={() => setFilterOpen(false)}
            onClear={() => { setFilters(EMPTY_FILTERS); setRecommendationFilter([]); setRecFilterType('overall') }}
            activeCount={activeFilterCount}
            selectedRecs={recommendationFilter}
            onRecsChange={setRecommendationFilter}
            recFilterType={recFilterType}
            onRecFilterTypeChange={setRecFilterType}
          />
        )}

        {bulkResult && (
          <div style={{
            padding: '12px 16px',
            marginBottom: '16px',
            backgroundColor: bulkResult.success ? 'var(--status-success-bg)' : 'var(--status-error-bg)',
            border: `1px solid ${bulkResult.success ? '#10b981' : '#ef4444'}`,
            borderRadius: '6px',
            color: bulkResult.success ? 'var(--status-success-text)' : 'var(--status-error-text)'
          }}>
            {bulkResult.success ? '✅' : '⚠️'} {bulkResult.message}
          </div>
        )}
        
        {watchlistItems.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
            <p>No stocks in your watchlist yet.</p>
            <button
              onClick={() => router.push('/watchlist/add')}
              style={{
                padding: '10px 20px',
                backgroundColor: 'var(--color-primary)',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                fontWeight: '500',
                cursor: 'pointer',
                marginTop: '16px'
              }}
            >
              Add Your First Stock
            </button>
          </div>
        ) : (
          <div className="watchlist-cards-grid" style={{ display: 'grid', gap: '16px' }}>
            {displayItems.length === 0 && (
              <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '14px' }}>
                No stocks match the current filters.{' '}
                <button onClick={() => { setFilters(EMPTY_FILTERS); setRecommendationFilter([]) }} style={{ background: 'none', border: 'none', color: 'var(--color-primary)', cursor: 'pointer', fontSize: '14px', fontWeight: '500' }}>Clear filters</button>
              </div>
            )}
            {displayItems.map((stock) => {
              const valuation = getValuationDisplay(stock)
              const isSelected = selectedTickers.has(stock.ticker)
              // Use stored currency, fall back to ticker/exchange inference, then USD
              const effectiveCurrency = stock.currency || inferCurrencyFromTicker(stock.ticker, stock.exchange) || 'USD'
              return (
              <div
                key={stock.ticker}
                className="watchlist-stock-card"
                style={{
                  padding: '20px',
                  border: `1px solid ${isSelected ? 'var(--color-primary)' : 'var(--border-default)'}`,
                  borderRadius: '8px',
                  backgroundColor: isSelected ? 'var(--color-primary-bg)' : 'var(--bg-surface-subtle)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
                onClick={() => handleStockClick(stock)}
                onMouseEnter={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = 'var(--bg-hover)'
                    e.currentTarget.style.borderColor = '#3b82f6'
                  }
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.2)'
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.backgroundColor = 'var(--bg-surface-subtle)'
                    e.currentTarget.style.borderColor = 'var(--border-default)'
                  }
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
                  {/* Checkbox */}
                  <div onClick={(e) => toggleSelect(stock.ticker, e)} style={{ paddingTop: '2px', flexShrink: 0 }}>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => {}}
                      style={{ width: '16px', height: '16px', cursor: 'pointer', accentColor: 'var(--color-primary)' }}
                    />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px', flexWrap: 'wrap' }}>
                      <h3 style={{ fontSize: '18px', fontWeight: '600', color: 'var(--text-primary)', margin: 0 }}>
                        {stock.company_name || `${stock.ticker} Corporation`}
                      </h3>
                      {isPrivate(stock.ticker) && (
                        <span style={{ padding: '3px 10px', borderRadius: '10px', fontSize: '11px', fontWeight: '700', color: '#7c3aed', backgroundColor: 'rgba(124,58,237,0.12)', border: '1px solid rgba(124,58,237,0.25)', letterSpacing: '0.03em' }}>
                          PRIVATE
                        </span>
                      )}
                      {stock.recommendation && (
                        <span style={{
                          padding: '4px 12px',
                          borderRadius: '12px',
                          fontSize: '12px',
                          fontWeight: '600',
                          color: 'white',
                          backgroundColor: getRecommendationColor(stock.recommendation)
                        }}>
                          {stock.recommendation}
                        </span>
                      )}
                      {valuation && (
                        <span style={{
                          padding: '4px 10px',
                          borderRadius: '8px',
                          fontSize: '12px',
                          fontWeight: '600',
                          color: 'white',
                          backgroundColor: valuation.color
                        }}>
                          {valuation.text}
                        </span>
                      )}
                      {/* Show when analysis ran but produced no fair value — missing financial data */}
                      {stock.last_analyzed_at && !stock.fair_value && (
                        <span style={{
                          padding: '4px 10px',
                          borderRadius: '8px',
                          fontSize: '12px',
                          fontWeight: '500',
                          color: 'var(--status-warning-text)',
                          backgroundColor: 'var(--status-warning-bg)',
                          border: '1px solid var(--status-warning-border)',
                        }}>
                          ⚠ Incomplete Data
                        </span>
                      )}
                    </div>
                    <p style={{ fontSize: '14px', color: 'var(--text-muted)', margin: '0 0 4px 0', fontFamily: isPrivate(stock.ticker) ? 'monospace' : undefined }}>
                      {displayTicker(stock.ticker)}
                      {stock.exchange && !isPrivate(stock.ticker) && <span style={{ marginLeft: '6px', fontSize: '12px' }}>· {stock.exchange}</span>}
                    </p>
                    <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginTop: '6px', alignItems: 'center' }}>
                      {stock.fair_value != null && !isNaN(stock.fair_value) && (
                        <span style={{ fontSize: '12px', color: 'var(--text-meta)' }}>
                          Fair value: {showLocal
                            ? formatPrice(stock.fair_value, effectiveCurrency)
                            : formatPrice(convert(stock.fair_value, effectiveCurrency) ?? undefined, preferredCurrency)}
                        </span>
                      )}
                      {stock.pe_ratio != null && !isNaN(stock.pe_ratio) && (
                        <span style={{ fontSize: '12px', color: 'var(--text-meta)' }}>
                          P/E: {stock.pe_ratio.toFixed(1)}
                        </span>
                      )}
                      {(stock.financial_health_score != null || stock.business_quality_score != null) && (
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                          {stock.financial_health_score != null && `Health ${Math.round(stock.financial_health_score)}`}
                          {stock.financial_health_score != null && stock.business_quality_score != null && ' · '}
                          {stock.business_quality_score != null && `Quality ${Math.round(stock.business_quality_score)}`}
                        </span>
                      )}
                    </div>
                    {(stock.last_updated || stock.last_analyzed_at) && (
                      <p style={{ fontSize: '12px', color: 'var(--text-subtle)', margin: '4px 0 0 0' }}>
                        Updated: {new Date(stock.last_analyzed_at || stock.last_updated!).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    {stock.current_price ? (
                      <>
                        <div style={{ fontSize: '20px', fontWeight: '700', color: 'var(--text-primary)' }}>
                          {showLocal
                            ? formatPrice(stock.current_price, effectiveCurrency)
                            : formatPrice(convert(stock.current_price, effectiveCurrency) ?? undefined, preferredCurrency)}
                        </div>
                        {stock.price_change !== undefined && !isPrivate(stock.ticker) && (
                          <div style={{
                            fontSize: '14px',
                            fontWeight: '500',
                            color: getPriceChangeColor(stock.price_change)
                          }}>
                            {stock.price_change >= 0 ? '+' : ''}{stock.price_change.toFixed(2)}
                            {stock.price_change_percent && (
                              <span style={{ marginLeft: '4px' }}>
                                ({stock.price_change_percent >= 0 ? '+' : ''}{stock.price_change_percent.toFixed(2)}%)
                              </span>
                            )}
                          </div>
                        )}
                      </>
                    ) : (
                      <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                        Price unavailable
                      </div>
                    )}
                    {stock.fair_value && stock.current_price && stock.current_price > 0 && (() => {
                      const multiplier = stock.fair_value / stock.current_price
                      const isUndervalued = multiplier > 1
                      return (
                        <div style={{
                          fontSize: '15px',
                          fontWeight: '700',
                          color: isUndervalued ? '#059669' : 'var(--text-muted)',
                          marginTop: '4px',
                        }}>
                          V/P: {multiplier.toFixed(2)}x
                        </div>
                      )
                    })()}
                  </div>
                </div>
              </div>
            )
            })}
          </div>
        )}
      </div>

      {/* Confirm remove modal */}
      {confirmRemoveOpen && (
        <div onClick={() => setConfirmRemoveOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 1000, backgroundColor: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
          <div onClick={(e) => e.stopPropagation()} style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '12px', width: '100%', maxWidth: '400px', padding: '28px 24px 20px', boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
            <div style={{ fontSize: '20px', marginBottom: '8px' }}>🗑 Remove from watchlist</div>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6', margin: '0 0 20px 0' }}>
              Remove <strong>{selectedTickers.size} stock{selectedTickers.size !== 1 ? 's' : ''}</strong> from your watchlist?
              {selectedTickers.size <= 5 && (
                <span style={{ display: 'block', marginTop: '8px', color: 'var(--text-muted)', fontSize: '13px' }}>
                  {[...selectedTickers].join(', ')}
                </span>
              )}
            </p>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setConfirmRemoveOpen(false)}
                style={{ padding: '8px 18px', borderRadius: '7px', border: '1px solid var(--border-input)', backgroundColor: 'transparent', color: 'var(--text-secondary)', fontSize: '14px', cursor: 'pointer', fontWeight: '500' }}
              >
                Cancel
              </button>
              <button
                onClick={removeSelected}
                style={{ padding: '8px 18px', borderRadius: '7px', border: 'none', backgroundColor: '#ef4444', color: '#fff', fontSize: '14px', cursor: 'pointer', fontWeight: '600' }}
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
