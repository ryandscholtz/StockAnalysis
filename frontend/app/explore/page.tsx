'use client'

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import Link from 'next/link'
import { stockApi, ExploreMarket, ExploreStock } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'
import { useSessionState } from '@/lib/useSessionState'
import {
  AnalysisFilterContent,
  AnalysisFilterState,
  EMPTY_ANALYSIS_FILTERS,
  RecFilterType,
  REC_OPTIONS,
  REC_COLOR,
  recMatches,
} from '@/components/AnalysisFilterModal'
import {
  formatPrice,
  formatLargeNumber,
  formatPercent,
  formatNumber,
  formatRatio,
  inferCurrencyFromTicker,
} from '@/lib/currency'
import { useCurrency } from '@/lib/useCurrency'

// ─── Types ────────────────────────────────────────────────────────────────────


// ─── AnalyseAndAddModal ───────────────────────────────────────────────────────

type AnalysePhase = 'setup' | 'analysing' | 'adding' | 'done'

function AnalyseAndAddModal({
  tickers,
  stocks,
  onClose,
  onAdded,
}: {
  tickers: string[]
  stocks: ExploreStock[]
  onClose: () => void
  onAdded: (count: number) => void
}) {
  const [filters, setFilters] = useState<AnalysisFilterState>(EMPTY_ANALYSIS_FILTERS)
  const [selectedRecs, setSelectedRecs] = useState<string[]>([])
  const [recFilterType, setRecFilterType] = useState<RecFilterType>('overall')
  const [phase, setPhase] = useState<AnalysePhase>('setup')
  const [progress, setProgress] = useState({ current: 0, total: tickers.length })
  const [result, setResult] = useState<{ added: number; skipped: number; failed: number } | null>(null)
  const [errorMsg, setErrorMsg] = useState('')

  const inRange = (val: number | null | undefined, { min, max }: { min: string; max: string }): boolean => {
    if (min === '' && max === '') return true
    if (val == null || !isFinite(val)) return false
    if (min !== '' && val < parseFloat(min)) return false
    if (max !== '' && val > parseFloat(max)) return false
    return true
  }

  const run = async () => {
    setPhase('analysing')
    setProgress({ current: 0, total: tickers.length })
    setErrorMsg('')
    try {
      // 1. Start bulk analysis
      const { jobId, total } = await stockApi.startBulkAnalysis(tickers)

      // 2. Poll until complete
      await new Promise<void>((resolve, reject) => {
        const poll = setInterval(async () => {
          try {
            const status = await stockApi.getBulkStatus(jobId)
            setProgress({ current: status.completed + status.failed, total: status.total })
            if (status.status === 'complete') {
              clearInterval(poll)
              resolve()
            }
          } catch (e) { /* keep polling */ }
        }, 2000)
        // safety timeout: 10 minutes
        setTimeout(() => { clearInterval(poll); reject(new Error('Timed out waiting for analysis')) }, 600_000)
      })

      // 3. Fetch analysis results & apply filters
      setPhase('adding')
      const hasNumericFilters = Object.values(filters).some(({ min, max }) => min !== '' || max !== '')
      const hasRecFilter = selectedRecs.length > 0

      const results = await Promise.all(
        tickers.map(async (ticker) => {
          try {
            const data = await stockApi.getFinancialData(ticker)
            const la = data.latest_analysis as any
            const stockInfo = stocks.find(s => s.ticker === ticker)
            if (!la) {
              // No analysis data — only passes if 'Unrated' is selected (or no rec filter)
              const passes = !hasRecFilter || selectedRecs.includes('Unrated')
              return { ticker, pass: passes, stockInfo, la: null }
            }

            // Recommendation filter
            if (hasRecFilter) {
              const rec = recFilterType === 'model' ? la.modelRecommendation
                : recFilterType === 'ai' ? la.aiRecommendation
                : la.recommendation
              if (!recMatches(rec, selectedRecs)) return { ticker, pass: false, stockInfo }
            }

            // Numeric filters — prefer analysis data, fall back to explore stock data
            if (hasNumericFilters) {
              const price = la.currentPrice ?? stockInfo?.price
              const fairValue = la.fairValue
              const marginOfSafety = la.marginOfSafety
              const upsidePotential = la.upsidePotential
              const peRatio = stockInfo?.peRatio
              const pbRatio = stockInfo?.pbRatio
              const psRatio = stockInfo?.psRatio
              const evToEbitda = stockInfo?.evToEbitda

              if (
                !inRange(peRatio, filters.peRatio) ||
                !inRange(pbRatio, filters.pbRatio) ||
                !inRange(psRatio, filters.psRatio) ||
                !inRange(evToEbitda, filters.evToEbitda) ||
                !inRange(marginOfSafety, filters.marginOfSafety) ||
                !inRange(upsidePotential, filters.upsidePotential) ||
                !inRange(price, filters.price) ||
                !inRange(fairValue, filters.fairValue)
              ) return { ticker, pass: false, stockInfo }
            }

            return { ticker, pass: true, stockInfo, la }
          } catch {
            return { ticker, pass: false, stockInfo: stocks.find(s => s.ticker === ticker), la: null }
          }
        })
      )

      // 4. Add passing stocks to watchlist
      const passing = results.filter(r => r.pass)
      let addedCount = 0
      let failedCount = 0
      await Promise.allSettled(passing.map(async ({ ticker, stockInfo, la }) => {
        try {
          await stockApi.addToWatchlist(
            ticker,
            stockInfo?.companyName || ticker,
            stockInfo?.exchange || '',
            undefined,
            undefined,
            la ? {
              recommendation: la.recommendation,
              modelRecommendation: la.modelRecommendation,
              aiRecommendation: la.aiRecommendation,
              fair_value: la.fairValue ?? la.fair_value,
              margin_of_safety_pct: la.marginOfSafety ?? la.margin_of_safety_pct,
              upside_potential: la.upsidePotential,
              pe_ratio: la.priceRatios?.peRatio,
              pb_ratio: la.priceRatios?.pbRatio,
              ps_ratio: la.priceRatios?.priceToSalesRatio,
              ev_to_ebitda: la.priceRatios?.enterpriseValueToEBITDA,
              current_price: la.currentPrice,
              last_analyzed_at: la.timestamp,
              currency: la.currency,
            } : undefined
          )
          addedCount++
        } catch {
          failedCount++
        }
      }))

      const skipped = tickers.length - passing.length
      setResult({ added: addedCount, skipped, failed: failedCount })
      setPhase('done')
      onAdded(addedCount)
    } catch (e: any) {
      setErrorMsg(e?.message || 'Something went wrong')
      setPhase('setup')
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, backgroundColor: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000, padding: '16px',
    }}>
      <div style={{
        backgroundColor: 'var(--bg-surface)', borderRadius: '12px',
        border: '1px solid var(--border-default)', width: '100%', maxWidth: '560px',
        maxHeight: '90vh', overflowY: 'auto',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--border-default)' }}>
          <div>
            <div style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>Analyse & Add to Watchlist</div>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>{tickers.length} stock{tickers.length !== 1 ? 's' : ''} selected</div>
          </div>
          {phase !== 'analysing' && phase !== 'adding' && (
            <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '18px', cursor: 'pointer', color: 'var(--text-muted)', lineHeight: 1 }}>×</button>
          )}
        </div>

        <div style={{ padding: '20px' }}>
          {/* Setup phase */}
          {(phase === 'setup') && (
            <>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Set optional filters below. Only stocks that pass after analysis will be added to your watchlist.
                Leave all filters empty to add every analysed stock.
              </p>

              <AnalysisFilterContent
                filters={filters}
                onChange={setFilters}
                selectedRecs={selectedRecs}
                onRecsChange={setSelectedRecs}
                recFilterType={recFilterType}
                onRecFilterTypeChange={setRecFilterType}
              />

              {errorMsg && (
                <div style={{ padding: '10px 14px', borderRadius: '6px', backgroundColor: 'var(--status-error-bg)', color: 'var(--status-error-text)', fontSize: '13px', marginBottom: '12px' }}>
                  {errorMsg}
                </div>
              )}

              <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '8px' }}>
                <button onClick={onClose} style={{ padding: '8px 16px', borderRadius: '6px', border: '1px solid var(--border-input)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-secondary)', fontSize: '13px', cursor: 'pointer' }}>
                  Cancel
                </button>
                <button onClick={run} style={{ padding: '8px 20px', borderRadius: '6px', border: 'none', backgroundColor: '#7c3aed', color: '#fff', fontSize: '13px', fontWeight: '600', cursor: 'pointer' }}>
                  Run Analysis
                </button>
              </div>
            </>
          )}

          {/* Analysing phase */}
          {(phase === 'analysing' || phase === 'adding') && (
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <div style={{ fontSize: '32px', marginBottom: '12px' }}>
                {phase === 'adding' ? '⚙️' : '📊'}
              </div>
              <div style={{ fontSize: '15px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '6px' }}>
                {phase === 'adding' ? 'Applying filters & adding…' : 'Analysing stocks…'}
              </div>
              {phase === 'analysing' && (
                <>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '16px' }}>
                    {progress.current} / {progress.total} complete
                  </div>
                  <div style={{ height: '6px', borderRadius: '3px', backgroundColor: 'var(--bg-hover)', overflow: 'hidden' }}>
                    <div style={{
                      height: '100%', borderRadius: '3px', backgroundColor: '#7c3aed',
                      width: `${progress.total > 0 ? (progress.current / progress.total) * 100 : 0}%`,
                      transition: 'width 0.4s ease',
                    }} />
                  </div>
                </>
              )}
            </div>
          )}

          {/* Done phase */}
          {phase === 'done' && result && (
            <div style={{ textAlign: 'center', padding: '24px 0' }}>
              <div style={{ fontSize: '32px', marginBottom: '12px' }}>✓</div>
              <div style={{ fontSize: '15px', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '16px' }}>Done!</div>
              <div style={{ display: 'flex', justifyContent: 'center', gap: '24px', marginBottom: '24px' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '28px', fontWeight: '700', color: '#10b981' }}>{result.added}</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Added</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '28px', fontWeight: '700', color: 'var(--text-muted)' }}>{result.skipped}</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Filtered out</div>
                </div>
                {result.failed > 0 && (
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '28px', fontWeight: '700', color: '#ef4444' }}>{result.failed}</div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Failed to add</div>
                  </div>
                )}
              </div>
              <button onClick={onClose} style={{ padding: '8px 24px', borderRadius: '6px', border: 'none', backgroundColor: '#7c3aed', color: '#fff', fontSize: '13px', fontWeight: '600', cursor: 'pointer' }}>
                Close
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

type SortField = keyof ExploreStock | null
type SortDir = 'asc' | 'desc'

interface FilterRange { min: string; max: string }
interface FilterState {
  price:         FilterRange
  marketCap:     FilterRange  // in $B
  peRatio:       FilterRange
  forwardPE:     FilterRange
  pbRatio:       FilterRange
  psRatio:       FilterRange
  evToEbitda:    FilterRange
  dividendYield: FilterRange  // %
  eps:           FilterRange
  beta:          FilterRange
  volume:        FilterRange  // in M
}

const EMPTY_FILTERS: FilterState = {
  price:         { min: '', max: '' },
  marketCap:     { min: '', max: '' },
  peRatio:       { min: '', max: '' },
  forwardPE:     { min: '', max: '' },
  pbRatio:       { min: '', max: '' },
  psRatio:       { min: '', max: '' },
  evToEbitda:    { min: '', max: '' },
  dividendYield: { min: '', max: '' },
  eps:           { min: '', max: '' },
  beta:          { min: '', max: '' },
  volume:        { min: '', max: '' },
}

// ─── Constants ────────────────────────────────────────────────────────────────

const COLUMNS: {
  key: SortField
  label: string
  align: 'left' | 'right'
  minWidth: number
  tooltip?: string
}[] = [
  { key: 'ticker',        label: 'Symbol',       align: 'left',  minWidth: 80 },
  { key: 'companyName',   label: 'Company',      align: 'left',  minWidth: 160 },
  { key: 'price',         label: 'Price',        align: 'right', minWidth: 90 },
  { key: 'priceChangePct',label: 'Chg %',        align: 'right', minWidth: 80 },
  { key: 'marketCap',     label: 'Mkt Cap',      align: 'right', minWidth: 100 },
  { key: 'peRatio',       label: 'P/E',          align: 'right', minWidth: 72,  tooltip: 'Trailing twelve-month P/E ratio' },
  { key: 'forwardPE',     label: 'Fwd P/E',      align: 'right', minWidth: 82,  tooltip: 'Forward P/E based on estimated earnings' },
  { key: 'pbRatio',       label: 'P/B',          align: 'right', minWidth: 72,  tooltip: 'Price-to-Book ratio' },
  { key: 'psRatio',       label: 'P/S',          align: 'right', minWidth: 72,  tooltip: 'Price-to-Sales (TTM)' },
  { key: 'evToEbitda',    label: 'EV/EBITDA',    align: 'right', minWidth: 96,  tooltip: 'Enterprise Value / EBITDA' },
  { key: 'dividendYield', label: 'Div Yield',    align: 'right', minWidth: 90,  tooltip: 'Annual dividend yield (%)' },
  { key: 'eps',           label: 'EPS',          align: 'right', minWidth: 72,  tooltip: 'Trailing EPS' },
  { key: 'beta',          label: 'Beta',         align: 'right', minWidth: 68,  tooltip: 'Beta vs. market benchmark' },
  { key: 'week52High',    label: '52W High',     align: 'right', minWidth: 90 },
  { key: 'week52Low',     label: '52W Low',      align: 'right', minWidth: 90 },
  { key: 'volume',        label: 'Volume',       align: 'right', minWidth: 100 },
  { key: 'sector',        label: 'Sector',       align: 'left',  minWidth: 120 },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatVolume(v?: number | null): string {
  if (v == null || isNaN(v)) return '-'
  if (v >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1)}B`
  if (v >= 1_000_000)     return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000)         return `${(v / 1_000).toFixed(0)}K`
  return v.toFixed(0)
}

function getSortValue(stock: ExploreStock, field: SortField): number | string {
  if (!field) return ''
  const val = stock[field as keyof ExploreStock]
  if (val == null) return field === 'ticker' || field === 'companyName' || field === 'sector' ? '' : -Infinity
  return val as number | string
}

// ─── Subcomponents ────────────────────────────────────────────────────────────

const SortIcon = ({ active, dir }: { active: boolean; dir: SortDir }) => (
  <span style={{
    display: 'inline-block',
    marginLeft: '4px',
    fontSize: '10px',
    opacity: active ? 1 : 0.35,
    color: active ? 'var(--color-primary)' : 'inherit',
    verticalAlign: 'middle',
  }}>
    {active ? (dir === 'asc' ? '▲' : '▼') : '⇅'}
  </span>
)

const SkeletonRow = () => (
  <tr>
    <td style={{ padding: '10px 12px', textAlign: 'center' }}>
      <div style={{ height: '15px', width: '15px', borderRadius: '3px', backgroundColor: 'var(--bg-hover)', animation: 'pulse 1.4s ease-in-out infinite', margin: '0 auto' }} />
    </td>
    {COLUMNS.map((col) => (
      <td key={String(col.key)} style={{ padding: '10px 12px' }}>
        <div style={{
          height: '14px',
          borderRadius: '4px',
          backgroundColor: 'var(--bg-hover)',
          width: col.align === 'right' ? '60%' : '80%',
          marginLeft: col.align === 'right' ? 'auto' : undefined,
          animation: 'pulse 1.4s ease-in-out infinite',
        }} />
      </td>
    ))}
  </tr>
)

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ExplorePage() {
  const { isAuthenticated } = useAuth()

  const [markets, setMarkets] = useState<ExploreMarket[]>([])
  const [selectedContinent, setSelectedContinent] = useSessionState<string>('explore_continent', 'Americas')
  const [selectedMarket, setSelectedMarket] = useSessionState<string>('explore_market', 'SP500')
  const [stocks, setStocks] = useState<ExploreStock[]>([])
  const [loading, setLoading] = useState(false)
  const [marketsLoading, setMarketsLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [cached, setCached] = useState(false)
  const [cacheAge, setCacheAge] = useState(0)

  const [sortField, setSortField] = useSessionState<SortField>('explore_sortField', 'marketCap')
  const [sortDir, setSortDir] = useSessionState<SortDir>('explore_sortDir', 'desc')

  const [watchlistTickers, setWatchlistTickers] = useState<Set<string>>(new Set())
  const [toastMessage, setToastMessage] = useState<string>('')

  const [sectorFilter, setSectorFilter] = useSessionState<string>('explore_sectorFilter', 'All')
  const [filters, setFilters] = useSessionState<FilterState>('explore_filters', EMPTY_FILTERS)
  const [filterOpen, setFilterOpen] = useState(false)

  // Selection state
  const [selectedTickers, setSelectedTickers] = useState<Set<string>>(new Set())
  const [bulkLoading, setBulkLoading] = useState(false)
  const selectAllRef = useRef<HTMLInputElement>(null)
  const [analyseModalOpen, setAnalyseModalOpen] = useState(false)
  const [showLocal, setShowLocal] = useState(false)
  const { preferredCurrency, prefetchRates } = useCurrency()

  // Derived: ordered continent list + markets per continent
  const continents = useMemo(() => {
    const order = ['Americas', 'Europe', 'Asia Pacific', 'Middle East & Africa']
    const seen = new Set(markets.map((m) => m.continent))
    return order.filter((c) => seen.has(c))
  }, [markets])

  const marketsForContinent = useMemo(
    () => markets.filter((m) => m.continent === selectedContinent),
    [markets, selectedContinent]
  )

  const handleContinentSelect = (continent: string) => {
    setSelectedContinent(continent)
    const first = markets.find((m) => m.continent === continent)
    if (first && !markets.find((m) => m.id === selectedMarket && m.continent === continent)) {
      setSelectedMarket(first.id)
    }
  }

  // Load available markets once
  useEffect(() => {
    stockApi.getExploreMarkets()
      .then((res) => setMarkets(res.markets))
      .catch(() => {/* fail silently */})
      .finally(() => setMarketsLoading(false))
  }, [])

  // Load watchlist if authenticated
  useEffect(() => {
    if (!isAuthenticated) return
    stockApi.getWatchlist()
      .then((res) => {
        const tickers = new Set<string>((res?.items || []).map((i: any) => i.ticker.toUpperCase()))
        setWatchlistTickers(tickers)
      })
      .catch(() => {/* ignore */})
  }, [isAuthenticated])

  // Clear selection when market changes
  useEffect(() => {
    setSelectedTickers(new Set())
  }, [selectedMarket])

  // Load stocks when market changes
  const loadStocks = useCallback(async (market: string, forceRefresh = false) => {
    setLoading(true)
    setError('')
    setSectorFilter('All')
    try {
      const res = await stockApi.getExploreStocks(market, forceRefresh)
      setStocks(res.stocks)
      setCached(res.cached)
      setCacheAge(res.cache_age_seconds)
    } catch (err: any) {
      setError(err?.message || 'Failed to load stocks.')
      setStocks([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStocks(selectedMarket)
  }, [selectedMarket, loadStocks])

  useEffect(() => {
    if (stocks.length > 0) {
      prefetchRates(stocks.map(s => s.currency || inferCurrencyFromTicker(s.ticker, s.exchange) || 'USD'), preferredCurrency)
    }
  }, [stocks, preferredCurrency, prefetchRates])

  // Sorting
  const handleSort = (field: SortField) => {
    if (field === sortField) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDir(field === 'companyName' || field === 'ticker' || field === 'sector' ? 'asc' : 'desc')
    }
  }

  // Unique sectors for filter
  const sectors = useMemo(() => {
    const set = new Set<string>()
    stocks.forEach((s) => { if (s.sector) set.add(s.sector) })
    return ['All', ...Array.from(set).sort()]
  }, [stocks])

  // Active filter count
  const activeFilterCount = useMemo(
    () => Object.values(filters).filter(({ min, max }) => min !== '' || max !== '').length,
    [filters]
  )

  // Filtered + sorted stocks
  const displayStocks = useMemo(() => {
    const inRange = (val: number | null | undefined, { min, max }: FilterRange): boolean => {
      if (min === '' && max === '') return true
      if (val == null || !isFinite(val)) return false
      if (min !== '' && val < parseFloat(min)) return false
      if (max !== '' && val > parseFloat(max)) return false
      return true
    }
    let filtered = sectorFilter === 'All' ? stocks : stocks.filter((s) => s.sector === sectorFilter)
    if (activeFilterCount > 0) {
      filtered = filtered.filter((s) =>
        inRange(s.price, filters.price) &&
        inRange(s.marketCap != null ? s.marketCap / 1e9 : null, filters.marketCap) &&
        inRange(s.peRatio, filters.peRatio) &&
        inRange(s.forwardPE, filters.forwardPE) &&
        inRange(s.pbRatio, filters.pbRatio) &&
        inRange(s.psRatio, filters.psRatio) &&
        inRange(s.evToEbitda, filters.evToEbitda) &&
        inRange(s.dividendYield, filters.dividendYield) &&
        inRange(s.eps, filters.eps) &&
        inRange(s.beta, filters.beta) &&
        inRange(s.volume != null ? s.volume / 1e6 : null, filters.volume)
      )
    }
    if (!sortField) return filtered
    return [...filtered].sort((a, b) => {
      const av = getSortValue(a, sortField)
      const bv = getSortValue(b, sortField)
      if (av === bv) return 0
      if (av === -Infinity || av === '') return 1
      if (bv === -Infinity || bv === '') return -1
      const cmp = av < bv ? -1 : 1
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [stocks, sortField, sortDir, sectorFilter, filters, activeFilterCount])

  // Selection helpers
  const visibleTickers = useMemo(() => displayStocks.map((s) => s.ticker), [displayStocks])
  const allSelected = visibleTickers.length > 0 && visibleTickers.every((t) => selectedTickers.has(t))
  const someSelected = !allSelected && visibleTickers.some((t) => selectedTickers.has(t))

  // Sync header checkbox indeterminate state
  useEffect(() => {
    if (selectAllRef.current) selectAllRef.current.indeterminate = someSelected
  }, [someSelected])

  const handleToggleSelect = useCallback((ticker: string) => {
    setSelectedTickers((prev) => {
      const next = new Set(prev)
      if (next.has(ticker)) next.delete(ticker)
      else next.add(ticker)
      return next
    })
  }, [])

  const handleToggleAll = () => {
    if (allSelected || someSelected) {
      setSelectedTickers(new Set())
    } else {
      setSelectedTickers(new Set(visibleTickers))
    }
  }

  const showToast = (msg: string) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(''), 3500)
  }

  // Bulk add to watchlist
  const handleBulkAdd = async () => {
    if (!isAuthenticated || bulkLoading) return
    const toAdd = [...selectedTickers].filter((t) => !watchlistTickers.has(t))
    if (!toAdd.length) { showToast('All selected stocks are already on your watchlist'); return }
    setBulkLoading(true)
    try {
      await Promise.all(toAdd.map((ticker) => {
        const s = stocks.find((x) => x.ticker === ticker)
        return stockApi.addToWatchlist(ticker, s?.companyName || ticker, s?.exchange || '')
      }))
      setWatchlistTickers((prev) => new Set([...prev, ...toAdd]))
      setSelectedTickers(new Set())
      showToast(`${toAdd.length} stock${toAdd.length !== 1 ? 's' : ''} added to watchlist`)
    } catch {
      showToast('Some stocks could not be added. Please try again.')
    } finally {
      setBulkLoading(false)
    }
  }

  // Bulk remove from watchlist
  const handleBulkRemove = async () => {
    if (!isAuthenticated || bulkLoading) return
    const toRemove = [...selectedTickers].filter((t) => watchlistTickers.has(t))
    if (!toRemove.length) { showToast('None of the selected stocks are on your watchlist'); return }
    setBulkLoading(true)
    try {
      await Promise.all(toRemove.map((ticker) => stockApi.removeFromWatchlist(ticker)))
      setWatchlistTickers((prev) => new Set([...prev].filter((t) => !toRemove.includes(t))))
      setSelectedTickers(new Set())
      showToast(`${toRemove.length} stock${toRemove.length !== 1 ? 's' : ''} removed from watchlist`)
    } catch {
      showToast('Some stocks could not be removed. Please try again.')
    } finally {
      setBulkLoading(false)
    }
  }

  const currentMarket = markets.find((m) => m.id === selectedMarket)
  const numSelected = selectedTickers.size
  const canAdd    = [...selectedTickers].some((t) => !watchlistTickers.has(t))
  const canRemove = [...selectedTickers].some((t) => watchlistTickers.has(t))

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div className="container" style={{ paddingBottom: '48px' }}>
      {/* Page header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '6px' }}>
          Explore Stocks
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
          Browse stocks by market or exchange. Click a symbol to view its full analysis.
          {cached && (
            <span style={{ marginLeft: '8px', color: 'var(--text-subtle)', fontSize: '12px' }}>
              (data cached · {Math.floor(cacheAge / 60)}m ago)
            </span>
          )}
        </p>
      </div>

      {/* Market selector — two-tier: continents → markets */}
      {marketsLoading ? (
        <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} style={{ height: '34px', width: '110px', borderRadius: '8px', backgroundColor: 'var(--bg-hover)', animation: 'pulse 1.4s ease-in-out infinite' }} />
          ))}
        </div>
      ) : (
        <>
          {/* Continent tabs */}
          <div style={{
            display: 'flex',
            gap: '4px',
            marginBottom: '10px',
            borderBottom: '2px solid var(--border-default)',
            paddingBottom: '0',
          }}>
            {continents.map((c) => (
              <button
                key={c}
                onClick={() => handleContinentSelect(c)}
                style={{
                  padding: '7px 16px',
                  border: 'none',
                  borderBottom: selectedContinent === c ? '2px solid var(--color-primary)' : '2px solid transparent',
                  marginBottom: '-2px',
                  backgroundColor: 'transparent',
                  color: selectedContinent === c ? 'var(--color-primary)' : 'var(--text-muted)',
                  fontSize: '13px',
                  fontWeight: selectedContinent === c ? '600' : '400',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  transition: 'color 0.15s',
                }}
              >
                {c}
              </button>
            ))}
          </div>

          {/* Market pills for selected continent */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '16px' }}>
            {marketsForContinent.map((m) => (
              <button
                key={m.id}
                onClick={() => setSelectedMarket(m.id)}
                style={{
                  padding: '5px 12px',
                  borderRadius: '6px',
                  border: '1px solid',
                  borderColor: selectedMarket === m.id ? 'var(--color-primary)' : 'var(--border-default)',
                  backgroundColor: selectedMarket === m.id ? 'var(--color-primary-bg)' : 'var(--bg-surface)',
                  color: selectedMarket === m.id ? 'var(--color-primary)' : 'var(--text-secondary)',
                  fontSize: '13px',
                  fontWeight: selectedMarket === m.id ? '600' : '400',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                  whiteSpace: 'nowrap',
                }}
              >
                {m.name}
                <span style={{ marginLeft: '5px', fontSize: '11px', opacity: 0.55 }}>
                  {m.screener_based
                    ? (m.ticker_count != null ? m.ticker_count : 'all')
                    : m.ticker_count}
                </span>
              </button>
            ))}
          </div>
        </>
      )}

      {/* Controls row */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '12px',
        marginBottom: '16px',
      }}>
        {/* Market description */}
        <div style={{ flex: 1, minWidth: '200px' }}>
          {currentMarket && (
            <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              <strong style={{ color: 'var(--text-secondary)' }}>{currentMarket.name}</strong>
              {' · '}{currentMarket.description}
              {' · '}<span style={{ color: 'var(--text-subtle)' }}>{currentMarket.region}</span>
            </p>
          )}
        </div>

        {/* Sector filter */}
        {sectors.length > 2 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>Sector:</span>
            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              style={{
                padding: '5px 10px',
                borderRadius: '6px',
                border: '1px solid var(--border-input)',
                backgroundColor: 'var(--bg-surface)',
                color: 'var(--text-primary)',
                fontSize: '13px',
                cursor: 'pointer',
              }}
            >
              {sectors.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
        )}

        {/* Filter button */}
        <button
          onClick={() => setFilterOpen(true)}
          style={{
            position: 'relative',
            padding: '6px 14px',
            borderRadius: '6px',
            border: `1px solid ${activeFilterCount > 0 ? 'var(--color-primary)' : 'var(--border-input)'}`,
            backgroundColor: activeFilterCount > 0 ? 'var(--color-primary-bg)' : 'var(--bg-surface)',
            color: activeFilterCount > 0 ? 'var(--color-primary)' : 'var(--text-secondary)',
            fontSize: '13px',
            cursor: 'pointer',
            whiteSpace: 'nowrap',
            fontWeight: activeFilterCount > 0 ? '600' : '400',
          }}
        >
          ⚙ Filters
          {activeFilterCount > 0 && (
            <span style={{
              marginLeft: '6px',
              backgroundColor: 'var(--color-primary)',
              color: '#fff',
              borderRadius: '10px',
              fontSize: '11px',
              padding: '1px 6px',
              fontWeight: '700',
            }}>
              {activeFilterCount}
            </span>
          )}
        </button>

        {/* Refresh button */}
        <button
          onClick={() => loadStocks(selectedMarket, true)}
          disabled={loading}
          style={{
            padding: '6px 14px',
            borderRadius: '6px',
            border: '1px solid var(--border-input)',
            backgroundColor: 'var(--bg-surface)',
            color: 'var(--text-secondary)',
            fontSize: '13px',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.6 : 1,
            whiteSpace: 'nowrap',
          }}
        >
          {loading ? 'Loading…' : '↻ Refresh'}
        </button>
      </div>

      {/* Advanced filter modal */}
      {filterOpen && (
        <FilterModal
          filters={filters}
          onChange={setFilters}
          onClose={() => setFilterOpen(false)}
          onClear={() => setFilters(EMPTY_FILTERS)}
          activeCount={activeFilterCount}
        />
      )}

      {/* Bulk action bar — slides in when stocks are selected */}
      {numSelected > 0 && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '10px 14px',
          marginBottom: '12px',
          borderRadius: '8px',
          backgroundColor: 'var(--color-primary-bg)',
          border: '1px solid var(--color-primary)',
          flexWrap: 'wrap',
        }}>
          <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--color-primary)', whiteSpace: 'nowrap' }}>
            {numSelected} selected
          </span>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
            {!isAuthenticated ? (
              <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                Sign in to add to watchlist
              </span>
            ) : (
              <>
                {canAdd && (
                  <button
                    onClick={handleBulkAdd}
                    disabled={bulkLoading}
                    style={{
                      padding: '5px 14px',
                      borderRadius: '6px',
                      border: '1px solid var(--color-primary)',
                      backgroundColor: 'var(--color-primary)',
                      color: '#fff',
                      fontSize: '13px',
                      fontWeight: '500',
                      cursor: bulkLoading ? 'not-allowed' : 'pointer',
                      opacity: bulkLoading ? 0.6 : 1,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {bulkLoading ? '…' : '+ Add to Watchlist'}
                  </button>
                )}
                <button
                  onClick={() => setAnalyseModalOpen(true)}
                  disabled={bulkLoading}
                  style={{
                    padding: '5px 14px',
                    borderRadius: '6px',
                    border: '1px solid #7c3aed',
                    backgroundColor: '#7c3aed',
                    color: '#fff',
                    fontSize: '13px',
                    fontWeight: '500',
                    cursor: bulkLoading ? 'not-allowed' : 'pointer',
                    opacity: bulkLoading ? 0.6 : 1,
                    whiteSpace: 'nowrap',
                  }}
                >
                  📊 Analyse & Add to Watchlist
                </button>
                {canRemove && (
                  <button
                    onClick={handleBulkRemove}
                    disabled={bulkLoading}
                    style={{
                      padding: '5px 14px',
                      borderRadius: '6px',
                      border: '1px solid var(--border-input)',
                      backgroundColor: 'var(--bg-surface)',
                      color: 'var(--text-secondary)',
                      fontSize: '13px',
                      fontWeight: '500',
                      cursor: bulkLoading ? 'not-allowed' : 'pointer',
                      opacity: bulkLoading ? 0.6 : 1,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {bulkLoading ? '…' : '− Remove from Watchlist'}
                  </button>
                )}
              </>
            )}
            <button
              onClick={() => setSelectedTickers(new Set())}
              disabled={bulkLoading}
              style={{
                padding: '5px 10px',
                borderRadius: '6px',
                border: 'none',
                backgroundColor: 'transparent',
                color: 'var(--text-muted)',
                fontSize: '13px',
                cursor: bulkLoading ? 'not-allowed' : 'pointer',
                whiteSpace: 'nowrap',
              }}
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Analyse & Add to Watchlist modal */}
      {analyseModalOpen && (
        <AnalyseAndAddModal
          tickers={[...selectedTickers]}
          stocks={stocks}
          onClose={() => setAnalyseModalOpen(false)}
          onAdded={(count) => {
            if (count > 0) {
              setWatchlistTickers(prev => new Set([...prev, ...[...selectedTickers]]))
              setSelectedTickers(new Set())
              showToast(`${count} stock${count !== 1 ? 's' : ''} added to watchlist`)
            }
          }}
        />
      )}

      {/* Toast notification */}
      {toastMessage && (
        <div style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          backgroundColor: 'var(--status-success-bg, #f0fdf4)',
          border: '1px solid #86efac',
          color: '#166534',
          padding: '10px 16px',
          borderRadius: '8px',
          fontSize: '14px',
          fontWeight: '500',
          zIndex: 1000,
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        }}>
          ✓ {toastMessage}
        </div>
      )}

      {/* Error state */}
      {error && (
        <div style={{
          padding: '16px',
          borderRadius: '8px',
          backgroundColor: 'var(--status-error-bg)',
          border: '1px solid var(--status-error-border, #fca5a5)',
          color: 'var(--status-error-text)',
          marginBottom: '16px',
          fontSize: '14px',
        }}>
          {error}
        </div>
      )}

      {/* Result count */}
      {!loading && !error && displayStocks.length > 0 && (
        <p style={{ fontSize: '12px', color: 'var(--text-subtle)', marginBottom: '8px' }}>
          Showing {displayStocks.length} stock{displayStocks.length !== 1 ? 's' : ''}
          {sectorFilter !== 'All' ? ` in ${sectorFilter}` : ''}
        </p>
      )}

      {/* Currency toggle — above table, aligned right */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '8px' }}>
        <div style={{ display: 'flex', gap: '0', borderRadius: '6px', border: '1px solid var(--border-input)', overflow: 'hidden' }}>
          {([false, true] as const).map(local => (
            <button
              key={String(local)}
              onClick={() => setShowLocal(local)}
              style={{
                padding: '6px 12px',
                border: 'none',
                fontSize: '13px',
                fontWeight: showLocal === local ? '600' : '400',
                cursor: 'pointer',
                backgroundColor: showLocal === local ? 'var(--color-primary)' : 'var(--bg-surface)',
                color: showLocal === local ? 'white' : 'var(--text-muted)',
              }}
            >
              {local ? 'Local' : preferredCurrency}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div style={{
        overflowX: 'auto',
        WebkitOverflowScrolling: 'touch',
        borderRadius: '10px',
        border: '1px solid var(--border-default)',
        backgroundColor: 'var(--bg-surface)',
      }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: '13px',
          minWidth: '1200px',
        }}>
          <thead>
            <tr style={{ backgroundColor: 'var(--bg-surface-subtle)' }}>
              {/* Select-all checkbox */}
              <th style={{
                padding: '10px 12px',
                textAlign: 'center',
                borderBottom: '2px solid var(--border-default)',
                position: 'sticky',
                top: 0,
                left: 0,
                backgroundColor: 'var(--bg-surface-subtle)',
                zIndex: 3,
                minWidth: 40,
                width: 40,
              }}>
                <input
                  ref={selectAllRef}
                  type="checkbox"
                  checked={allSelected}
                  onChange={handleToggleAll}
                  disabled={loading || displayStocks.length === 0}
                  title={allSelected ? 'Deselect all' : 'Select all'}
                  style={{ cursor: 'pointer', width: '15px', height: '15px', accentColor: 'var(--color-primary)' }}
                />
              </th>
              {COLUMNS.map((col, colIdx) => (
                <th
                  key={String(col.key)}
                  title={col.tooltip}
                  onClick={() => col.key && handleSort(col.key)}
                  style={{
                    padding: '10px 12px',
                    textAlign: col.align,
                    fontWeight: '600',
                    fontSize: '12px',
                    color: sortField === col.key ? 'var(--color-primary)' : 'var(--text-muted)',
                    borderBottom: '2px solid var(--border-default)',
                    cursor: col.key ? 'pointer' : 'default',
                    whiteSpace: 'nowrap',
                    position: 'sticky',
                    top: 0,
                    left: colIdx === 0 ? 40 : undefined,
                    backgroundColor: 'var(--bg-surface-subtle)',
                    zIndex: colIdx === 0 ? 3 : 2,
                    minWidth: col.minWidth,
                    userSelect: 'none',
                    boxShadow: colIdx === 0 ? '2px 0 6px -2px rgba(0,0,0,0.08)' : undefined,
                  }}
                >
                  {col.label}
                  {col.key && <SortIcon active={sortField === col.key} dir={sortDir} />}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 12 }).map((_, i) => <SkeletonRow key={i} />)
              : displayStocks.map((stock, idx) => (
                  <StockRow
                    key={stock.ticker}
                    stock={stock}
                    idx={idx}
                    selected={selectedTickers.has(stock.ticker)}
                    onToggle={handleToggleSelect}
                    onWatchlist={watchlistTickers.has(stock.ticker.toUpperCase())}
                    showLocal={showLocal}
                  />
                ))}
            {!loading && !error && displayStocks.length === 0 && (
              <tr>
                <td
                  colSpan={COLUMNS.length + 1}
                  style={{ padding: '48px 16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '14px' }}
                >
                  No stocks found. Try refreshing or selecting a different market.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Disclaimer */}
      <p style={{ marginTop: '16px', fontSize: '11px', color: 'var(--text-subtle)', lineHeight: '1.5' }}>
        Data provided via Yahoo Finance. Prices and ratios may be delayed. Not financial advice.
        Data is cached for up to 15 minutes.
      </p>

      <style jsx global>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  )
}

// ─── Stock Row ────────────────────────────────────────────────────────────────

interface StockRowProps {
  stock: ExploreStock
  idx: number
  selected: boolean
  onToggle: (ticker: string) => void
  onWatchlist: boolean
  showLocal: boolean
}

function StockRow({ stock, idx, selected, onToggle, onWatchlist, showLocal }: StockRowProps) {
  const changePositive = (stock.priceChangePct ?? 0) >= 0
  const currency = stock.currency || inferCurrencyFromTicker(stock.ticker, stock.exchange) || 'USD'
  const { preferredCurrency, convert } = useCurrency()
  const fmtStockPrice = (v: number | null | undefined) => {
    if (v == null) return '-'
    if (showLocal) return formatPrice(v, currency)
    const converted = convert(v, currency)
    return converted != null ? formatPrice(converted, preferredCurrency) : formatPrice(v, currency)
  }
  const checkboxCellRef = useRef<HTMLTableCellElement>(null)
  const symbolCellRef = useRef<HTMLTableCellElement>(null)

  const rowBg = selected
    ? 'var(--color-primary-bg)'
    : idx % 2 === 0 ? 'var(--bg-surface)' : 'var(--bg-surface-subtle)'

  const setStickyBg = (bg: string) => {
    if (checkboxCellRef.current) checkboxCellRef.current.style.backgroundColor = bg
    if (symbolCellRef.current) symbolCellRef.current.style.backgroundColor = bg
  }

  const cell = (content: React.ReactNode, align: 'left' | 'right' = 'right', style?: React.CSSProperties) => (
    <td style={{
      padding: '9px 12px',
      textAlign: align,
      color: 'var(--text-secondary)',
      whiteSpace: 'nowrap',
      ...style,
    }}>
      {content}
    </td>
  )

  return (
    <tr
      style={{ backgroundColor: rowBg, transition: 'background-color 0.1s', cursor: 'pointer' }}
      onClick={() => onToggle(stock.ticker)}
      onMouseEnter={(e) => {
        if (!selected) {
          e.currentTarget.style.backgroundColor = 'var(--bg-hover)'
          setStickyBg('var(--bg-hover)')
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = rowBg
        setStickyBg(rowBg)
      }}
    >
      {/* Checkbox */}
      <td
        ref={checkboxCellRef}
        style={{
          padding: '9px 12px',
          textAlign: 'center',
          whiteSpace: 'nowrap',
          position: 'sticky',
          left: 0,
          zIndex: 1,
          backgroundColor: rowBg,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <input
          type="checkbox"
          checked={selected}
          onChange={() => onToggle(stock.ticker)}
          style={{ cursor: 'pointer', width: '15px', height: '15px', accentColor: 'var(--color-primary)' }}
        />
      </td>

      {/* Symbol */}
      <td
        ref={symbolCellRef}
        style={{
          padding: '9px 12px',
          textAlign: 'left',
          whiteSpace: 'nowrap',
          position: 'sticky',
          left: 40,
          zIndex: 1,
          backgroundColor: rowBg,
          boxShadow: '2px 0 6px -2px rgba(0,0,0,0.08)',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <Link
          href={`/ticker?ticker=${stock.ticker}`}
          style={{
            fontWeight: '600',
            fontSize: '13px',
            color: 'var(--color-primary)',
            textDecoration: 'none',
            fontFamily: 'monospace',
          }}
        >
          {stock.ticker}
        </Link>
        {onWatchlist && (
          <span title="On watchlist" style={{ marginLeft: '5px', fontSize: '10px', color: '#16a34a' }}>★</span>
        )}
      </td>

      {/* Company name */}
      <td style={{
        padding: '9px 12px',
        textAlign: 'left',
        color: 'var(--text-primary)',
        maxWidth: '200px',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}>
        {stock.companyName}
      </td>

      {/* Price */}
      {cell(
        <span style={{ fontWeight: '500', fontFamily: 'monospace' }}>
          {fmtStockPrice(stock.price)}
        </span>
      )}

      {/* Change % */}
      {cell(
        stock.priceChangePct != null ? (
          <span style={{
            color: changePositive ? '#16a34a' : '#dc2626',
            fontWeight: '500',
          }}>
            {changePositive ? '+' : ''}{stock.priceChangePct.toFixed(2)}%
          </span>
        ) : '-'
      )}

      {/* Market Cap */}
      {cell(
        <span style={{ fontFamily: 'monospace' }}>
          {stock.marketCap != null ? formatLargeNumber(stock.marketCap, currency) : '-'}
        </span>
      )}

      {/* P/E */}
      {cell(<RatioCell value={stock.peRatio} />)}

      {/* Fwd P/E */}
      {cell(<RatioCell value={stock.forwardPE} />)}

      {/* P/B */}
      {cell(<RatioCell value={stock.pbRatio} />)}

      {/* P/S */}
      {cell(<RatioCell value={stock.psRatio} />)}

      {/* EV/EBITDA */}
      {cell(<RatioCell value={stock.evToEbitda} />)}

      {/* Dividend Yield */}
      {cell(
        stock.dividendYield != null && stock.dividendYield > 0
          ? <span style={{ color: '#16a34a' }}>{stock.dividendYield.toFixed(2)}%</span>
          : <span style={{ color: 'var(--text-subtle)' }}>—</span>
      )}

      {/* EPS */}
      {cell(
        stock.eps != null
          ? <span style={{ fontFamily: 'monospace' }}>{fmtStockPrice(stock.eps)}</span>
          : '-'
      )}

      {/* Beta */}
      {cell(
        stock.beta != null
          ? <span style={{
              color: Math.abs(stock.beta) > 1.5 ? '#d97706' : 'var(--text-secondary)',
              fontFamily: 'monospace',
            }}>
              {stock.beta.toFixed(2)}
            </span>
          : '-'
      )}

      {/* 52W High */}
      {cell(
        stock.week52High != null
          ? <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>{fmtStockPrice(stock.week52High)}</span>
          : '-'
      )}

      {/* 52W Low */}
      {cell(
        stock.week52Low != null
          ? <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>{fmtStockPrice(stock.week52Low)}</span>
          : '-'
      )}

      {/* Volume */}
      {cell(
        <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>
          {formatVolume(stock.volume)}
        </span>
      )}

      {/* Sector */}
      <td style={{ padding: '9px 12px', textAlign: 'left', whiteSpace: 'nowrap' }}>
        {stock.sector ? (
          <span style={{
            fontSize: '11px',
            padding: '2px 7px',
            borderRadius: '10px',
            backgroundColor: 'var(--bg-hover)',
            color: 'var(--text-muted)',
          }}>
            {stock.sector}
          </span>
        ) : '-'}
      </td>
    </tr>
  )
}

// ─── Filter Modal ─────────────────────────────────────────────────────────────

interface FilterModalProps {
  filters: FilterState
  onChange: (f: FilterState) => void
  onClose: () => void
  onClear: () => void
  activeCount: number
}

const FILTER_GROUPS: {
  label: string
  rows: { key: keyof FilterState; label: string; unit?: string; placeholder?: string }[]
}[] = [
  {
    label: 'Valuation',
    rows: [
      { key: 'peRatio',    label: 'P/E Ratio',    placeholder: 'e.g. 15' },
      { key: 'forwardPE',  label: 'Forward P/E',  placeholder: 'e.g. 12' },
      { key: 'pbRatio',    label: 'P/B Ratio',    placeholder: 'e.g. 2' },
      { key: 'psRatio',    label: 'P/S Ratio',    placeholder: 'e.g. 3' },
      { key: 'evToEbitda', label: 'EV / EBITDA',  placeholder: 'e.g. 10' },
    ],
  },
  {
    label: 'Income',
    rows: [
      { key: 'dividendYield', label: 'Dividend Yield', unit: '%',  placeholder: 'e.g. 2' },
      { key: 'eps',           label: 'EPS',            unit: '$',  placeholder: 'e.g. 5' },
    ],
  },
  {
    label: 'Size & Price',
    rows: [
      { key: 'marketCap', label: 'Market Cap', unit: '$B', placeholder: 'e.g. 100' },
      { key: 'price',     label: 'Price',      unit: '$',  placeholder: 'e.g. 50' },
    ],
  },
  {
    label: 'Risk & Volume',
    rows: [
      { key: 'beta',   label: 'Beta',   placeholder: 'e.g. 0.8' },
      { key: 'volume', label: 'Volume', unit: 'M shares', placeholder: 'e.g. 1' },
    ],
  },
]

function FilterModal({ filters, onChange, onClose, onClear, activeCount }: FilterModalProps) {
  const set = (key: keyof FilterState, side: 'min' | 'max', val: string) => {
    onChange({ ...filters, [key]: { ...filters[key], [side]: val } })
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        backgroundColor: 'rgba(0,0,0,0.45)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '16px',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: '12px',
          width: '100%',
          maxWidth: '560px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '18px 20px 14px',
          borderBottom: '1px solid var(--border-default)',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>
              Advanced Filters
            </span>
            {activeCount > 0 && (
              <span style={{
                backgroundColor: 'var(--color-primary)',
                color: '#fff',
                borderRadius: '10px',
                fontSize: '11px',
                padding: '2px 8px',
                fontWeight: '700',
              }}>
                {activeCount} active
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {activeCount > 0 && (
              <button
                onClick={onClear}
                style={{
                  padding: '4px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-input)',
                  backgroundColor: 'transparent',
                  color: 'var(--text-muted)',
                  fontSize: '12px',
                  cursor: 'pointer',
                }}
              >
                Clear all
              </button>
            )}
            <button
              onClick={onClose}
              style={{
                width: '28px', height: '28px',
                borderRadius: '6px',
                border: 'none',
                backgroundColor: 'var(--bg-hover)',
                color: 'var(--text-muted)',
                fontSize: '16px',
                cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              ×
            </button>
          </div>
        </div>

        {/* Column labels */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 120px 120px',
          gap: '8px',
          padding: '10px 20px 4px',
          flexShrink: 0,
        }}>
          <div />
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600', textAlign: 'center' }}>MIN</span>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600', textAlign: 'center' }}>MAX</span>
        </div>

        {/* Scrollable filter body */}
        <div style={{ overflowY: 'auto', padding: '0 20px 20px', flexGrow: 1 }}>
          {FILTER_GROUPS.map((group, gi) => (
            <div key={gi} style={{ marginBottom: '20px' }}>
              <div style={{
                fontSize: '11px',
                fontWeight: '700',
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                marginBottom: '8px',
                paddingTop: gi > 0 ? '12px' : '8px',
                borderTop: gi > 0 ? '1px solid var(--border-default)' : 'none',
              }}>
                {group.label}
              </div>
              {group.rows.map(({ key, label, unit, placeholder }) => (
                <div
                  key={key}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 120px 120px',
                    gap: '8px',
                    alignItems: 'center',
                    marginBottom: '6px',
                  }}
                >
                  <label style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                    {label}
                    {unit && <span style={{ color: 'var(--text-muted)', fontSize: '11px', marginLeft: '4px' }}>{unit}</span>}
                  </label>
                  {(['min', 'max'] as const).map((side) => (
                    <input
                      key={side}
                      type="number"
                      value={filters[key][side]}
                      onChange={(e) => set(key, side, e.target.value)}
                      placeholder={side === 'min' ? (placeholder || '—') : '—'}
                      style={{
                        padding: '5px 8px',
                        borderRadius: '6px',
                        border: `1px solid ${filters[key][side] ? 'var(--color-primary)' : 'var(--border-input)'}`,
                        backgroundColor: 'var(--bg-surface)',
                        color: 'var(--text-primary)',
                        fontSize: '13px',
                        width: '100%',
                        boxSizing: 'border-box',
                        outline: 'none',
                      }}
                    />
                  ))}
                </div>
              ))}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div style={{
          padding: '12px 20px',
          borderTop: '1px solid var(--border-default)',
          flexShrink: 0,
          display: 'flex',
          justifyContent: 'flex-end',
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 24px',
              borderRadius: '7px',
              border: 'none',
              backgroundColor: 'var(--color-primary)',
              color: '#fff',
              fontSize: '14px',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}

function RatioCell({ value }: { value?: number | null }) {
  if (value == null || isNaN(value) || !isFinite(value) || value <= 0) {
    return <span style={{ color: 'var(--text-subtle)' }}>—</span>
  }
  const isHigh = value > 40
  const isLow = value < 10
  return (
    <span style={{
      fontFamily: 'monospace',
      color: isHigh ? '#d97706' : isLow ? '#16a34a' : 'var(--text-secondary)',
    }}>
      {value.toFixed(1)}
    </span>
  )
}
