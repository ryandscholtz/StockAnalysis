'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/AuthProvider'
import { useCurrency } from '@/lib/useCurrency'
import { formatPrice, inferCurrencyFromTicker } from '@/lib/currency'
import { stockApi } from '@/lib/api'
import { BuyListItem } from '@/lib/buyList'

type SortKey = 'name' | 'price' | 'fair_value' | 'margin' | 'quantity' | 'total_cost' | 'total_fv'
type SortDir = 'asc' | 'desc'

const isPrivate = (ticker: string) => ticker.startsWith('PRIVATE#')
const displayTicker = (ticker: string) => isPrivate(ticker) ? ticker.slice('PRIVATE#'.length) : ticker

const getRecommendationColor = (rec?: string) => {
  switch (rec) {
    case 'Strong Buy': return '#10b981'
    case 'Buy':        return '#3b82f6'
    case 'Hold':       return '#f59e0b'
    case 'Reduce':     return '#f97316'
    case 'Avoid':      return '#ef4444'
    default:           return '#6b7280'
  }
}

function SortHeader({
  label, sortKey, current, dir, onClick, align = 'right'
}: {
  label: string; sortKey: SortKey; current: SortKey; dir: SortDir; onClick: (k: SortKey) => void; align?: 'left' | 'right'
}) {
  const active = current === sortKey
  return (
    <th
      onClick={() => onClick(sortKey)}
      style={{
        padding: '10px 12px',
        textAlign: align,
        fontSize: '12px',
        fontWeight: '600',
        color: active ? 'var(--color-primary)' : 'var(--text-muted)',
        cursor: 'pointer',
        userSelect: 'none',
        whiteSpace: 'nowrap',
        borderBottom: '2px solid var(--border-default)',
        backgroundColor: active ? 'var(--color-primary-bg)' : 'transparent',
      }}
    >
      {label} {active ? (dir === 'asc' ? '↑' : '↓') : ''}
    </th>
  )
}

export default function BuyListPage() {
  const router = useRouter()
  const { isAuthenticated, loading: authLoading } = useAuth()
  const { preferredCurrency, convert, prefetchRates } = useCurrency()

  const [items, setItems] = useState<BuyListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedTickers, setSelectedTickers] = useState<Set<string>>(new Set())
  const [sortKey, setSortKey] = useState<SortKey>('name')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [confirmRemoveOpen, setConfirmRemoveOpen] = useState(false)
  const [editingQty, setEditingQty] = useState<Record<string, string>>({})
  const [savingQty, setSavingQty] = useState<Set<string>>(new Set())

  // Budget allocator state
  const [budget, setBudget] = useState('')
  const [allocating, setAllocating] = useState(false)
  const [allocateError, setAllocateError] = useState('')

  const loadBuyList = useCallback(async () => {
    try {
      setLoading(true)
      setError('')
      const { items } = await stockApi.getBuyList()
      setItems(items)
      setEditingQty({})
    } catch (err: any) {
      setError(err?.message || 'Failed to load buy list')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!authLoading && isAuthenticated) loadBuyList()
  }, [isAuthenticated, authLoading, loadBuyList])

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.replace('/')
  }, [isAuthenticated, authLoading, router])

  useEffect(() => {
    if (items.length > 0) {
      const currencies = items.map(i => i.currency || inferCurrencyFromTicker(i.ticker, i.exchange) || 'USD')
      prefetchRates(currencies, preferredCurrency)
    }
  }, [items, preferredCurrency, prefetchRates])

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir(key === 'name' ? 'asc' : 'desc') }
  }

  const getConvertedPrice = useCallback((price: number | undefined, currency: string) => {
    if (price == null) return undefined
    return convert(price, currency) ?? price
  }, [convert])

  // Effective quantity — uses live editing value if present, otherwise saved value
  const effectiveQty = useCallback((item: BuyListItem): number => {
    const raw = editingQty[item.ticker]
    if (raw !== undefined) return Math.max(0, parseInt(raw) || 0)
    return item.quantity
  }, [editingQty])

  const displayItems = useMemo(() => {
    return [...items].sort((a, b) => {
      const aCur = a.currency || inferCurrencyFromTicker(a.ticker, a.exchange) || 'USD'
      const bCur = b.currency || inferCurrencyFromTicker(b.ticker, b.exchange) || 'USD'
      const aPrice = getConvertedPrice(a.current_price, aCur)
      const bPrice = getConvertedPrice(b.current_price, bCur)
      const aFV    = getConvertedPrice(a.fair_value, aCur)
      const bFV    = getConvertedPrice(b.fair_value, bCur)
      const aQty = effectiveQty(a)
      const bQty = effectiveQty(b)

      let aVal: number | string = 0
      let bVal: number | string = 0
      switch (sortKey) {
        case 'name':       aVal = (a.company_name || a.ticker).toLowerCase(); bVal = (b.company_name || b.ticker).toLowerCase(); break
        case 'price':      aVal = aPrice ?? -Infinity; bVal = bPrice ?? -Infinity; break
        case 'fair_value': aVal = aFV ?? -Infinity;    bVal = bFV ?? -Infinity;    break
        case 'margin':     aVal = a.margin_of_safety_pct ?? -Infinity; bVal = b.margin_of_safety_pct ?? -Infinity; break
        case 'quantity':   aVal = aQty; bVal = bQty; break
        case 'total_cost': aVal = (aPrice ?? 0) * aQty; bVal = (bPrice ?? 0) * bQty; break
        case 'total_fv':   aVal = (aFV ?? 0) * aQty;    bVal = (bFV ?? 0) * bQty;    break
      }
      if (typeof aVal === 'string') {
        const cmp = aVal.localeCompare(bVal as string)
        return sortDir === 'asc' ? cmp : -cmp
      }
      return sortDir === 'asc' ? (aVal as number) - (bVal as number) : (bVal as number) - (aVal as number)
    })
  }, [items, sortKey, sortDir, getConvertedPrice, effectiveQty])

  // Totals — use effective (live) quantities
  const totals = useMemo(() => {
    let cost = 0, fv = 0, costAvailable = 0, fvAvailable = 0
    for (const item of items) {
      const cur = item.currency || inferCurrencyFromTicker(item.ticker, item.exchange) || 'USD'
      const price   = getConvertedPrice(item.current_price, cur)
      const fairVal = getConvertedPrice(item.fair_value, cur)
      const qty = effectiveQty(item)
      if (price != null)   { cost += price   * qty; costAvailable++ }
      if (fairVal != null) { fv   += fairVal * qty; fvAvailable++ }
    }
    return { cost, fv, costAvailable, fvAvailable, total: items.length }
  }, [items, getConvertedPrice, effectiveQty])

  const toggleSelect = (ticker: string) => {
    setSelectedTickers(prev => {
      const next = new Set(prev)
      next.has(ticker) ? next.delete(ticker) : next.add(ticker)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedTickers.size === displayItems.length && displayItems.length > 0) setSelectedTickers(new Set())
    else setSelectedTickers(new Set(displayItems.map(i => i.ticker)))
  }

  const removeSelected = async () => {
    const tickers = [...selectedTickers]
    setConfirmRemoveOpen(false)
    await Promise.allSettled(tickers.map(t => stockApi.removeFromBuyList(t)))
    setSelectedTickers(new Set())
    await loadBuyList()
  }

  const handleQuantityChange = (ticker: string, value: string) => {
    setEditingQty(prev => ({ ...prev, [ticker]: value }))
  }

  const commitQuantity = async (ticker: string) => {
    const raw = editingQty[ticker]
    if (raw === undefined) return
    const parsed = parseInt(raw, 10)
    setEditingQty(prev => { const next = { ...prev }; delete next[ticker]; return next })
    if (!isNaN(parsed) && parsed >= 0) {
      setSavingQty(prev => new Set([...prev, ticker]))
      try {
        if (parsed === 0) {
          await stockApi.removeFromBuyList(ticker)
          setSelectedTickers(prev => { const next = new Set(prev); next.delete(ticker); return next })
        } else {
          await stockApi.updateBuyListQuantity(ticker, parsed)
        }
        await loadBuyList()
      } finally {
        setSavingQty(prev => { const next = new Set(prev); next.delete(ticker); return next })
      }
    }
  }

  // Budget allocator
  const handleAllocate = async () => {
    const budgetVal = parseFloat(budget)
    if (isNaN(budgetVal) || budgetVal <= 0) {
      setAllocateError('Please enter a valid budget amount.')
      return
    }
    setAllocateError('')

    // Build price list in preferred currency
    const priced: Array<{ ticker: string; price: number }> = []
    const unpriced: string[] = []
    for (const item of items) {
      const cur = item.currency || inferCurrencyFromTicker(item.ticker, item.exchange) || 'USD'
      const price = getConvertedPrice(item.current_price, cur)
      if (price != null && price > 0) priced.push({ ticker: item.ticker, price })
      else unpriced.push(item.ticker)
    }

    if (priced.length === 0) {
      setAllocateError('No items have price data to allocate.')
      return
    }

    // Check if budget covers at least 1 share of each priced stock
    const minCost = priced.reduce((sum, p) => sum + p.price, 0)
    if (minCost > budgetVal) {
      const missing = formatPrice(minCost - budgetVal, preferredCurrency)
      setAllocateError(
        `Budget too small by ${missing}. Need at least ${formatPrice(minCost, preferredCurrency)} to buy 1 share of each stock.`
      )
      return
    }

    // Greedy even-value allocation
    const quantities: Record<string, number> = {}
    for (const { ticker } of priced) quantities[ticker] = 1
    let remaining = budgetVal - minCost
    const target = budgetVal / priced.length

    let progress = true
    while (progress && remaining > 0) {
      progress = false
      // Pick the stock furthest below its target allocation that we can still afford
      let bestTicker = ''
      let bestDeficit = -Infinity
      for (const { ticker, price } of priced) {
        if (price > remaining) continue
        const deficit = target - quantities[ticker] * price
        if (deficit > bestDeficit) { bestDeficit = deficit; bestTicker = ticker }
      }
      if (bestTicker) {
        const price = priced.find(p => p.ticker === bestTicker)!.price
        quantities[bestTicker]++
        remaining -= price
        progress = true
      }
    }

    // Save all updated quantities
    setAllocating(true)
    try {
      await Promise.all(
        priced.map(({ ticker }) => stockApi.updateBuyListQuantity(ticker, quantities[ticker]))
      )
      await loadBuyList()
    } finally {
      setAllocating(false)
    }
  }

  if (authLoading || (!isAuthenticated && !authLoading)) {
    return <div className="container" style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>
  }

  return (
    <div className="container" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '32px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '6px' }}>Buy List</h1>
        <p style={{ fontSize: '15px', color: 'var(--text-muted)' }}>
          Stocks you intend to buy. Set quantities and track total cost vs fair value.
        </p>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', backgroundColor: 'var(--status-error-bg)', border: '1px solid #ef4444', borderRadius: '6px', color: 'var(--status-error-text)', marginBottom: '20px' }}>
          ⚠️ {error}
        </div>
      )}

      {/* Summary cards */}
      {items.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '24px' }}>
          <div style={{ padding: '16px 20px', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.08)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>Positions</div>
            <div style={{ fontSize: '26px', fontWeight: '700', color: 'var(--text-primary)' }}>{items.length}</div>
          </div>
          <div style={{ padding: '16px 20px', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.08)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>Total Cost ({preferredCurrency})</div>
            <div style={{ fontSize: '22px', fontWeight: '700', color: 'var(--text-primary)' }}>
              {totals.costAvailable > 0 ? formatPrice(totals.cost, preferredCurrency) : '—'}
            </div>
            {totals.costAvailable < totals.total && totals.total > 0 && (
              <div style={{ fontSize: '11px', color: 'var(--text-subtle)', marginTop: '2px' }}>{totals.total - totals.costAvailable} without price data</div>
            )}
          </div>
          <div style={{ padding: '16px 20px', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px', boxShadow: '0 2px 4px rgba(0,0,0,0.08)' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '6px' }}>Total Fair Value ({preferredCurrency})</div>
            <div style={{ fontSize: '22px', fontWeight: '700', color: totals.fv > totals.cost && totals.fvAvailable > 0 ? '#10b981' : totals.fvAvailable > 0 ? '#ef4444' : 'var(--text-primary)' }}>
              {totals.fvAvailable > 0 ? formatPrice(totals.fv, preferredCurrency) : '—'}
            </div>
            {totals.fvAvailable > 0 && totals.costAvailable > 0 && totals.cost > 0 && (
              <div style={{ fontSize: '12px', color: totals.fv > totals.cost ? '#10b981' : '#ef4444', fontWeight: '600', marginTop: '2px' }}>
                {totals.fv > totals.cost ? '+' : ''}{(((totals.fv - totals.cost) / totals.cost) * 100).toFixed(1)}% vs cost
              </div>
            )}
          </div>
        </div>
      )}

      {/* Budget allocator */}
      {items.length > 0 && (
        <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '10px', padding: '16px 20px', marginBottom: '16px', display: 'flex', alignItems: 'flex-start', gap: '12px', flexWrap: 'wrap' }}>
          <div>
            <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)', marginBottom: '6px' }}>
              Buy Budget ({preferredCurrency})
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
              <input
                type="number"
                min="0"
                placeholder={`e.g. 10000`}
                value={budget}
                onChange={(e) => { setBudget(e.target.value); setAllocateError('') }}
                style={{
                  width: '160px', padding: '7px 10px', borderRadius: '6px',
                  border: '1px solid var(--border-input)', backgroundColor: 'var(--bg-surface)',
                  color: 'var(--text-primary)', fontSize: '14px',
                }}
              />
              <button
                onClick={handleAllocate}
                disabled={allocating || !budget || items.length === 0}
                style={{
                  padding: '7px 16px', borderRadius: '6px', border: 'none',
                  backgroundColor: allocating ? '#9ca3af' : '#f59e0b',
                  color: 'white', fontSize: '13px', fontWeight: '600',
                  cursor: allocating || !budget ? 'not-allowed' : 'pointer',
                  whiteSpace: 'nowrap',
                }}
              >
                {allocating ? '⏳ Allocating…' : '⚖️ Allocate to Buy List'}
              </button>
            </div>
          </div>
          {allocateError && (
            <div style={{ alignSelf: 'flex-end', padding: '7px 12px', backgroundColor: 'var(--status-error-bg)', border: '1px solid #ef4444', borderRadius: '6px', color: 'var(--status-error-text)', fontSize: '13px', maxWidth: '420px' }}>
              ⚠️ {allocateError}
            </div>
          )}
        </div>
      )}

      {/* Table */}
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', overflow: 'hidden' }}>
        {/* Toolbar */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 20px', borderBottom: '1px solid var(--border-default)', flexWrap: 'wrap', gap: '10px' }}>
          <h2 style={{ fontSize: '18px', fontWeight: '600', color: 'var(--text-primary)', margin: 0 }}>
            Your Buy List {items.length > 0 && <span style={{ fontSize: '14px', color: 'var(--text-muted)', fontWeight: '400' }}>({items.length} stock{items.length !== 1 ? 's' : ''})</span>}
          </h2>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {selectedTickers.size > 0 && (
              <button
                onClick={() => setConfirmRemoveOpen(true)}
                style={{ padding: '6px 14px', borderRadius: '6px', border: '1px solid #ef4444', backgroundColor: 'transparent', color: '#ef4444', fontSize: '13px', fontWeight: '600', cursor: 'pointer' }}
              >
                🗑 Remove {selectedTickers.size} selected
              </button>
            )}
            <button
              onClick={loadBuyList}
              style={{ padding: '6px 14px', borderRadius: '6px', border: '1px solid var(--border-input)', backgroundColor: 'var(--bg-surface)', color: 'var(--text-secondary)', fontSize: '13px', cursor: 'pointer' }}
            >
              🔄 Refresh
            </button>
          </div>
        </div>

        {loading ? (
          <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <div style={{ width: '32px', height: '32px', border: '3px solid var(--bg-hover)', borderTop: '3px solid var(--color-primary)', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 12px' }} />
            <style>{`@keyframes spin { 0% { transform: rotate(0deg) } 100% { transform: rotate(360deg) } }`}</style>
            Loading buy list…
          </div>
        ) : items.length === 0 ? (
          <div style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: '40px', marginBottom: '12px' }}>🛒</div>
            <p style={{ fontSize: '16px', marginBottom: '8px' }}>Your buy list is empty.</p>
            <p style={{ fontSize: '14px' }}>
              Add stocks from your{' '}
              <button onClick={() => router.push('/watchlist')} style={{ background: 'none', border: 'none', color: 'var(--color-primary)', cursor: 'pointer', fontSize: '14px', fontWeight: '500' }}>Watchlist</button>
              {' '}or{' '}
              <button onClick={() => router.push('/explore')} style={{ background: 'none', border: 'none', color: 'var(--color-primary)', cursor: 'pointer', fontSize: '14px', fontWeight: '500' }}>Explore</button>.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--bg-surface-subtle)' }}>
                  <th style={{ padding: '10px 12px', width: '36px', borderBottom: '2px solid var(--border-default)' }}>
                    <input
                      type="checkbox"
                      checked={displayItems.length > 0 && selectedTickers.size === displayItems.length}
                      ref={(el) => { if (el) el.indeterminate = selectedTickers.size > 0 && selectedTickers.size < displayItems.length }}
                      onChange={toggleSelectAll}
                      style={{ width: '15px', height: '15px', cursor: 'pointer', accentColor: 'var(--color-primary)' }}
                    />
                  </th>
                  <SortHeader label="Company / Ticker" sortKey="name" current={sortKey} dir={sortDir} onClick={handleSort} align="left" />
                  <th style={{ padding: '10px 12px', fontSize: '12px', fontWeight: '600', color: 'var(--text-muted)', textAlign: 'center', whiteSpace: 'nowrap', borderBottom: '2px solid var(--border-default)' }}>Rec.</th>
                  <SortHeader label={`Price (${preferredCurrency})`} sortKey="price" current={sortKey} dir={sortDir} onClick={handleSort} />
                  <SortHeader label={`Fair Value (${preferredCurrency})`} sortKey="fair_value" current={sortKey} dir={sortDir} onClick={handleSort} />
                  <SortHeader label="% Under/Over" sortKey="margin" current={sortKey} dir={sortDir} onClick={handleSort} />
                  <SortHeader label="Quantity" sortKey="quantity" current={sortKey} dir={sortDir} onClick={handleSort} />
                  <SortHeader label={`Total Cost (${preferredCurrency})`} sortKey="total_cost" current={sortKey} dir={sortDir} onClick={handleSort} />
                  <SortHeader label={`Total Fair Value (${preferredCurrency})`} sortKey="total_fv" current={sortKey} dir={sortDir} onClick={handleSort} />
                </tr>
              </thead>
              <tbody>
                {displayItems.map((item, idx) => {
                  const effectiveCurrency = item.currency || inferCurrencyFromTicker(item.ticker, item.exchange) || 'USD'
                  const price   = getConvertedPrice(item.current_price, effectiveCurrency)
                  const fairVal = getConvertedPrice(item.fair_value, effectiveCurrency)
                  const qty = effectiveQty(item)
                  const totalCost = price != null ? price * qty : undefined
                  const totalFV   = fairVal != null ? fairVal * qty : undefined
                  const margin = item.margin_of_safety_pct
                  const isSelected = selectedTickers.has(item.ticker)
                  const qtyEditing = editingQty[item.ticker]
                  const isSaving = savingQty.has(item.ticker)

                  return (
                    <tr
                      key={item.ticker}
                      style={{
                        backgroundColor: isSelected ? 'var(--color-primary-bg)' : idx % 2 === 0 ? 'transparent' : 'var(--bg-surface-subtle)',
                        borderBottom: '1px solid var(--border-default)',
                        transition: 'background-color 0.1s',
                        opacity: isSaving ? 0.6 : 1,
                      }}
                      onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.backgroundColor = 'var(--bg-hover)' }}
                      onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.backgroundColor = idx % 2 === 0 ? 'transparent' : 'var(--bg-surface-subtle)' }}
                    >
                      <td style={{ padding: '12px', textAlign: 'center' }}>
                        <input type="checkbox" checked={isSelected} onChange={() => toggleSelect(item.ticker)}
                          style={{ width: '15px', height: '15px', cursor: 'pointer', accentColor: 'var(--color-primary)' }} />
                      </td>

                      <td style={{ padding: '12px', cursor: 'pointer' }} onClick={() => router.push(`/ticker?ticker=${item.ticker}`)}>
                        <div style={{ fontWeight: '600', color: 'var(--text-primary)', fontSize: '14px' }}>{item.company_name || displayTicker(item.ticker)}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {displayTicker(item.ticker)}{item.exchange && <span style={{ marginLeft: '4px' }}>· {item.exchange}</span>}
                        </div>
                      </td>

                      <td style={{ padding: '12px', textAlign: 'center' }}>
                        {item.recommendation ? (
                          <span style={{ padding: '3px 8px', borderRadius: '10px', fontSize: '11px', fontWeight: '600', color: 'white', backgroundColor: getRecommendationColor(item.recommendation), whiteSpace: 'nowrap' }}>
                            {item.recommendation}
                          </span>
                        ) : <span style={{ color: 'var(--text-subtle)', fontSize: '12px' }}>—</span>}
                      </td>

                      <td style={{ padding: '12px', textAlign: 'right', fontWeight: '500', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
                        {price != null ? formatPrice(price, preferredCurrency) : <span style={{ color: 'var(--text-subtle)' }}>—</span>}
                      </td>

                      <td style={{ padding: '12px', textAlign: 'right', fontWeight: '500', whiteSpace: 'nowrap', color: fairVal != null && price != null ? (fairVal > price ? '#10b981' : '#ef4444') : 'var(--text-primary)' }}>
                        {fairVal != null ? formatPrice(fairVal, preferredCurrency) : <span style={{ color: 'var(--text-subtle)' }}>—</span>}
                      </td>

                      <td style={{ padding: '12px', textAlign: 'right', whiteSpace: 'nowrap' }}>
                        {margin != null && !isNaN(margin) ? (
                          <span style={{ fontWeight: '600', fontSize: '13px', color: margin > 0 ? '#059669' : '#dc2626' }}>
                            {margin > 0 ? '+' : ''}{margin.toFixed(1)}%
                          </span>
                        ) : <span style={{ color: 'var(--text-subtle)' }}>—</span>}
                      </td>

                      <td style={{ padding: '8px 12px', textAlign: 'right' }}>
                        <input
                          type="number"
                          min="0"
                          value={qtyEditing !== undefined ? qtyEditing : item.quantity}
                          onChange={(e) => handleQuantityChange(item.ticker, e.target.value)}
                          onBlur={() => commitQuantity(item.ticker)}
                          onKeyDown={(e) => { if (e.key === 'Enter') e.currentTarget.blur() }}
                          onClick={(e) => e.stopPropagation()}
                          disabled={isSaving}
                          style={{
                            width: '72px', padding: '5px 8px', borderRadius: '6px',
                            border: '1px solid var(--border-input)', backgroundColor: 'var(--bg-surface)',
                            color: 'var(--text-primary)', fontSize: '14px', textAlign: 'right', fontWeight: '500',
                          }}
                        />
                      </td>

                      <td style={{ padding: '12px', textAlign: 'right', fontWeight: '600', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>
                        {totalCost != null ? formatPrice(totalCost, preferredCurrency) : <span style={{ color: 'var(--text-subtle)' }}>—</span>}
                      </td>

                      <td style={{ padding: '12px', textAlign: 'right', fontWeight: '600', whiteSpace: 'nowrap', color: totalFV != null && totalCost != null ? (totalFV > totalCost ? '#10b981' : '#ef4444') : 'var(--text-primary)' }}>
                        {totalFV != null ? formatPrice(totalFV, preferredCurrency) : <span style={{ color: 'var(--text-subtle)' }}>—</span>}
                      </td>
                    </tr>
                  )
                })}
              </tbody>

              <tfoot>
                <tr style={{ borderTop: '2px solid var(--border-default)', backgroundColor: 'var(--bg-surface-subtle)' }}>
                  <td colSpan={7} style={{ padding: '12px', fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)', textAlign: 'right' }}>
                    Total ({items.length} position{items.length !== 1 ? 's' : ''})
                  </td>
                  <td style={{ padding: '12px', textAlign: 'right', fontWeight: '700', color: 'var(--text-primary)', whiteSpace: 'nowrap', fontSize: '14px' }}>
                    {totals.costAvailable > 0 ? formatPrice(totals.cost, preferredCurrency) : '—'}
                  </td>
                  <td style={{ padding: '12px', textAlign: 'right', fontWeight: '700', whiteSpace: 'nowrap', fontSize: '14px', color: totals.fv > totals.cost && totals.fvAvailable > 0 ? '#10b981' : totals.fvAvailable > 0 ? '#ef4444' : 'var(--text-primary)' }}>
                    {totals.fvAvailable > 0 ? formatPrice(totals.fv, preferredCurrency) : '—'}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>

      {/* Confirm remove modal */}
      {confirmRemoveOpen && (
        <div onClick={() => setConfirmRemoveOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 1000, backgroundColor: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
          <div onClick={(e) => e.stopPropagation()} style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '12px', width: '100%', maxWidth: '400px', padding: '28px 24px 20px', boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
            <div style={{ fontSize: '20px', marginBottom: '8px' }}>🗑 Remove from buy list</div>
            <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6', margin: '0 0 20px 0' }}>
              Remove <strong>{selectedTickers.size} stock{selectedTickers.size !== 1 ? 's' : ''}</strong> from your buy list?
              {selectedTickers.size <= 5 && (
                <span style={{ display: 'block', marginTop: '8px', color: 'var(--text-muted)', fontSize: '13px' }}>{[...selectedTickers].join(', ')}</span>
              )}
            </p>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button onClick={() => setConfirmRemoveOpen(false)} style={{ padding: '8px 18px', borderRadius: '7px', border: '1px solid var(--border-input)', backgroundColor: 'transparent', color: 'var(--text-secondary)', fontSize: '14px', cursor: 'pointer', fontWeight: '500' }}>Cancel</button>
              <button onClick={removeSelected} style={{ padding: '8px 18px', borderRadius: '7px', border: 'none', backgroundColor: '#ef4444', color: '#fff', fontSize: '14px', cursor: 'pointer', fontWeight: '600' }}>Remove</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
