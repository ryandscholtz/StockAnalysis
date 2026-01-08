'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import StockSearch from '@/components/StockSearch'
import MultiplePDFUpload from '@/components/MultiplePDFUpload'

export default function SingleSearchPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)
  const [showPDFUpload, setShowPDFUpload] = useState(false)
  const [uploadedTicker, setUploadedTicker] = useState<string | null>(null)

  const handleSearch = (ticker: string) => {
    if (!ticker || ticker.trim().length === 0) {
      setError('Please enter a ticker symbol')
      return
    }

    setError(null)
    router.push(`/analysis/${ticker.toUpperCase()}`)
  }

  const handlePDFItemComplete = (ticker: string) => {
    setUploadedTicker(ticker)
  }

  const handlePDFAllComplete = () => {
    if (uploadedTicker) {
      // Auto-navigate to analysis after PDF upload completes
      setTimeout(() => {
        router.push(`/analysis/${uploadedTicker.toUpperCase()}`)
      }, 1000)
    }
  }

  return (
    <div className="container" style={{ maxWidth: '1000px', margin: '40px auto', padding: '20px' }}>
      <div style={{ textAlign: 'center', marginBottom: '40px' }}>
        <h1 style={{ fontSize: '48px', marginBottom: '16px', color: '#111827' }}>
          Single Stock Analysis
        </h1>
        <p style={{ fontSize: '20px', color: '#6b7280', marginBottom: '40px' }}>
          Analyze stocks using value investing principles
        </p>
      </div>

      {/* Toggle between search and PDF upload */}
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
          Search by Ticker
        </button>
        <button
          onClick={() => router.push('/processing-data')}
          style={{
            padding: '12px 24px',
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: '500',
            transition: 'all 0.2s'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#1d4ed8'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = '#2563eb'
          }}
        >
          Upload PDF Statement
        </button>
      </div>

      {error && (
        <div style={{
          padding: '12px 16px',
          backgroundColor: '#fee2e2',
          color: '#991b1b',
          borderRadius: '8px',
          marginBottom: '24px',
          textAlign: 'center'
        }}>
          {error}
        </div>
      )}

      {!showPDFUpload ? (
        <div style={{ textAlign: 'center' }}>
          <StockSearch onSearch={handleSearch} />

          <div style={{ marginTop: '40px', color: '#9ca3af' }}>
            <p>Enter a stock ticker symbol to get started</p>
            <p style={{ marginTop: '8px', fontSize: '14px' }}>
              Examples: AAPL, MSFT, GOOGL, TSLA
            </p>
            <p style={{ marginTop: '16px', fontSize: '14px', fontStyle: 'italic' }}>
              Or upload a PDF financial statement to extract data automatically
            </p>
          </div>
        </div>
      ) : (
        <MultiplePDFUpload
          onItemComplete={handlePDFItemComplete}
          onAllComplete={handlePDFAllComplete}
        />
      )}
    </div>
  )
}

