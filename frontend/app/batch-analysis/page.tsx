'use client'

import { useState, useEffect, useRef } from 'react'
import { stockApi, SearchResult } from '@/lib/api'
import MultiplePDFUpload from '@/components/MultiplePDFUpload'
import { formatPrice, formatPercent, formatNumber } from '@/lib/currency'

interface TickerCard {
  ticker: string
  companyName?: string
  exchange?: string
}

export default function BatchAnalysisPage() {
  const [tickers, setTickers] = useState<TickerCard[]>([])
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [suggestions, setSuggestions] = useState<SearchResult[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [loading, setLoading] = useState<boolean>(false)
  const [searchLoading, setSearchLoading] = useState<boolean>(false)
  const [validating, setValidating] = useState<string | null>(null)
  const [result, setResult] = useState<any>(null)
  const [batchResults, setBatchResults] = useState<any[]>([])
  const [loadingResults, setLoadingResults] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [showPDFUpload, setShowPDFUpload] = useState(false)
  const [uploadedTickers, setUploadedTickers] = useState<Set<string>>(new Set())
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const skipExisting = true

  // Search for tickers with debounce
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    if (searchQuery.trim().length >= 1) {
      setSearchLoading(true)
      searchTimeoutRef.current = setTimeout(async () => {
        try {
          const results = await stockApi.searchTickers(searchQuery.trim())
          // Ensure results is always an array
          const safeResults = Array.isArray(results) ? results : []
          setSuggestions(safeResults)
          setShowSuggestions(safeResults.length > 0)
          setSelectedIndex(-1)
        } catch (error) {
          console.error('Search error:', error)
          setSuggestions([])
          setShowSuggestions(false)
        } finally {
          setSearchLoading(false)
        }
      }, 300)
    } else {
      setSuggestions([])
      setShowSuggestions(false)
      setSearchLoading(false)
    }

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [searchQuery])

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [])

  const validateAndAddTicker = async (ticker: string, companyName?: string, exchange?: string) => {
    // Check if already added
    if (tickers.some(t => t.ticker.toUpperCase() === ticker.toUpperCase())) {
      setError(`${ticker.toUpperCase()} is already in the list`)
      setTimeout(() => setError(null), 3000)
      return
    }

    // Check if exceeds limit
    if (tickers.length >= 1000) {
      setError('Maximum 1000 tickers per batch')
      setTimeout(() => setError(null), 3000)
      return
    }

    setValidating(ticker)
    setError(null)

    try {
      // Validate ticker exists by getting a quote
      const quote = await stockApi.getQuote(ticker)
      
      const newTicker: TickerCard = {
        ticker: quote.ticker,
        companyName: quote.companyName || companyName,
        exchange: exchange
      }

      setTickers([...tickers, newTicker])
      setSuccessMessage(`✓ ${newTicker.ticker} added successfully`)
      setTimeout(() => setSuccessMessage(null), 3000)
    } catch (err: any) {
      setError(`Invalid ticker: ${ticker}. ${err.response?.data?.detail || err.message || 'Ticker not found'}`)
      setTimeout(() => setError(null), 5000)
    } finally {
      setValidating(null)
    }
  }

  const handleSelectSuggestion = (suggestion: SearchResult) => {
    // Close dropdown immediately
    setShowSuggestions(false)
    setSearchQuery('')
    // Then validate and add
    validateAndAddTicker(suggestion.ticker, suggestion.companyName, suggestion.exchange)
  }

  const handleRemoveTicker = (tickerToRemove: string) => {
    setTickers(tickers.filter(t => t.ticker !== tickerToRemove))
    setSuccessMessage(`✓ ${tickerToRemove} removed`)
    setTimeout(() => setSuccessMessage(null), 2000)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(prev => 
        prev < suggestions.length - 1 ? prev + 1 : prev
      )
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(prev => prev > 0 ? prev - 1 : -1)
    } else if (e.key === 'Enter' && selectedIndex >= 0 && suggestions[selectedIndex]) {
      e.preventDefault()
      handleSelectSuggestion(suggestions[selectedIndex])
    } else if (e.key === 'Enter' && searchQuery.trim()) {
      e.preventDefault()
      // Close dropdown immediately
      setShowSuggestions(false)
      // Try to add the typed ticker directly
      validateAndAddTicker(searchQuery.trim().toUpperCase())
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setResult(null)
    setSuccessMessage(null)

    if (tickers.length === 0) {
      setError('Please add at least one ticker symbol')
      return
    }

    setLoading(true)
    setBatchResults([])
    try {
      const tickerList = tickers.map(t => t.ticker)
      const response = await stockApi.batchAnalyze(tickerList, 'Custom', skipExisting)
      setResult(response)
      setSuccessMessage('Batch analysis completed successfully!')
      
      // Fetch and display results
      if (response.success) {
        setLoadingResults(true)
        try {
          // Use the exchange name from the response summary if available
          const exchangeName = response.summary?.exchange || 'Custom'
          console.log('Fetching batch results for exchange:', exchangeName)
          const results = await stockApi.getBatchResults(exchangeName)
          console.log('Batch results received:', results)
          setBatchResults(results.results || [])
          if (!results.results || results.results.length === 0) {
            console.warn('No results found. Exchange:', exchangeName, 'Total:', results.total)
            setError(`No results found for exchange "${exchangeName}". The analysis may have been saved with a different exchange name.`)
          }
        } catch (err: any) {
          console.error('Error fetching batch results:', err)
          setError(`Failed to load results: ${err.response?.data?.detail || err.message || 'Unknown error'}. You can try refreshing manually.`)
        } finally {
          setLoadingResults(false)
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Batch analysis failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container" style={{ maxWidth: '1000px', margin: '40px auto', padding: '20px' }}>
      <h1 style={{ fontSize: '36px', marginBottom: '8px', color: '#111827' }}>
        Batch Stock Analysis
      </h1>
      <p style={{ fontSize: '16px', color: '#6b7280', marginBottom: '32px' }}>
        Analyze multiple stocks at once. Search and add tickers, or upload PDF financial statements.
      </p>

      {/* Toggle between ticker search and PDF upload */}
      <div style={{ marginBottom: '32px', display: 'flex', gap: '16px', justifyContent: 'center' }}>
        <button
          onClick={() => setShowPDFUpload(false)}
          style={{
            padding: '12px 24px',
            backgroundColor: !showPDFUpload ? '#2563eb' : '#e5e7eb',
            color: !showPDFUpload ? 'white' : '#374151',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: '500',
            transition: 'all 0.2s'
          }}
        >
          Add by Ticker Search
        </button>
        <button
          onClick={() => setShowPDFUpload(true)}
          style={{
            padding: '12px 24px',
            backgroundColor: showPDFUpload ? '#2563eb' : '#e5e7eb',
            color: showPDFUpload ? 'white' : '#374151',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: '500',
            transition: 'all 0.2s'
          }}
        >
          Upload PDF Statements
        </button>
      </div>

      {/* Toast Notifications - Fixed Position */}
      {/* Toast Notifications - Fixed Position (doesn't affect layout) */}
      {successMessage && (
        <div style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          padding: '12px 20px',
          backgroundColor: '#10b981',
          borderRadius: '8px',
          color: 'white',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
          zIndex: 10000,
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          animation: 'slideIn 0.3s ease-out',
          maxWidth: '400px',
          fontSize: '14px',
          fontWeight: '500'
        }}>
          <span>✓</span>
          <span>{successMessage}</span>
        </div>
      )}

      {error && (
        <div style={{
          position: 'fixed',
          top: successMessage ? '80px' : '20px',
          right: '20px',
          padding: '12px 20px',
          backgroundColor: '#ef4444',
          borderRadius: '8px',
          color: 'white',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
          zIndex: 10000,
          maxWidth: '400px',
          animation: 'slideIn 0.3s ease-out',
          fontSize: '14px',
          fontWeight: '500'
        }}>
          {error}
        </div>
      )}

      {/* PDF Upload Section */}
      {showPDFUpload && (
        <MultiplePDFUpload
          onItemComplete={(ticker) => {
            setUploadedTickers(prev => new Set([...prev, ticker]))
            // Auto-add ticker to the list if not already present
            if (!tickers.some(t => t.ticker === ticker)) {
              setTickers(prev => [...prev, { ticker: ticker.toUpperCase() }])
            }
          }}
          onAllComplete={() => {
            setSuccessMessage('All PDFs processed successfully! You can now run batch analysis.')
            setTimeout(() => setSuccessMessage(null), 5000)
          }}
        />
      )}

      {/* Add Ticker Section */}
      {!showPDFUpload && (
      <div style={{ marginBottom: '32px' }}>
        <label htmlFor="ticker-search" style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#374151' }}>
          Add Ticker
        </label>
        <div style={{ position: 'relative' }}>
          <input
            ref={inputRef}
            id="ticker-search"
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={(e) => {
              if (suggestions.length > 0) {
                setShowSuggestions(true)
              }
              e.currentTarget.style.borderColor = '#2563eb'
            }}
            placeholder="Search for a stock ticker (e.g., AAPL, MSFT)..."
            style={{
              width: '100%',
              padding: '12px 16px',
              border: '1px solid #d1d5db',
              borderRadius: '8px',
              fontSize: '16px',
              outline: 'none',
              transition: 'border-color 0.2s'
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = '#d1d5db'
            }}
          />
          
          {searchLoading && (
            <div style={{
              position: 'absolute',
              right: '16px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#6b7280'
            }}>
              Searching...
            </div>
          )}

          {/* Suggestions Dropdown */}
          {showSuggestions && suggestions.length > 0 && (
            <div
              ref={suggestionsRef}
              style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                right: 0,
                backgroundColor: 'white',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                marginTop: '4px',
                maxHeight: '300px',
                overflowY: 'auto',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                zIndex: 1000
              }}
            >
              {suggestions.map((suggestion, index) => (
                <div
                  key={`${suggestion.ticker}-${index}`}
                  onClick={() => handleSelectSuggestion(suggestion)}
                  onMouseEnter={() => setSelectedIndex(index)}
                  style={{
                    padding: '12px 16px',
                    cursor: 'pointer',
                    borderBottom: index < suggestions.length - 1 ? '1px solid #e5e7eb' : 'none',
                    backgroundColor: selectedIndex === index ? '#f3f4f6' : 'white',
                    transition: 'background-color 0.15s'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: '600', fontSize: '16px', color: '#111827' }}>
                        {suggestion.ticker}
                      </div>
                      {suggestion.companyName && (
                        <div style={{ fontSize: '14px', color: '#6b7280', marginTop: '2px' }}>
                          {suggestion.companyName}
                        </div>
                      )}
                    </div>
                    {suggestion.exchange && (
                      <div style={{ fontSize: '12px', color: '#9ca3af', textTransform: 'uppercase' }}>
                        {suggestion.exchange}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        <p style={{ fontSize: '14px', color: '#6b7280', marginTop: '8px' }}>
          {validating && `Validating ${validating}...`}
          {!validating && tickers.length > 0 && `${tickers.length} ticker(s) added`}
          {!validating && tickers.length === 0 && 'Search for stocks to add them to your batch analysis list'}
        </p>
      </div>
      )}

      {/* Ticker Cards */}
      {tickers.length > 0 && (
        <div style={{ marginBottom: '32px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '20px', fontWeight: '600', color: '#111827' }}>
              Selected Tickers ({tickers.length})
            </h2>
            <button
              onClick={() => {
                setTickers([])
                setSuccessMessage('All tickers cleared')
                setTimeout(() => setSuccessMessage(null), 2000)
              }}
              style={{
                padding: '6px 12px',
                backgroundColor: '#f3f4f6',
                color: '#374151',
                border: 'none',
                borderRadius: '6px',
                fontSize: '14px',
                cursor: 'pointer',
                fontWeight: '500'
              }}
            >
              Clear All
            </button>
          </div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: '12px'
          }}>
            {tickers.map((tickerCard) => (
              <div
                key={tickerCard.ticker}
                style={{
                  padding: '16px',
                  backgroundColor: '#f9fafb',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  position: 'relative',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#d1d5db'
                  e.currentTarget.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.1)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#e5e7eb'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                <button
                  onClick={() => handleRemoveTicker(tickerCard.ticker)}
                  style={{
                    position: 'absolute',
                    top: '8px',
                    right: '8px',
                    width: '24px',
                    height: '24px',
                    borderRadius: '50%',
                    border: 'none',
                    backgroundColor: '#fee2e2',
                    color: '#991b1b',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '16px',
                    lineHeight: '1',
                    fontWeight: 'bold',
                    transition: 'background-color 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = '#fecaca'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = '#fee2e2'
                  }}
                >
                  ×
                </button>
                <div style={{ fontWeight: '600', fontSize: '18px', color: '#111827', marginBottom: '4px' }}>
                  {tickerCard.ticker}
                </div>
                {tickerCard.companyName && (
                  <div style={{ fontSize: '12px', color: '#6b7280', lineHeight: '1.4' }}>
                    {tickerCard.companyName.length > 30 
                      ? `${tickerCard.companyName.substring(0, 30)}...` 
                      : tickerCard.companyName}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Options */}
      <div style={{ marginBottom: '24px', padding: '16px', backgroundColor: '#f9fafb', borderRadius: '8px' }}>
        <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={skipExisting}
            disabled
            style={{ marginRight: '8px', width: '18px', height: '18px' }}
          />
          <span style={{ color: '#374151' }}>
            Skip stocks already analyzed today (enabled)
          </span>
        </label>
      </div>

      {/* Submit Button */}
      <form onSubmit={handleSubmit}>
        <button
          type="submit"
          disabled={loading || tickers.length === 0}
          style={{
            width: '100%',
            padding: '14px',
            backgroundColor: loading || tickers.length === 0 ? '#9ca3af' : '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            fontSize: '16px',
            fontWeight: '600',
            cursor: loading || tickers.length === 0 ? 'not-allowed' : 'pointer',
            transition: 'background-color 0.2s'
          }}
        >
          {loading ? 'Analyzing...' : `Start Batch Analysis (${tickers.length} ticker${tickers.length !== 1 ? 's' : ''})`}
        </button>
      </form>

      {/* Results Summary */}
      {result && (
        <div style={{
          padding: '24px',
          backgroundColor: '#f0fdf4',
          border: '1px solid #86efac',
          borderRadius: '8px',
          marginTop: '32px'
        }}>
          <h2 style={{ fontSize: '24px', marginBottom: '16px', color: '#166534' }}>
            Analysis Complete!
          </h2>
          <div style={{ color: '#166534' }}>
            <p style={{ marginBottom: '12px', fontSize: '16px' }}>{result.message}</p>
            {result.summary && (
              <div style={{ marginTop: '16px', padding: '16px', backgroundColor: 'white', borderRadius: '8px' }}>
                <h3 style={{ fontSize: '18px', marginBottom: '12px', color: '#111827' }}>Summary:</h3>
                <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                  <li style={{ padding: '8px 0', borderBottom: '1px solid #e5e7eb' }}>
                    <strong>Total:</strong> {result.summary.total_tickers || result.summary.total || 0} tickers
                  </li>
                  <li style={{ padding: '8px 0', borderBottom: '1px solid #e5e7eb' }}>
                    <strong>Successful:</strong> {result.summary.successful || 0} tickers
                  </li>
                  <li style={{ padding: '8px 0', borderBottom: '1px solid #e5e7eb' }}>
                    <strong>Failed:</strong> {result.summary.failed || 0} tickers
                  </li>
                  <li style={{ padding: '8px 0' }}>
                    <strong>Skipped:</strong> {result.summary.skipped_from_db || result.summary.skipped || 0} tickers
                  </li>
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Batch Results - Sorted by Fair Value % */}
      {loadingResults && (
        <div style={{ marginTop: '32px', textAlign: 'center', padding: '40px', color: '#6b7280' }}>
          Loading results...
        </div>
      )}

      {/* Manual Refresh Button */}
      {result && result.success && batchResults.length === 0 && !loadingResults && (
        <div style={{ marginTop: '24px', textAlign: 'center' }}>
          <button
            onClick={async () => {
              setLoadingResults(true)
              setError(null)
              try {
                const exchangeName = result.summary?.exchange || 'Custom'
                const results = await stockApi.getBatchResults(exchangeName)
                setBatchResults(results.results || [])
                if (!results.results || results.results.length === 0) {
                  setError(`No results found for exchange "${exchangeName}". Try checking the database directly.`)
                }
              } catch (err: any) {
                setError(`Failed to load results: ${err.response?.data?.detail || err.message || 'Unknown error'}`)
              } finally {
                setLoadingResults(false)
              }
            }}
            style={{
              padding: '10px 20px',
              backgroundColor: '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '14px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Refresh Results
          </button>
        </div>
      )}

      {!loadingResults && batchResults.length > 0 && (
        <div style={{ marginTop: '32px' }}>
          <h2 style={{ fontSize: '24px', marginBottom: '16px', color: '#111827' }}>
            Analysis Results ({batchResults.length} stocks)
          </h2>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '20px' }}>
            Sorted by Fair Value / Share Price % (lowest = best deals first)
          </p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
            gap: '16px'
          }}>
            {batchResults.map((stock, index) => {
              const fairValuePct = stock.fair_value_pct || 0
              const isGoodDeal = fairValuePct < 100 // Fair value is less than current price
              const color = isGoodDeal ? '#10b981' : fairValuePct < 120 ? '#f59e0b' : '#ef4444'
              
              return (
                <div
                  key={stock.ticker}
                  style={{
                    padding: '20px',
                    backgroundColor: 'white',
                    border: `2px solid ${color}`,
                    borderRadius: '12px',
                    transition: 'all 0.2s',
                    cursor: 'pointer',
                    position: 'relative'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                    e.currentTarget.style.transform = 'translateY(-2px)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.boxShadow = 'none'
                    e.currentTarget.style.transform = 'translateY(0)'
                  }}
                  onClick={() => {
                    window.location.href = `/analysis/${stock.ticker}`
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                    <div>
                      <div style={{ fontWeight: '700', fontSize: '20px', color: '#111827', marginBottom: '4px' }}>
                        {stock.ticker}
                      </div>
                      <div style={{ fontSize: '14px', color: '#6b7280', lineHeight: '1.4' }}>
                        {stock.company_name || '-'}
                      </div>
                    </div>
                    {stock.recommendation && (
                      <div style={{
                        padding: '4px 8px',
                        borderRadius: '6px',
                        fontSize: '12px',
                        fontWeight: '600',
                        backgroundColor: stock.recommendation.includes('Buy') ? '#dbeafe' : 
                                       stock.recommendation.includes('Hold') ? '#fef3c7' : '#fee2e2',
                        color: stock.recommendation.includes('Buy') ? '#1e40af' : 
                               stock.recommendation.includes('Hold') ? '#92400e' : '#991b1b'
                      }}>
                        {stock.recommendation}
                      </div>
                    )}
                  </div>
                  
                  <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px solid #e5e7eb' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ fontSize: '14px', color: '#6b7280' }}>Fair Value %</span>
                      <span style={{ 
                        fontSize: '20px', 
                        fontWeight: '700', 
                        color: color 
                      }}>
                        {formatPercent(fairValuePct, 1)}
                      </span>
                    </div>
                    
                    <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '8px' }}>
                      <div>Price: {formatPrice(stock.current_price)}</div>
                      <div>Fair Value: {formatPrice(stock.fair_value)}</div>
                      <div style={{ marginTop: '4px', color: isGoodDeal ? '#10b981' : '#6b7280' }}>
                        Margin: {formatPercent(stock.margin_of_safety_pct, 1)}
                      </div>
                    </div>
                  </div>
                  
                  <div style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #e5e7eb', fontSize: '11px', color: '#9ca3af' }}>
                    <span style={{ marginRight: '12px' }}>Health: {formatNumber(stock.financial_health_score, 0)}</span>
                    <span>Quality: {formatNumber(stock.business_quality_score, 0)}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Tips */}
      <div style={{ marginTop: '40px', padding: '20px', backgroundColor: '#f9fafb', borderRadius: '8px' }}>
        <h3 style={{ fontSize: '18px', marginBottom: '12px', color: '#111827' }}>Tips:</h3>
        <ul style={{ color: '#6b7280', lineHeight: '1.8', paddingLeft: '20px' }}>
          <li>Search for stocks using the search box - only valid tickers can be added</li>
          <li>Click on a suggestion or press Enter to add a ticker</li>
          <li>Remove tickers by clicking the × button on each card</li>
          <li>Batch analysis processes stocks with rate limiting to avoid API throttling</li>
          <li>Results are automatically saved to DynamoDB</li>
          <li>Large batches (100+ stocks) may take 30 minutes to several hours</li>
        </ul>
      </div>
    </div>
  )
}
