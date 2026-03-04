'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { stockApi } from '@/lib/api'
import { formatPrice } from '@/lib/currency'

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
  const [bulkAnalyzing, setBulkAnalyzing] = useState(false)
  const [bulkResult, setBulkResult] = useState<{ success: boolean; message: string } | null>(null)
  const [sortBy, setSortBy] = useState<'name' | 'undervalued'>('name')

  useEffect(() => {
    loadWatchlist()
  }, [])

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
                recommendation: la.recommendation ?? item.recommendation,
                pe_ratio: la.aiFinancialData?.keyMetrics?.pe_ratio ?? la.pe_ratio ?? item.pe_ratio,
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

  const runBulkAnalysis = async () => {
    if (watchlistItems.length === 0) {
      setBulkResult({ success: false, message: 'No stocks in watchlist to analyze.' })
      setTimeout(() => setBulkResult(null), 5000)
      return
    }
    try {
      setBulkAnalyzing(true)
      setBulkResult(null)
      setError('')
      const tickers = watchlistItems.map((item) => item.ticker)
      const exchangeName = watchlistItems[0]?.exchange || 'Custom'
      const result = await stockApi.batchAnalyze(tickers, exchangeName, true)
      setBulkResult({
        success: result.success,
        message: result.message || (result.summary ? `Processed ${result.summary.successful ?? 0} successfully, ${result.summary.failed ?? 0} failed.` : 'Done.')
      })
      setTimeout(() => setBulkResult(null), 5000)
      if (result.success) await loadWatchlist()
    } catch (err: any) {
      setBulkResult({
        success: false,
        message: err?.response?.data?.detail || err?.message || 'Bulk analysis failed.'
      })
      setTimeout(() => setBulkResult(null), 5000)
    } finally {
      setBulkAnalyzing(false)
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

  const sortedItems = [...watchlistItems].sort((a, b) => {
    if (sortBy === 'undervalued') {
      // Items with margin data first, sorted descending (most undervalued first)
      const aVal = a.margin_of_safety_pct ?? -Infinity
      const bVal = b.margin_of_safety_pct ?? -Infinity
      return bVal - aVal
    }
    return (a.company_name || a.ticker).localeCompare(b.company_name || b.ticker)
  })

  if (loading) {
    return (
      <div className="container" style={{ padding: '40px 20px', textAlign: 'center' }}>
        <LoadingSpinner />
        <p style={{ marginTop: '20px', color: '#6b7280' }}>Loading your watchlist...</p>
      </div>
    )
  }

  return (
    <div className="container watchlist-page" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '36px', fontWeight: '700', color: '#111827', marginBottom: '8px' }}>
          Watchlist
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
      <div
        className="watchlist-cards-box"
        style={{
          background: 'white',
          borderRadius: '12px',
          padding: '24px',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
          border: '1px solid #e5e7eb',
          marginBottom: '32px'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
            <h2 style={{ fontSize: '24px', fontWeight: '600', color: '#111827', margin: 0 }}>
              📊 Your Stocks
            </h2>
            <div style={{ display: 'flex', gap: '4px', background: '#f3f4f6', borderRadius: '8px', padding: '3px' }}>
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
                    backgroundColor: sortBy === opt ? 'white' : 'transparent',
                    color: sortBy === opt ? '#111827' : '#6b7280',
                    boxShadow: sortBy === opt ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                  }}
                >
                  {opt === 'name' ? 'Name' : '% Undervalued'}
                </button>
              ))}
            </div>
          </div>
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
              {bulkAnalyzing ? '⏳ Analyzing…' : '📈 Run bulk analysis'}
            </button>
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

        {bulkResult && (
          <div style={{
            padding: '12px 16px',
            marginBottom: '16px',
            backgroundColor: bulkResult.success ? '#d1fae5' : '#fee2e2',
            border: `1px solid ${bulkResult.success ? '#10b981' : '#ef4444'}`,
            borderRadius: '6px',
            color: bulkResult.success ? '#065f46' : '#991b1b'
          }}>
            {bulkResult.success ? '✅' : '⚠️'} {bulkResult.message}
          </div>
        )}
        
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
          <div className="watchlist-cards-grid" style={{ display: 'grid', gap: '16px' }}>
            {sortedItems.map((stock) => {
              const valuation = getValuationDisplay(stock)
              return (
              <div
                key={stock.ticker}
                className="watchlist-stock-card"
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
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px', flexWrap: 'wrap' }}>
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
                          color: '#92400e',
                          backgroundColor: '#fef3c7',
                          border: '1px solid #fde68a',
                        }}>
                          ⚠ Incomplete Data
                        </span>
                      )}
                    </div>
                    <p style={{ fontSize: '14px', color: '#6b7280', margin: '0 0 4px 0' }}>
                      {stock.ticker}
                    </p>
                    <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginTop: '6px', alignItems: 'center' }}>
                      {stock.fair_value != null && !isNaN(stock.fair_value) && (
                        <span style={{ fontSize: '12px', color: '#4b5563' }}>
                          Fair value: {formatPrice(stock.fair_value, stock.currency)}
                        </span>
                      )}
                      {stock.pe_ratio != null && !isNaN(stock.pe_ratio) && (
                        <span style={{ fontSize: '12px', color: '#4b5563' }}>
                          P/E: {stock.pe_ratio.toFixed(1)}
                        </span>
                      )}
                      {(stock.financial_health_score != null || stock.business_quality_score != null) && (
                        <span style={{ fontSize: '12px', color: '#6b7280' }}>
                          {stock.financial_health_score != null && `Health ${Math.round(stock.financial_health_score)}`}
                          {stock.financial_health_score != null && stock.business_quality_score != null && ' · '}
                          {stock.business_quality_score != null && `Quality ${Math.round(stock.business_quality_score)}`}
                        </span>
                      )}
                    </div>
                    {(stock.last_updated || stock.last_analyzed_at) && (
                      <p style={{ fontSize: '12px', color: '#9ca3af', margin: '4px 0 0 0' }}>
                        Updated: {new Date(stock.last_analyzed_at || stock.last_updated!).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
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
                    {stock.fair_value && stock.current_price && stock.current_price > 0 && (() => {
                      const multiplier = stock.fair_value / stock.current_price
                      const isUndervalued = multiplier > 1
                      return (
                        <div style={{
                          fontSize: '15px',
                          fontWeight: '700',
                          color: isUndervalued ? '#059669' : '#6b7280',
                          marginTop: '4px',
                        }}>
                          V/P: {multiplier.toFixed(2)}x
                        </div>
                      )
                    })()}
                    <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '4px' }}>
                      Click to analyze →
                    </div>
                  </div>
                </div>
              </div>
            )
            })}
          </div>
        )}
      </div>

    </div>
  )
}