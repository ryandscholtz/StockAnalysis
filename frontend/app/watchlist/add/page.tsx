'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { stockApi, SearchResult } from '@/lib/api'
import { searchTickers } from '@/lib/enhanced-search'
import { RequireAuth } from '@/components/AuthProvider'

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------
const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 14px',
  fontSize: '15px',
  border: '1px solid var(--border-input)',
  borderRadius: '6px',
  outline: 'none',
  backgroundColor: 'var(--bg-surface)',
  color: 'var(--text-primary)',
  boxSizing: 'border-box',
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: '13px',
  fontWeight: '600',
  color: 'var(--text-secondary)',
  marginBottom: '6px',
}

// ---------------------------------------------------------------------------
// Public company search (existing flow)
// ---------------------------------------------------------------------------
function PublicCompanyForm({ onCancel }: { onCancel: () => void }) {
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState('')
  const [suggestions, setSuggestions] = useState<SearchResult[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current)
    if (searchQuery.trim().length < 1) {
      setSuggestions([]); setShowSuggestions(false); setSearchLoading(false); return
    }
    setSearchLoading(true)
    searchTimeoutRef.current = setTimeout(async () => {
      try {
        const localResults: SearchResult[] = searchTickers(searchQuery.trim(), 10).map(l => ({
          ticker: l.ticker, companyName: l.companyName, exchange: l.exchange,
        }))
        let finalResults = localResults
        try {
          const apiResults = await stockApi.searchTickers(searchQuery.trim())
          const safeApi = Array.isArray(apiResults) ? apiResults : []
          if (safeApi.length > 0) {
            const localNotInApi = localResults.filter(l => !safeApi.some(a => a.ticker === l.ticker))
            finalResults = [...safeApi, ...localNotInApi].slice(0, 10)
          }
        } catch { /* use local results */ }
        setSuggestions(finalResults)
        setShowSuggestions(finalResults.length > 0)
        setSelectedIndex(-1)
      } catch {
        setSuggestions([]); setShowSuggestions(false)
      } finally {
        setSearchLoading(false)
      }
    }, 300)
    return () => { if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current) }
  }, [searchQuery])

  const handleSelect = async (suggestion: SearchResult) => {
    setSearchQuery(suggestion.ticker || '')
    setShowSuggestions(false)
    setAdding(true)
    setError('')
    try {
      const result = await stockApi.addToWatchlist(suggestion.ticker, suggestion.companyName, suggestion.exchange)
      if (result.success) {
        router.push(`/ticker?symbol=${encodeURIComponent(suggestion.ticker)}`)
      } else {
        setError(result.message || 'Failed to add to watchlist')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to add to watchlist')
    } finally {
      setAdding(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelectedIndex(p => p < suggestions.length - 1 ? p + 1 : p) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSelectedIndex(p => p > 0 ? p - 1 : -1) }
    else if (e.key === 'Enter' && selectedIndex >= 0 && suggestions[selectedIndex]) { e.preventDefault(); handleSelect(suggestions[selectedIndex]) }
    else if (e.key === 'Escape') setShowSuggestions(false)
  }

  return (
    <div>
      {error && (
        <div style={{ padding: '10px 14px', backgroundColor: 'var(--status-error-bg)', border: '1px solid #ef4444', borderRadius: '6px', color: 'var(--status-error-text)', marginBottom: '16px', fontSize: '14px' }}>
          {error}
        </div>
      )}

      <div style={{ position: 'relative', marginBottom: '20px' }}>
        <input
          type="text"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={e => { e.currentTarget.style.borderColor = 'var(--color-primary)'; setShowSuggestions(suggestions.length > 0) }}
          onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-input)'; setTimeout(() => setShowSuggestions(false), 200) }}
          placeholder="Search for a stock ticker or company name..."
          disabled={adding}
          style={{ ...inputStyle, padding: '12px 16px', fontSize: '16px' }}
        />
        {searchLoading && (
          <div style={{ position: 'absolute', right: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)', fontSize: '13px' }}>
            Searching...
          </div>
        )}
        {showSuggestions && suggestions.length > 0 && (
          <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, marginTop: '4px', backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '6px', boxShadow: '0 4px 12px rgba(0,0,0,0.15)', maxHeight: '300px', overflowY: 'auto', zIndex: 1000 }}>
            {suggestions.map((s, i) => (
              <div
                key={`${s.ticker}-${i}`}
                onMouseDown={e => { e.preventDefault(); handleSelect(s) }}
                style={{ padding: '10px 14px', cursor: 'pointer', backgroundColor: i === selectedIndex ? 'var(--color-primary-bg)' : 'var(--bg-surface)', borderBottom: i < suggestions.length - 1 ? '1px solid var(--border-default)' : 'none' }}
                onMouseEnter={e => { if (i !== selectedIndex) e.currentTarget.style.backgroundColor = 'var(--bg-surface-subtle)' }}
                onMouseLeave={e => { if (i !== selectedIndex) e.currentTarget.style.backgroundColor = 'var(--bg-surface)' }}
              >
                <div style={{ fontWeight: '600', color: 'var(--text-primary)', fontSize: '14px' }}>
                  {s.ticker}
                  {s.exchange && <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: '400', marginLeft: '8px' }}>({s.exchange})</span>}
                </div>
                {s.companyName && <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>{s.companyName}</div>}
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: '10px' }}>
        <button onClick={onCancel} disabled={adding} style={{ padding: '10px 20px', backgroundColor: 'var(--bg-hover)', color: 'var(--text-secondary)', border: 'none', borderRadius: '6px', fontSize: '14px', fontWeight: '500', cursor: adding ? 'not-allowed' : 'pointer', opacity: adding ? 0.5 : 1 }}>
          Cancel
        </button>
      </div>

      {adding && (
        <div style={{ marginTop: '16px', padding: '12px', backgroundColor: 'var(--color-primary-bg)', borderRadius: '6px', color: 'var(--color-primary)', textAlign: 'center', fontSize: '14px' }}>
          Adding to watchlist...
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Private company form
// ---------------------------------------------------------------------------
const CURRENCIES = ['USD', 'EUR', 'GBP', 'ZAR', 'AUD', 'CAD', 'NZD', 'JPY', 'CHF', 'HKD', 'SGD', 'SEK', 'NOK', 'DKK']
const SECTORS = ['Technology', 'Healthcare', 'Financials', 'Consumer Staples', 'Consumer Discretionary', 'Industrials', 'Energy', 'Materials', 'Utilities', 'Real Estate', 'Communication Services', 'Other']

function PrivateCompanyForm({ onCancel }: { onCancel: () => void }) {
  const router = useRouter()
  const [companyName, setCompanyName] = useState('')
  const [abbreviation, setAbbreviation] = useState('')
  const [pricePerShare, setPricePerShare] = useState('')
  const [currency, setCurrency] = useState('USD')
  const [sector, setSector] = useState('')
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState('')

  const abbreviationError = abbreviation && !/^[A-Z0-9]{1,12}$/.test(abbreviation)
    ? 'Use only letters and numbers, max 12 characters'
    : ''

  const handleSubmit = async () => {
    if (!companyName.trim()) { setError('Company name is required'); return }
    if (!abbreviation.trim()) { setError('Abbreviation/code is required'); return }
    if (abbreviationError) { setError(abbreviationError); return }

    const ticker = `PRIVATE#${abbreviation.trim().toUpperCase()}`
    const price = pricePerShare ? parseFloat(pricePerShare) : undefined

    setAdding(true)
    setError('')
    try {
      const result = await stockApi.addToWatchlist(
        ticker,
        companyName.trim(),
        undefined,
        undefined,
        { companyType: 'private', pricePerShare: price, sector: sector || undefined, currency }
      )
      if (result.success) {
        const priceParam = price != null ? `&price=${price}&currency=${encodeURIComponent(currency)}` : ''
        const nameParam = `&company_name=${encodeURIComponent(companyName.trim())}`
        const sectorParam = sector ? `&sector=${encodeURIComponent(sector)}` : ''
        router.push(`/ticker?symbol=${encodeURIComponent(ticker)}${priceParam}${nameParam}${sectorParam}`)
      } else {
        setError(result.message || 'Failed to add to watchlist')
      }
    } catch (err: any) {
      setError(err.message || 'Failed to add to watchlist')
    } finally {
      setAdding(false)
    }
  }

  const selectStyle: React.CSSProperties = { ...inputStyle, cursor: 'pointer' }

  return (
    <div>
      <div style={{ backgroundColor: 'var(--bg-surface-subtle)', border: '1px solid var(--border-default)', borderRadius: '8px', padding: '12px 16px', marginBottom: '20px', fontSize: '13px', color: 'var(--text-muted)', lineHeight: '1.5' }}>
        Private companies are stored in your watchlist only and are never visible to other users.
        No market data will be fetched — enter financial data manually after adding.
      </div>

      {error && (
        <div style={{ padding: '10px 14px', backgroundColor: 'var(--status-error-bg)', border: '1px solid #ef4444', borderRadius: '6px', color: 'var(--status-error-text)', marginBottom: '16px', fontSize: '14px' }}>
          {error}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px' }}>
        {/* Company Name */}
        <div>
          <label style={labelStyle}>Company Name <span style={{ color: '#ef4444' }}>*</span></label>
          <input
            type="text"
            value={companyName}
            onChange={e => setCompanyName(e.target.value)}
            placeholder="e.g. Acme Holdings"
            disabled={adding}
            style={inputStyle}
            onFocus={e => e.currentTarget.style.borderColor = 'var(--color-primary)'}
            onBlur={e => e.currentTarget.style.borderColor = 'var(--border-input)'}
          />
        </div>

        {/* Abbreviation */}
        <div>
          <label style={labelStyle}>
            Ticker / Abbreviation <span style={{ color: '#ef4444' }}>*</span>
            <span style={{ fontWeight: '400', color: 'var(--text-muted)', marginLeft: '6px' }}>Letters and numbers only, max 12 characters</span>
          </label>
          <input
            type="text"
            value={abbreviation}
            onChange={e => setAbbreviation(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ''))}
            placeholder="e.g. ACME"
            disabled={adding}
            maxLength={12}
            style={{ ...inputStyle, borderColor: abbreviationError ? '#ef4444' : undefined, fontFamily: 'monospace', letterSpacing: '0.05em' }}
            onFocus={e => e.currentTarget.style.borderColor = abbreviationError ? '#ef4444' : 'var(--color-primary)'}
            onBlur={e => e.currentTarget.style.borderColor = abbreviationError ? '#ef4444' : 'var(--border-input)'}
          />
          {abbreviationError && <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#ef4444' }}>{abbreviationError}</p>}
        </div>

        {/* Price + Currency row */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: '10px', alignItems: 'end' }}>
          <div>
            <label style={labelStyle}>Price per Share <span style={{ fontWeight: '400', color: 'var(--text-muted)' }}>(optional)</span></label>
            <input
              type="number"
              value={pricePerShare}
              onChange={e => setPricePerShare(e.target.value)}
              placeholder="0.00"
              min="0"
              step="0.01"
              disabled={adding}
              style={inputStyle}
              onFocus={e => e.currentTarget.style.borderColor = 'var(--color-primary)'}
              onBlur={e => e.currentTarget.style.borderColor = 'var(--border-input)'}
            />
          </div>
          <div style={{ minWidth: '90px' }}>
            <label style={labelStyle}>Currency</label>
            <select value={currency} onChange={e => setCurrency(e.target.value)} disabled={adding} style={selectStyle}>
              {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
        </div>

        {/* Sector */}
        <div>
          <label style={labelStyle}>Sector <span style={{ fontWeight: '400', color: 'var(--text-muted)' }}>(optional — used for preset selection)</span></label>
          <select value={sector} onChange={e => setSector(e.target.value)} disabled={adding} style={selectStyle}>
            <option value="">— Select sector —</option>
            {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px' }}>
        <button onClick={onCancel} disabled={adding} style={{ padding: '10px 20px', backgroundColor: 'var(--bg-hover)', color: 'var(--text-secondary)', border: 'none', borderRadius: '6px', fontSize: '14px', fontWeight: '500', cursor: adding ? 'not-allowed' : 'pointer', opacity: adding ? 0.5 : 1 }}>
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={adding || !companyName.trim() || !abbreviation.trim() || !!abbreviationError}
          style={{ padding: '10px 24px', backgroundColor: 'var(--color-primary)', color: '#fff', border: 'none', borderRadius: '6px', fontSize: '14px', fontWeight: '600', cursor: (adding || !companyName.trim() || !abbreviation.trim() || !!abbreviationError) ? 'not-allowed' : 'pointer', opacity: (adding || !companyName.trim() || !abbreviation.trim() || !!abbreviationError) ? 0.6 : 1 }}
        >
          {adding ? 'Adding...' : 'Add to Watchlist'}
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
type Mode = 'public' | 'private'

function AddToWatchlistContent() {
  const router = useRouter()
  const [mode, setMode] = useState<Mode>('public')

  const tabStyle = (active: boolean): React.CSSProperties => ({
    flex: 1,
    padding: '10px 0',
    border: 'none',
    borderBottom: active ? '2px solid var(--color-primary)' : '2px solid transparent',
    backgroundColor: 'transparent',
    color: active ? 'var(--color-primary)' : 'var(--text-muted)',
    fontSize: '14px',
    fontWeight: active ? '600' : '400',
    cursor: 'pointer',
    transition: 'color 0.15s, border-color 0.15s',
  })

  return (
    <div className="container" style={{ padding: '40px 20px', maxWidth: '560px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '26px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '24px' }}>
        Add to Watchlist
      </h1>

      {/* DISABLED: Private company tab hidden pending further development.
          PrivateCompanyForm and related logic below are kept for future use. */}
      <PublicCompanyForm onCancel={() => router.back()} />
    </div>
  )
}

export default function AddToWatchlistPage() {
  return (
    <RequireAuth>
      <AddToWatchlistContent />
    </RequireAuth>
  )
}
