'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import Link from 'next/link'
import { stockApi, ExploreMarket, ExploreStock } from '@/lib/api'
import { useAuth } from '@/components/AuthProvider'
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

interface WatchlistSet {
  tickers: Set<string>
  adding: Set<string>
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
    <td style={{ padding: '10px 12px' }}>
      <div style={{ height: '28px', width: '120px', borderRadius: '6px', backgroundColor: 'var(--bg-hover)', animation: 'pulse 1.4s ease-in-out infinite' }} />
    </td>
  </tr>
)

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function ExplorePage() {
  const { isAuthenticated } = useAuth()

  const [markets, setMarkets] = useState<ExploreMarket[]>([])
  const [selectedMarket, setSelectedMarket] = useState<string>('SP500')
  const [stocks, setStocks] = useState<ExploreStock[]>([])
  const [loading, setLoading] = useState(false)
  const [marketsLoading, setMarketsLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [cached, setCached] = useState(false)
  const [cacheAge, setCacheAge] = useState(0)

  const [sortField, setSortField] = useState<SortField>('marketCap')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const [watchlist, setWatchlist] = useState<WatchlistSet>({ tickers: new Set(), adding: new Set() })
  const [addedMessage, setAddedMessage] = useState<string>('')

  const [sectorFilter, setSectorFilter] = useState<string>('All')

  // Load available markets once
  useEffect(() => {
    stockApi.getExploreMarkets()
      .then((res) => setMarkets(res.markets))
      .catch(() => {/* fail silently, markets won't be shown */})
      .finally(() => setMarketsLoading(false))
  }, [])

  // Load watchlist if authenticated
  useEffect(() => {
    if (!isAuthenticated) return
    stockApi.getWatchlist()
      .then((res) => {
        const tickers = new Set<string>((res?.items || []).map((i: any) => i.ticker.toUpperCase()))
        setWatchlist((prev) => ({ ...prev, tickers }))
      })
      .catch(() => {/* ignore */})
  }, [isAuthenticated])

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

  // Filtered + sorted stocks
  const displayStocks = useMemo(() => {
    let filtered = sectorFilter === 'All' ? stocks : stocks.filter((s) => s.sector === sectorFilter)
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
  }, [stocks, sortField, sortDir, sectorFilter])

  // Add to watchlist
  const handleAddToWatchlist = async (stock: ExploreStock) => {
    if (!isAuthenticated) return
    const ticker = stock.ticker.toUpperCase()
    setWatchlist((prev) => ({ ...prev, adding: new Set([...prev.adding, ticker]) }))
    try {
      await stockApi.addToWatchlist(ticker, stock.companyName, stock.exchange)
      setWatchlist((prev) => ({
        tickers: new Set([...prev.tickers, ticker]),
        adding: new Set([...prev.adding].filter((t) => t !== ticker)),
      }))
      setAddedMessage(`${ticker} added to watchlist`)
      setTimeout(() => setAddedMessage(''), 3000)
    } catch {
      setWatchlist((prev) => ({
        ...prev,
        adding: new Set([...prev.adding].filter((t) => t !== ticker)),
      }))
    }
  }

  const currentMarket = markets.find((m) => m.id === selectedMarket)

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

      {/* Market selector */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '8px',
        marginBottom: '20px',
      }}>
        {marketsLoading
          ? Array.from({ length: 6 }).map((_, i) => (
              <div key={i} style={{
                height: '34px', width: '100px', borderRadius: '6px',
                backgroundColor: 'var(--bg-hover)', animation: 'pulse 1.4s ease-in-out infinite',
              }} />
            ))
          : markets.map((m) => (
              <button
                key={m.id}
                onClick={() => setSelectedMarket(m.id)}
                style={{
                  padding: '6px 14px',
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
                <span style={{
                  marginLeft: '6px',
                  fontSize: '11px',
                  opacity: 0.6,
                }}>
                  {m.ticker_count}
                </span>
              </button>
            ))}
      </div>

      {/* Market description + controls row */}
      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: '12px',
        marginBottom: '16px',
      }}>
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

      {/* Watchlist feedback toast */}
      {addedMessage && (
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
          ✓ {addedMessage}
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

      {/* Table container — horizontal scroll on mobile */}
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
                    left: colIdx === 0 ? 0 : undefined,
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
              {/* Action column — sticky right */}
              <th style={{
                padding: '10px 12px',
                textAlign: 'right',
                fontWeight: '600',
                fontSize: '12px',
                color: 'var(--text-muted)',
                borderBottom: '2px solid var(--border-default)',
                position: 'sticky',
                top: 0,
                right: 0,
                backgroundColor: 'var(--bg-surface-subtle)',
                zIndex: 3,
                minWidth: 140,
                whiteSpace: 'nowrap',
                boxShadow: '-2px 0 6px -2px rgba(0,0,0,0.08)',
              }}>
                Watchlist
              </th>
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
                    isAuthenticated={isAuthenticated}
                    onWatchlist={watchlist.tickers.has(stock.ticker.toUpperCase())}
                    adding={watchlist.adding.has(stock.ticker.toUpperCase())}
                    onAdd={handleAddToWatchlist}
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
  isAuthenticated: boolean
  onWatchlist: boolean
  adding: boolean
  onAdd: (stock: ExploreStock) => void
}

function StockRow({ stock, idx, isAuthenticated, onWatchlist, adding, onAdd }: StockRowProps) {
  const changePositive = (stock.priceChangePct ?? 0) >= 0
  const currency = stock.currency || 'USD'

  const rowBg = idx % 2 === 0 ? 'var(--bg-surface)' : 'var(--bg-surface-subtle)'
  const [hover, setHover] = useState(false)
  const stickyBg = hover ? 'var(--bg-hover)' : rowBg

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
      style={{ backgroundColor: stickyBg, transition: 'background-color 0.1s' }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {/* Symbol — sticky left */}
      <td style={{
        padding: '9px 12px',
        textAlign: 'left',
        whiteSpace: 'nowrap',
        position: 'sticky',
        left: 0,
        backgroundColor: stickyBg,
        zIndex: 1,
        boxShadow: '2px 0 6px -2px rgba(0,0,0,0.08)',
      }}>
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
      {cell(
        <RatioCell value={stock.peRatio} />
      )}

      {/* Fwd P/E */}
      {cell(
        <RatioCell value={stock.forwardPE} />
      )}

      {/* P/B */}
      {cell(
        <RatioCell value={stock.pbRatio} />
      )}

      {/* P/S */}
      {cell(
        <RatioCell value={stock.psRatio} />
      )}

      {/* EV/EBITDA */}
      {cell(
        <RatioCell value={stock.evToEbitda} />
      )}

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

      {/* Add to Watchlist — sticky right */}
      <td style={{
        padding: '9px 12px',
        textAlign: 'right',
        whiteSpace: 'nowrap',
        position: 'sticky',
        right: 0,
        backgroundColor: stickyBg,
        zIndex: 1,
        boxShadow: '-2px 0 6px -2px rgba(0,0,0,0.08)',
      }}>
        {!isAuthenticated ? (
          <Link
            href="/auth/signin"
            style={{
              fontSize: '12px',
              color: 'var(--text-subtle)',
              textDecoration: 'none',
              padding: '4px 10px',
              border: '1px solid var(--border-default)',
              borderRadius: '5px',
            }}
          >
            Sign in
          </Link>
        ) : onWatchlist ? (
          <span style={{
            fontSize: '12px',
            padding: '4px 10px',
            border: '1px solid #86efac',
            borderRadius: '5px',
            backgroundColor: 'var(--status-success-bg, #f0fdf4)',
            color: '#16a34a',
            fontWeight: '500',
          }}>
            ✓ Watchlist
          </span>
        ) : (
          <button
            onClick={() => onAdd(stock)}
            disabled={adding}
            style={{
              fontSize: '12px',
              padding: '4px 10px',
              border: '1px solid var(--color-primary)',
              borderRadius: '5px',
              backgroundColor: adding ? 'var(--bg-hover)' : 'transparent',
              color: adding ? 'var(--text-muted)' : 'var(--color-primary)',
              cursor: adding ? 'not-allowed' : 'pointer',
              fontWeight: '500',
              transition: 'all 0.15s',
              whiteSpace: 'nowrap',
            }}
            onMouseEnter={(e) => {
              if (!adding) {
                e.currentTarget.style.backgroundColor = 'var(--color-primary)'
                e.currentTarget.style.color = 'white'
              }
            }}
            onMouseLeave={(e) => {
              if (!adding) {
                e.currentTarget.style.backgroundColor = 'transparent'
                e.currentTarget.style.color = 'var(--color-primary)'
              }
            }}
          >
            {adding ? '…' : '+ Watchlist'}
          </button>
        )}
      </td>
    </tr>
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
