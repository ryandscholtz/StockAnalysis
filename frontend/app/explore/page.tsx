'use client'

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import Link from 'next/link'
import { stockApi, ExploreMarket, ExploreStock } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'
import { useSessionState } from '@/lib/useSessionState'
import {
  formatPrice,
  formatLargeNumber,
  formatPercent,
  formatNumber,
  formatRatio,
} from '@/lib/currency'

// ─── Types ────────────────────────────────────────────────────────────────────

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
}

function StockRow({ stock, idx, selected, onToggle, onWatchlist }: StockRowProps) {
  const changePositive = (stock.priceChangePct ?? 0) >= 0
  const currency = stock.currency || 'USD'
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
          {stock.price != null ? formatPrice(stock.price, currency) : '-'}
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
          ? <span style={{ fontFamily: 'monospace' }}>{formatPrice(stock.eps, currency)}</span>
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
          ? <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>{formatPrice(stock.week52High, currency)}</span>
          : '-'
      )}

      {/* 52W Low */}
      {cell(
        stock.week52Low != null
          ? <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>{formatPrice(stock.week52Low, currency)}</span>
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
