'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import StockSearch from '@/components/StockSearch'

export default function Home() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  const handleSearch = (ticker: string) => {
    if (!ticker || ticker.trim().length === 0) {
      setError('Please enter a ticker symbol')
      return
    }

    setError(null)
    router.push(`/analysis/${ticker.toUpperCase()}`)
  }

  return (
    <div className="container">
      <div style={{ textAlign: 'center', padding: '60px 20px' }}>
        <h1 style={{ fontSize: '48px', marginBottom: '16px', color: '#111827' }}>
          Stock Analysis Tool
        </h1>
        <p style={{ fontSize: '20px', color: '#6b7280', marginBottom: '40px' }}>
          Analyze stocks using Charlie Munger&apos;s investment philosophy
        </p>

        {error && <div className="error">{error}</div>}

        <StockSearch onSearch={handleSearch} />

        <div style={{ marginTop: '40px', color: '#9ca3af' }}>
          <p>Enter a stock ticker symbol to get started</p>
          <p style={{ marginTop: '8px', fontSize: '14px' }}>
            Examples: AAPL, MSFT, GOOGL, TSLA
          </p>
        </div>
      </div>
    </div>
  )
}

