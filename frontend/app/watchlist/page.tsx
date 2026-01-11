'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { stockApi, WatchlistItem } from '@/lib/api'
import { RequireAuth } from '@/components/AuthProvider'
import { POPULAR_TICKERS } from '@/lib/enhanced-search'

export default function WatchlistPage() {
  return (
    <RequireAuth>
      <WatchlistContent />
    </RequireAuth>
  )
}

function WatchlistContent() {
  const router = useRouter()
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>('')
  const [refreshingPrices, setRefreshingPrices] = useState(false)
  const [livePrices, setLivePrices] = useState<Record<string, { price?: number; company_name?: string; error?: string; comment?: string; success?: boolean }>>({})

  useEffect(() => {
    loadWatchlist()
  }, [])

  const loadWatchlist = async () => {
    try {
      setLoading(true)
      setError('')
      
      console.log('🔄 Loading watchlist...')
      const startTime = Date.now()
      
      // Load watchlist from API (enhanced with MarketStack integration)
      console.log('🌐 Loading watchlist...')
      const result = await stockApi.getWatchlist()
      const loadTime = Date.now() - startTime
      console.log(`✅ Watchlist loaded: ${result?.items?.length || 0} items in ${loadTime}ms`)
      setWatchlist(result?.items || [])
    } catch (err: any) {
      console.log('❌ Error loading watchlist:', err)
      // Use formatted error message (from api.ts interceptor)
      setError(err?.message || 'Failed to load watchlist')
      console.error('Error loading watchlist:', err)
    } finally {
      setLoading(false)
    }
  }

  const refreshLivePrices = async () => {
    try {
      setRefreshingPrices(true)
      
      // Use the standard live prices endpoint (enhanced with MarketStack)
      console.log('🔄 Refreshing live prices from MarketStack API...')
      const result = await stockApi.getWatchlistLivePrices()
      setLivePrices(result?.live_prices || {})
      console.log('✅ Live prices updated successfully')
      
      // Also refresh analysis data for each stock to get fair values
      console.log('🔄 Refreshing analysis data for valuation...')
      const updatedWatchlist = await Promise.all(
        (watchlist || []).map(async (item) => {
          try {
            if (!item?.ticker) return item
            const analysis = await stockApi.analyzeStock(item.ticker)
            return {
              ...item,
              current_price: analysis?.currentPrice,
              fair_value: analysis?.fairValue,
              margin_of_safety_pct: analysis?.marginOfSafety,
              recommendation: analysis?.recommendation
            }
          } catch (error) {
            console.warn(`Failed to get analysis for ${item?.ticker}:`, error)
            return item // Return original item if analysis fails
          }
        })
      )
      setWatchlist(updatedWatchlist)
      console.log('✅ Analysis data updated successfully')
    } catch (err: any) {
      console.error('Error refreshing live prices:', err)
      // Set empty object to prevent undefined errors
      setLivePrices({})
      // Don't show error for live prices - it's optional
    } finally {
      setRefreshingPrices(false)
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
      alert(err?.message || 'Failed to remove from watchlist')
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
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={refreshLivePrices}
            disabled={refreshingPrices || loading}
            style={{
              padding: '10px 20px',
              backgroundColor: '#059669',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: '500',
              cursor: (refreshingPrices || loading) ? 'not-allowed' : 'pointer',
              opacity: (refreshingPrices || loading) ? 0.5 : 1,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            🔄 {refreshingPrices ? 'Refreshing...' : 'Refresh Prices'}
          </button>
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

      {watchlist && watchlist.length === 0 ? (
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
          {watchlist && Array.isArray(watchlist) && watchlist.map((item) => {
            // Safety check for item
            if (!item) return null
            
            return (
            <div
              key={item?.ticker || Math.random()}
              onClick={() => router.push(`/watchlist/${item?.ticker || ''}`)}
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
                      {item?.company_name || item?.ticker || 'Unknown Company'}
                    </h2>
                    {item?.recommendation && (
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
                    {/* Cache status indicator */}
                    {item?.cache_info && (
                      <span style={{
                        padding: '2px 8px',
                        borderRadius: '8px',
                        fontSize: '10px',
                        fontWeight: '500',
                        backgroundColor: item.cache_info.status === 'fresh' ? '#dcfce7' : 
                                        item.cache_info.status === 'stale' ? '#fef3c7' : '#fee2e2',
                        color: item.cache_info.status === 'fresh' ? '#166534' : 
                               item.cache_info.status === 'stale' ? '#92400e' : '#991b1b'
                      }}>
                        {item.cache_info.status === 'fresh' && '✅ Fresh'}
                        {item.cache_info.status === 'stale' && '⏰ Stale'}
                        {item.cache_info.status === 'missing' && '❌ No Data'}
                      </span>
                    )}
                  </div>
                  
                  <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 12px 0', fontWeight: '600' }}>
                    {item?.ticker || 'Unknown Ticker'}
                  </p>

                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                    gap: '16px',
                    marginTop: '16px'
                  }}>
                    {/* Show live price if available, otherwise cached price */}
                    {(() => {
                      const tickerPriceData = livePrices?.[item?.ticker || '']
                      const livePrice = tickerPriceData?.price
                      const cachedPrice = item?.current_price
                      const priceError = tickerPriceData?.error
                      
                      // Show live price if available and valid
                      if (livePrice && Math.abs(livePrice - 1.0) > 0.01) {
                        return (
                          <div>
                            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>
                              Current Price 
                              <span style={{ color: '#059669', fontSize: '10px', marginLeft: '4px' }}>● LIVE</span>
                            </div>
                            <div style={{ fontSize: '16px', fontWeight: '600', color: '#111827' }}>
                              {formatPrice(livePrice)}
                            </div>
                            {/* Show success comment if available */}
                            {tickerPriceData?.comment && tickerPriceData?.success && (
                              <div style={{ 
                                fontSize: '10px', 
                                color: '#059669', 
                                marginTop: '2px',
                                fontStyle: 'italic'
                              }}>
                                ✓ {tickerPriceData.comment}
                              </div>
                            )}
                          </div>
                        )
                      }
                      // Show cached price if available and valid
                      else if (cachedPrice && Math.abs(cachedPrice - 1.0) > 0.01) {
                        return (
                          <div>
                            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>
                              Current Price
                              {item?.cache_info?.last_updated && (
                                <span style={{ fontSize: '10px', marginLeft: '4px' }}>
                                  ({item.cache_info.last_updated})
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: '16px', fontWeight: '600', color: '#111827' }}>
                              {formatPrice(cachedPrice)}
                            </div>
                          </div>
                        )
                      }
                      // Show error if live price fetch failed
                      else if (priceError) {
                        return (
                          <div>
                            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Current Price</div>
                            <div style={{ fontSize: '14px', fontWeight: '500', color: '#dc2626' }}>
                              ⚠️ {priceError}
                            </div>
                            {/* Show detailed error comment if available */}
                            {tickerPriceData?.comment && (
                              <div style={{ 
                                fontSize: '11px', 
                                color: '#6b7280', 
                                marginTop: '2px',
                                fontStyle: 'italic',
                                lineHeight: '1.3'
                              }}>
                                {tickerPriceData.comment}
                              </div>
                            )}
                          </div>
                        )
                      }
                      // Show cached price error if available
                      else if ((item as any).price_error) {
                        return (
                          <div>
                            <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Current Price</div>
                            <div style={{ fontSize: '14px', fontWeight: '500', color: '#dc2626' }}>
                              ⚠️ {(item as any).price_error}
                            </div>
                          </div>
                        )
                      }
                      return null
                    })()}
                    <div>
                      <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Fair Value</div>
                      <div style={{ fontSize: '16px', fontWeight: '600', color: '#111827' }}>
                        {item?.fair_value && item.fair_value > 0 ? formatPrice(item.fair_value) : 'Not available'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Valuation</div>
                      <div style={{
                        fontSize: '16px',
                        fontWeight: '600',
                        color: item?.margin_of_safety_pct && item.margin_of_safety_pct > 0 ? '#10b981' : '#ef4444'
                      }}>
                        {item?.fair_value && item?.margin_of_safety_pct && item.margin_of_safety_pct !== 0 
                          ? item.margin_of_safety_pct > 0 
                            ? `${Math.abs(item.margin_of_safety_pct).toFixed(1)}% Under`
                            : `${Math.abs(item.margin_of_safety_pct).toFixed(1)}% Over`
                          : 'Not available'}
                      </div>
                    </div>
                    {item?.last_analyzed_at && (
                      <div>
                        <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>Last Analyzed</div>
                        <div style={{ fontSize: '14px', color: '#111827' }}>
                          {new Date(item.last_analyzed_at).toLocaleDateString()}
                        </div>
                      </div>
                    )}
                  </div>

                  {item?.notes && (
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
                    handleRemove(item?.ticker || '')
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
            )
          })}
        </div>
      )}
    </div>
  )
}

