'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { stockApi } from '@/lib/api'
import { formatPrice } from '@/lib/currency'

interface WatchlistItem {
  ticker: string
  company_name?: string
  current_price?: number
  price_change?: number
  price_change_percent?: number
  recommendation?: string
  last_updated?: string
  currency?: string
}

// Simple loading spinner component
const LoadingSpinner = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '20px' }}>
    <div style={{
      width: '40px',
      height: '40px',
      border: '4px solid #f3f4f6',
      borderTop: '4px solid #2563eb',
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
  const [watchlistItems, setWatchlistItems] = useState<WatchlistItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')

  useEffect(() => {
    loadWatchlist()
  }, [])

  const loadWatchlist = async () => {
    try {
      setLoading(true)
      setError('')
      
      // Get watchlist from API
      const response = await stockApi.getWatchlist()
      setWatchlistItems(response?.items || [])
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

  const handleStockClick = (ticker: string) => {
    router.push(`/ticker?ticker=${ticker}`)
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

  const getPriceChangeColor = (change?: number) => {
    if (!change) return '#6b7280'
    return change >= 0 ? '#10b981' : '#ef4444'
  }

  if (loading) {
    return (
      <div className="container" style={{ padding: '40px 20px', textAlign: 'center' }}>
        <LoadingSpinner />
        <p style={{ marginTop: '20px', color: '#6b7280' }}>Loading your watchlist...</p>
      </div>
    )
  }

  return (
    <div className="container" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '36px', fontWeight: '700', color: '#111827', marginBottom: '8px' }}>
          Stock Analysis Watchlist
        </h1>
        <p style={{ fontSize: '16px', color: '#6b7280' }}>
          Monitor and analyze your favorite stocks with real-time data and comprehensive financial metrics.
        </p>
      </div>

      {/* Error Message */}
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

      {/* Watchlist Items */}
      <div style={{
        background: 'white',
        borderRadius: '12px',
        padding: '24px',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        border: '1px solid #e5e7eb',
        marginBottom: '32px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
          <h2 style={{ fontSize: '24px', fontWeight: '600', color: '#111827', margin: 0 }}>
            📊 Your Stocks
          </h2>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={loadWatchlist}
              style={{
                padding: '8px 16px',
                backgroundColor: '#2563eb',
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
        
        {watchlistItems.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#6b7280' }}>
            <p>No stocks in your watchlist yet.</p>
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
                marginTop: '16px'
              }}
            >
              Add Your First Stock
            </button>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '16px' }}>
            {watchlistItems.map((stock) => (
              <div
                key={stock.ticker}
                style={{
                  padding: '20px',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  backgroundColor: '#f9fafb',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
                onClick={() => handleStockClick(stock.ticker)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = '#f3f4f6'
                  e.currentTarget.style.borderColor = '#3b82f6'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = '#f9fafb'
                  e.currentTarget.style.borderColor = '#e5e7eb'
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
                      <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#111827', margin: 0 }}>
                        {stock.company_name || `${stock.ticker} Corporation`}
                      </h3>
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
                    </div>
                    <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 4px 0' }}>
                      {stock.ticker}
                    </p>
                    {stock.last_updated && (
                      <p style={{ fontSize: '12px', color: '#9ca3af', margin: 0 }}>
                        Updated: {new Date(stock.last_updated).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  
                  <div style={{ textAlign: 'right' }}>
                    {stock.current_price ? (
                      <>
                        <div style={{ fontSize: '20px', fontWeight: '700', color: '#111827' }}>
                          {formatPrice(stock.current_price, stock.currency)}
                        </div>
                        {stock.price_change !== undefined && (
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
                      <div style={{ fontSize: '14px', color: '#6b7280' }}>
                        Price unavailable
                      </div>
                    )}
                    <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
                      Click to analyze →
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

    </div>
  )
}