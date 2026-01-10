'use client'

import { useState } from 'react'
import { searchTickers } from '@/lib/enhanced-search'

export default function SearchDebugPage() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[]>([])
  const [error, setError] = useState('')

  const handleSearch = () => {
    try {
      console.log('Searching for:', query)
      const searchResults = searchTickers(query, 10)
      console.log('Search results:', searchResults)
      setResults(searchResults)
      setError('')
    } catch (err: any) {
      console.error('Search error:', err)
      setError(err.message)
      setResults([])
    }
  }

  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto' }}>
      <h1>Search Debug Page</h1>
      
      <div style={{ marginBottom: '20px' }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for stocks (e.g., AAPL, coke, tesla)"
          style={{
            padding: '10px',
            width: '300px',
            marginRight: '10px',
            border: '1px solid #ccc',
            borderRadius: '4px'
          }}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button
          onClick={handleSearch}
          style={{
            padding: '10px 20px',
            background: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Search
        </button>
      </div>

      {error && (
        <div style={{
          padding: '10px',
          background: '#f8d7da',
          border: '1px solid #f5c6cb',
          borderRadius: '4px',
          color: '#721c24',
          marginBottom: '20px'
        }}>
          Error: {error}
        </div>
      )}

      <div>
        <h3>Results ({results.length}):</h3>
        {results.length === 0 ? (
          <p>No results found. Try searching for: AAPL, KO, coke, tesla, apple, microsoft</p>
        ) : (
          results.map((result, index) => (
            <div
              key={index}
              style={{
                padding: '10px',
                margin: '5px 0',
                background: '#f8f9fa',
                border: '1px solid #dee2e6',
                borderRadius: '4px'
              }}
            >
              <strong>{result.ticker}</strong> - {result.companyName} ({result.exchange})
              {result.aliases && (
                <div style={{ fontSize: '12px', color: '#6c757d', marginTop: '4px' }}>
                  Aliases: {result.aliases.join(', ')}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <div style={{ marginTop: '40px', padding: '20px', background: '#e9ecef', borderRadius: '4px' }}>
        <h4>Test Cases:</h4>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {['AAPL', 'KO', 'coke', 'tesla', 'apple', 'microsoft', 'TSLA', 'GOOGL'].map(testQuery => (
            <button
              key={testQuery}
              onClick={() => {
                setQuery(testQuery)
                setTimeout(() => {
                  try {
                    const searchResults = searchTickers(testQuery, 10)
                    setResults(searchResults)
                    setError('')
                  } catch (err: any) {
                    setError(err.message)
                    setResults([])
                  }
                }, 100)
              }}
              style={{
                padding: '5px 10px',
                background: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '12px'
              }}
            >
              {testQuery}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}