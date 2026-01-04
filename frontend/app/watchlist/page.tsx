'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { stockApi, WatchlistItem } from '@/lib/api'

export default function WatchlistPage() {
  const router = useRouter()
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')

  useEffect(() => {
    loadWatchlist()
  }, [])

  const loadWatchlist = async () => {
    try {
      setLoading(true)
      setError('')
      const result = await stockApi.getWatchlist()
      setWatchlist(result.items)
    } catch (err: any) {
      // Use formatted error message (from api.ts interceptor)
      setError(err.message || 'Failed to load watchlist')
      console.error('Error loading watchlist:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleRemove = async (ticker: string) => {
    if (!confirm(`Remove ${ticker} from watchlist?`)) {
      return
    }

    try {
      await stockApi.removeFromWatchlist(ticker)
      await loadWatchlist()
    } catch (err: any) {
      // Use formatted error message (from api.ts interceptor)
      alert(err.message || 'Failed to remove from watchlist')
      console.error('Error removing from watchlist:', err)
    }
  }

  const formatPrice = (price?: number) => {
    if (price === undefined || price === null) return 'N/A'
    return `$${price.toFixed(2)}`
  }

  const formatPercent = (value?: number) => {
    if (value === undefined || value === null) return 'N/A'
    const sign = value >= 0 ? '+' : ''
    return `${sign}${value.toFixed(1)}%`
  }

  const getRecommendationColor = (recommendation?: string) => {
    switch (recommendation) {
      case 'Strong Buy':
        return '#10b981' // green
      case 'Buy':
        return '#3b82f6' // blue
      case 'Hold':
        return '#f59e0b' // yellow
      case 'Avoid':
        return '#ef4444' // red
      default:
        return '#6b7280' // gray
    }
  }

  if (loading) {
    return (
      <div className="container" style={{ padding: '40px 20px', textAlign: 'center' }}>
        <p>Loading watchlist...</p>
      </div>
    )
  }

  return (
    <div className="container" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '28px', fontWeight: '700', color: '#111827', margin: 0 }}>
          📊 Watchlist
        </h1>
        <button
          onClick={() => router.push('/watchlist/add')}
          style={{
            padding: '10px 20px',
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: '500',
            cursor: 'pointer',
            transition: 'background-color 0.2s'
          }}
          onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#1d4ed8' }}
          onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#2563eb' }}
        >
          + Add Stock
        </button>
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
          ❌ {error}
        </div>
      )}

      {watchlist.length === 0 ? (
        <div style={{
          padding: '60px 20px',
          textAlign: 'center',
          backgroundColor: '#f9fafb',
          borderRadius: '8px',
          border: '2px dashed #d1d5db'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>📋</div>
          <h2 style={{ fontSize: '20px', fontWeight: '600', color: '#111827', marginBottom: '8px' }}>
            Your watchlist is empty
          </h2>
          <p style={{ color: '#6b7280', marginBottom: '20px' }}>
            Add stocks to track their performance and analysis
          </p>
          <button
            onClick={() => router.push('/watchlist/add')}
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
            Add Your First Stock
          </button>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gap: '16px'
        }}>
          {watchlist.map((item) => (
            <div
              key={item.ticker}
              onClick={() => router.push(`/watchlist/${item.ticker}`)}
              style={{
                padding: '20px',
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                cursor: 'pointer',
                transition: 'all 0.2s',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = '#2563eb'
                e.currentTarget.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = '#e5e7eb'
                e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                    <h2 style={{ fontSize: '20px', fontWeight: '700', color: '#111827', margin: 0 }}>
                      {item.ticker}
                    </h2>
                    {item.recommendation && (
                      <span style={{
                        padding: '4px 12px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: '600',
                        color: 'white',
                        backgroundColor: getRecommendationColor(item.recommendation)
                      }}>
                        {item.recommendation}
                      </span>
                    )}
                  </div>
                  
                  {item.company_name && (
                    <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 12px 0' }}>
                      {item.company_name}
                    </p>
                  )}

                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                    gap: '16px',
                    marginTop: '16px'
                  }}>
                    {/* Show price if valid, or show error message if price fetch failed */}
                    {item.current_price && Math.abs(item.current_price - 1.0) > 0.01 ? (
                      <div>
                        <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Current Price</div>
                        <div style={{ fontSize: '16px', fontWeight: '600', color: '#111827' }}>
                          {formatPrice(item.current_price)}
                        </div>
                      </div>
                    ) : (item as any).price_error ? (
                      <div>
                        <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Current Price</div>
                        <div style={{ fontSize: '14px', fontWeight: '500', color: '#dc2626' }}>
                          ⚠️ {(item as any).price_error}
                        </div>
                      </div>
                    ) : null}
                    <div>
                      <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Fair Value</div>
                      <div style={{ fontSize: '16px', fontWeight: '600', color: '#111827' }}>
                        {formatPrice(item.fair_value)}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Margin of Safety</div>
                      <div style={{
                        fontSize: '16px',
                        fontWeight: '600',
                        color: item.margin_of_safety_pct && item.margin_of_safety_pct > 0 ? '#10b981' : '#ef4444'
                      }}>
                        {formatPercent(item.margin_of_safety_pct)}
                      </div>
                    </div>
                    {item.last_analyzed_at && (
                      <div>
                        <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Last Analyzed</div>
                        <div style={{ fontSize: '14px', color: '#111827' }}>
                          {new Date(item.last_analyzed_at).toLocaleDateString()}
                        </div>
                      </div>
                    )}
                  </div>

                  {item.notes && (
                    <div style={{
                      marginTop: '12px',
                      padding: '8px 12px',
                      backgroundColor: '#f9fafb',
                      borderRadius: '6px',
                      fontSize: '13px',
                      color: '#374151'
                    }}>
                      <strong>Notes:</strong> {item.notes}
                    </div>
                  )}
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleRemove(item.ticker)
                  }}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: '#fee2e2',
                    color: '#991b1b',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '12px',
                    fontWeight: '500',
                    cursor: 'pointer',
                    marginLeft: '16px'
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#fecaca' }}
                  onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#fee2e2' }}
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

