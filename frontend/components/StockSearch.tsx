'use client'

import { useState, useEffect, useRef } from 'react'
import { stockApi, SearchResult } from '@/lib/api'

interface StockSearchProps {
  onSearch: (ticker: string) => void
}

export default function StockSearch({ onSearch }: StockSearchProps) {
  const [ticker, setTicker] = useState('')
  const [recentSearches, setRecentSearches] = useState<string[]>([])
  const [suggestions, setSuggestions] = useState<SearchResult[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [loading, setLoading] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    // Load recent searches from localStorage
    const saved = localStorage.getItem('stockAnalysisRecentSearches')
    if (saved) {
      try {
        setRecentSearches(JSON.parse(saved))
      } catch (e) {
        // Ignore parse errors
      }
    }
  }, [])

  useEffect(() => {
    // Debounce search
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    if (ticker.trim().length >= 1) {
      setLoading(true)
      searchTimeoutRef.current = setTimeout(async () => {
        try {
          const results = await stockApi.searchTickers(ticker.trim())
          setSuggestions(results)
          setShowSuggestions(results.length > 0)
          setSelectedIndex(-1)
        } catch (error) {
          console.error('Search error:', error)
          setSuggestions([])
          setShowSuggestions(false)
        } finally {
          setLoading(false)
        }
      }, 300) // 300ms debounce
    } else {
      setSuggestions([])
      setShowSuggestions(false)
      setLoading(false)
    }

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [ticker])

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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (ticker.trim()) {
      // If there's a selected suggestion, use that
      if (selectedIndex >= 0 && suggestions[selectedIndex]) {
        const selected = suggestions[selectedIndex]
        handleSelectSuggestion(selected)
      } else {
        // Otherwise, search with the entered ticker
        const tickerUpper = ticker.trim().toUpperCase()
        // Save to recent searches
        const updated = [tickerUpper, ...recentSearches.filter(s => s !== tickerUpper)].slice(0, 5)
        setRecentSearches(updated)
        localStorage.setItem('stockAnalysisRecentSearches', JSON.stringify(updated))
        
        setShowSuggestions(false)
        onSearch(tickerUpper)
      }
    }
  }

  const handleSelectSuggestion = (suggestion: SearchResult) => {
    setTicker(suggestion.ticker)
    setShowSuggestions(false)
    setSelectedIndex(-1)
    
    // Save to recent searches
    const updated = [suggestion.ticker, ...recentSearches.filter(s => s !== suggestion.ticker)].slice(0, 5)
    setRecentSearches(updated)
    localStorage.setItem('stockAnalysisRecentSearches', JSON.stringify(updated))
    
    onSearch(suggestion.ticker)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions || suggestions.length === 0) return

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(prev => (prev < suggestions.length - 1 ? prev + 1 : prev))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : -1))
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
      e.preventDefault()
      handleSelectSuggestion(suggestions[selectedIndex])
    } else if (e.key === 'Escape') {
      setShowSuggestions(false)
      setSelectedIndex(-1)
    }
  }

  const handleRecentClick = (recentTicker: string) => {
    setTicker(recentTicker)
    setShowSuggestions(false)
    onSearch(recentTicker)
  }

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto', position: 'relative' }}>
      <form onSubmit={handleSubmit}>
        <div style={{ display: 'flex', gap: '12px', position: 'relative' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <input
              ref={inputRef}
              type="text"
              className="input"
              placeholder="Search by ticker or company name (e.g., AAPL or Apple)"
              value={ticker}
              onChange={(e) => {
                const value = e.target.value
                setTicker(value)
                setShowSuggestions(value.trim().length >= 1)
              }}
              onKeyDown={handleKeyDown}
              onFocus={() => {
                if (suggestions.length > 0) {
                  setShowSuggestions(true)
                }
              }}
              style={{ flex: 1 }}
              autoComplete="off"
            />
            
            {/* Suggestions Dropdown */}
            {showSuggestions && (suggestions.length > 0 || loading) && (
              <div
                ref={suggestionsRef}
                style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  right: 0,
                  marginTop: '4px',
                  background: 'white',
                  border: '1px solid #d1d5db',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                  maxHeight: '300px',
                  overflowY: 'auto',
                  zIndex: 1000
                }}
              >
                {loading ? (
                  <div style={{ padding: '16px', textAlign: 'center', color: '#6b7280' }}>
                    Searching...
                  </div>
                ) : (
                  suggestions.map((suggestion, index) => (
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
                  ))
                )}
              </div>
            )}
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? '...' : 'Analyze'}
          </button>
        </div>
      </form>

      {recentSearches.length > 0 && !showSuggestions && (
        <div style={{ marginTop: '20px' }}>
          <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '8px' }}>Recent searches:</p>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {recentSearches.map((recent) => (
              <button
                key={recent}
                onClick={() => handleRecentClick(recent)}
                style={{
                  padding: '6px 12px',
                  background: '#f3f4f6',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  color: '#374151',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#e5e7eb'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = '#f3f4f6'
                }}
              >
                {recent}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

