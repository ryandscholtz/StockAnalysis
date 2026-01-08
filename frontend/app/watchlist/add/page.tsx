'use client'

import { useState, useRef, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { stockApi, SearchResult } from '@/lib/api'

export default function AddToWatchlistPage() {
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [suggestions, setSuggestions] = useState<SearchResult[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [searchLoading, setSearchLoading] = useState<boolean>(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [adding, setAdding] = useState(false)
  const [error, setError] = useState<string>('')
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    if (searchQuery && searchQuery.trim().length >= 1) {
      setSearchLoading(true)
      searchTimeoutRef.current = setTimeout(async () => {
        try {
          const results = await stockApi.searchTickers(searchQuery.trim())
          // Ensure results is always an array
          const safeResults = Array.isArray(results) ? results : []
          setSuggestions(safeResults)
          setShowSuggestions(safeResults.length > 0)
          setSelectedIndex(-1)
        } catch (error: any) {
          // Show error if it's a connection issue
          if (error.code === 'ERR_NETWORK' || error.code === 'ECONNREFUSED' || error.message?.includes('Cannot connect')) {
            setError(error.message || 'Cannot connect to backend server')
          } else if (error.code !== 'ERR_NETWORK' && error.code !== 'ECONNREFUSED') {
            console.error('Search error:', error)
            // Only show non-connection errors briefly
            setError(error.message || 'Search failed')
            setTimeout(() => setError(''), 5000)
          }
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

  const handleSelect = async (suggestion: SearchResult) => {
    setSearchQuery(suggestion.ticker || '')
    setShowSuggestions(false)
    setSelectedIndex(-1)
    
    // Add to watchlist
    setAdding(true)
    setError('')
    try {
      await stockApi.addToWatchlist(suggestion.ticker, suggestion.companyName, suggestion.exchange)
      router.push('/watchlist')
    } catch (err: any) {
      // Use formatted error message (from api.ts interceptor)
      setError(err.message || 'Failed to add to watchlist')
    } finally {
      setAdding(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(prev => prev < suggestions.length - 1 ? prev + 1 : prev)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(prev => prev > 0 ? prev - 1 : -1)
    } else if (e.key === 'Enter' && selectedIndex >= 0 && suggestions[selectedIndex]) {
      e.preventDefault()
      handleSelect(suggestions[selectedIndex])
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
    }
  }

  return (
    <div className="container" style={{ padding: '40px 20px', maxWidth: '600px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '28px', fontWeight: '700', color: '#111827', marginBottom: '24px' }}>
        Add Stock to Watchlist
      </h1>

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

      <div style={{ position: 'relative', marginBottom: '20px' }}>
        <input
          ref={inputRef}
          type="text"
          value={searchQuery || ''}
          onChange={(e) => setSearchQuery(e.target.value || '')}
          onKeyDown={handleKeyDown}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = '#2563eb'
            setShowSuggestions(suggestions.length > 0)
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = '#d1d5db'
            // Delay hiding suggestions to allow click
            setTimeout(() => setShowSuggestions(false), 200)
          }}
          placeholder="Search for a stock ticker or company name..."
          disabled={adding}
          style={{
            width: '100%',
            padding: '12px 16px',
            fontSize: '16px',
            border: '1px solid #d1d5db',
            borderRadius: '6px',
            outline: 'none',
            transition: 'border-color 0.2s'
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

        {showSuggestions && suggestions.length > 0 && (
          <div style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            marginTop: '4px',
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '6px',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
            maxHeight: '300px',
            overflowY: 'auto',
            zIndex: 1000
          }}>
            {suggestions.map((suggestion, index) => (
              <div
                key={`${suggestion.ticker}-${index}`}
                onClick={() => handleSelect(suggestion)}
                style={{
                  padding: '12px 16px',
                  cursor: 'pointer',
                  backgroundColor: index === selectedIndex ? '#eff6ff' : 'white',
                  borderBottom: index < suggestions.length - 1 ? '1px solid #f3f4f6' : 'none'
                }}
                onMouseEnter={(e) => {
                  if (index !== selectedIndex) {
                    e.currentTarget.style.backgroundColor = '#f9fafb'
                  }
                }}
                onMouseLeave={(e) => {
                  if (index !== selectedIndex) {
                    e.currentTarget.style.backgroundColor = 'white'
                  }
                }}
              >
                <div style={{ fontWeight: '600', color: '#111827', marginBottom: '4px' }}>
                  {suggestion.ticker}
                  {suggestion.exchange && (
                    <span style={{ fontSize: '14px', color: '#6b7280', fontWeight: '400', marginLeft: '8px' }}>
                      ({suggestion.exchange})
                    </span>
                  )}
                </div>
                {suggestion.companyName && (
                  <div style={{ fontSize: '13px', color: '#6b7280' }}>
                    {suggestion.companyName}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: '12px' }}>
        <button
          onClick={() => router.back()}
          disabled={adding}
          style={{
            padding: '10px 20px',
            backgroundColor: '#f3f4f6',
            color: '#374151',
            border: 'none',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: '500',
            cursor: adding ? 'not-allowed' : 'pointer',
            opacity: adding ? 0.5 : 1
          }}
        >
          Cancel
        </button>
      </div>

      {adding && (
        <div style={{
          marginTop: '20px',
          padding: '12px',
          backgroundColor: '#eff6ff',
          borderRadius: '6px',
          color: '#1e40af',
          textAlign: 'center'
        }}>
          Adding to watchlist...
        </div>
      )}
    </div>
  )
}

