'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { stockApi, StockAnalysis } from '@/lib/api'
import { formatPrice } from '@/lib/currency'
import AnalysisCard from '@/components/AnalysisCard'
import MarginOfSafety from '@/components/MarginOfSafety'
import ValuationChart from '@/components/ValuationChart'
import FinancialHealth from '@/components/FinancialHealth'
import BusinessQuality from '@/components/BusinessQuality'
import GrowthMetrics from '@/components/GrowthMetrics'
import PriceRatios from '@/components/PriceRatios'
import MissingDataPrompt from '@/components/MissingDataPrompt'
import PDFUpload from '@/components/PDFUpload'
import DataQualityWarnings from '@/components/DataQualityWarnings'

export default function AnalysisPage() {
  const params = useParams()
  const router = useRouter()
  const ticker = params.ticker as string

  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState<{ step: number; total: number; task: string } | null>(null)

  useEffect(() => {
    if (ticker) {
      loadAnalysis()
    }
  }, [ticker])

  // Normalize ticker: remove exchange prefix (e.g., "NYSE: BRK.B" -> "BRK-B")
  // Preserve international exchange suffixes (e.g., "MRF.JO" -> "MRF.JO")
  const normalizeTicker = (t: string): string => {
    // Remove exchange prefix (NYSE:, NASDAQ:, etc.)
    let normalized = t.replace(/^[A-Z]+:\s*/i, '')
    
    // Common international exchange suffixes to preserve
    const exchangeSuffixes = ['.JO', '.L', '.TO', '.PA', '.DE', '.HK', '.SS', '.SZ', '.T', '.AS', '.BR', '.MX', '.SA', '.SW', '.VI', '.ST', '.OL', '.CO', '.HE', '.IC', '.LS', '.MC', '.MI', '.NX', '.TA', '.TW', '.V', '.WA']
    
    // Check if ticker ends with an exchange suffix
    const hasExchangeSuffix = exchangeSuffixes.some(suffix => normalized.toUpperCase().endsWith(suffix))
    
    if (hasExchangeSuffix) {
      // Preserve the dot before the exchange suffix
      // Only replace dots that are NOT part of an exchange suffix
      const parts = normalized.split('.')
      if (parts.length > 1) {
        const lastPart = parts[parts.length - 1]
        // If last part looks like an exchange code (2-3 letters), preserve it
        if (lastPart.length <= 3 && /^[A-Z]{2,3}$/i.test(lastPart)) {
          // Keep the last dot, replace others with hyphens
          const mainPart = parts.slice(0, -1).join('-')
          normalized = `${mainPart}.${lastPart}`
        } else {
          // Not an exchange suffix, replace all dots
          normalized = normalized.replace(/\./g, '-')
        }
      }
    } else {
      // No exchange suffix, replace dots with hyphens for yfinance compatibility (BRK.B -> BRK-B)
      normalized = normalized.replace(/\./g, '-')
    }
    
    return normalized.toUpperCase()
  }

  const loadAnalysis = async () => {
    setLoading(true)
    setError(null)
    setProgress(null)
    try {
      const normalizedTicker = normalizeTicker(ticker)
      console.log('Starting analysis for', normalizedTicker, '(original:', ticker, ')')
      const data = await stockApi.analyzeStock(normalizedTicker, (update) => {
        console.log('Progress callback received:', update)
        if (update.type === 'progress') {
          setProgress({
            step: update.step || 0,
            total: update.total || 8,
            task: update.task || ''
          })
        }
      })
      console.log('Analysis complete:', data)
      setAnalysis(data)
    } catch (err: any) {
      console.error('Analysis error:', err)
      setError(err.response?.data?.detail || err.message || 'Failed to load analysis')
    } finally {
      setLoading(false)
      setProgress(null)
    }
  }

  if (loading) {
    return (
      <div className="container">
        <div className="loading">
          <h2 style={{ fontSize: '24px', marginBottom: '20px' }}>Analyzing {ticker}...</h2>
          
          {progress && (
            <div style={{ 
              maxWidth: '600px', 
              margin: '0 auto',
              background: 'white',
              padding: '24px',
              borderRadius: '8px',
              boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)'
            }}>
              <div style={{ marginBottom: '16px' }}>
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  marginBottom: '8px',
                  fontSize: '14px',
                  color: '#6b7280'
                }}>
                  <span>Step {progress.step} of {progress.total || 8}</span>
                  <span>{Math.round((progress.step / (progress.total || 8)) * 100)}%</span>
                </div>
                <div style={{
                  width: '100%',
                  height: '8px',
                  background: '#e5e7eb',
                  borderRadius: '4px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${(progress.step / (progress.total || 8)) * 100}%`,
                    height: '100%',
                    background: '#2563eb',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>
              
              <p style={{ 
                fontSize: '16px', 
                color: '#111827',
                fontWeight: '500',
                margin: 0
              }}>
                {progress.task}
              </p>
            </div>
          )}
          
          {!progress && (
            <p style={{ marginTop: '8px', fontSize: '14px', color: '#9ca3af' }}>
              Initializing analysis...
            </p>
          )}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container">
        <div className="error">
          <h2>Error</h2>
          <p>{error}</p>
          <button
            className="btn btn-primary"
            onClick={() => router.push('/')}
            style={{ marginTop: '16px' }}
          >
            Back to Search
          </button>
        </div>
      </div>
    )
  }

  if (!analysis) {
    return null
  }

  return (
    <div className="container">
      <div style={{ marginBottom: '20px' }}>
        <button
          onClick={() => router.push('/')}
          style={{
            background: 'none',
            border: 'none',
            color: '#2563eb',
            cursor: 'pointer',
            fontSize: '16px',
            marginBottom: '20px'
          }}
        >
          ← Back to Search
        </button>
        <h1 style={{ fontSize: '36px', marginBottom: '8px' }}>
          {analysis.companyName} ({analysis.ticker})
        </h1>
        <p style={{ fontSize: '20px', color: '#6b7280' }}>
          Current Price: {formatPrice(analysis.currentPrice, analysis.currency)}
          {analysis.currency && analysis.currency !== 'USD' && (
            <span style={{ fontSize: '14px', marginLeft: '8px', color: '#9ca3af' }}>
              ({analysis.currency})
            </span>
          )}
        </p>
      </div>

      {/* Show data quality warnings first */}
      <DataQualityWarnings warnings={analysis.dataQualityWarnings} />
      
      {/* Show missing data prompt if fair value is 0 or if data is missing */}
      {(analysis.fairValue === 0 || (analysis.missingData && analysis.missingData.has_missing_data)) && (
        <>
          <PDFUpload
            ticker={analysis.ticker}
            onDataExtracted={() => {
              // Reload analysis after PDF data is extracted
              loadAnalysis()
            }}
          />
          <MissingDataPrompt
            ticker={analysis.ticker}
            missingData={analysis.missingData || {
              income_statement: [],
              balance_sheet: [],
              cashflow: [],
              key_metrics: [],
              has_missing_data: true
            }}
            onDataAdded={() => {
              // Reload analysis after data is added
              loadAnalysis()
            }}
          />
        </>
      )}

      <AnalysisCard analysis={analysis} />
      <MarginOfSafety analysis={analysis} />
      <ValuationChart analysis={analysis} />
      <PriceRatios priceRatios={analysis.priceRatios} />
      <GrowthMetrics growthMetrics={analysis.growthMetrics} currency={analysis.currency} />
      <FinancialHealth analysis={analysis} />
      <BusinessQuality analysis={analysis} />
    </div>
  )
}

