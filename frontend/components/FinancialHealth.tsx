'use client'

import { StockAnalysis } from '@/types/analysis'

interface FinancialHealthProps {
  analysis: StockAnalysis
}

export default function FinancialHealth({ analysis }: FinancialHealthProps) {
  // Handle both full analysis and simplified watchlist data
  const financialHealth = analysis.financialHealth
  
  if (!financialHealth) {
    return (
      <div className="card">
        <h3 className="card-title">Financial Health</h3>
        <p style={{ color: '#6b7280', fontStyle: 'italic' }}>
          Financial health data not available
        </p>
      </div>
    )
  }

  const score = financialHealth.score || 0
  const metrics = financialHealth.metrics || {}
  
  // Check if we have detailed metrics
  const hasDetailedMetrics = metrics && Object.keys(metrics).length > 0

  const getScoreClass = (s: number) => {
    if (s >= 70) return 'score-high'
    if (s >= 50) return 'score-medium'
    return 'score-low'
  }

  const formatRatio = (value: number | null | undefined, decimals: number = 2) => {
    if (value === null || value === undefined || isNaN(value) || !isFinite(value)) return '-'
    return value.toFixed(decimals)
  }

  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined || isNaN(value) || !isFinite(value)) return '-'
    return `${(value * 100).toFixed(1)}%`
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '24px', margin: 0 }}>Financial Health</h2>
        <span className={`score ${getScoreClass(score)}`}>
          {score.toFixed(0)}/100
        </span>
      </div>

      {hasDetailedMetrics ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px' }}>
          <div>
            <h3 style={{ fontSize: '16px', marginBottom: '12px', color: '#6b7280' }}>Liquidity</h3>
            <div className="metric">
              <span className="metric-label">Current Ratio</span>
              <span className="metric-value">{formatRatio(metrics.currentRatio)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Quick Ratio</span>
              <span className="metric-value">{formatRatio(metrics.quickRatio)}</span>
            </div>
          </div>

          <div>
            <h3 style={{ fontSize: '16px', marginBottom: '12px', color: '#6b7280' }}>Leverage</h3>
            <div className="metric">
              <span className="metric-label">Debt-to-Equity</span>
              <span className="metric-value">{formatRatio(metrics.debtToEquity)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Interest Coverage</span>
              <span className="metric-value">{formatRatio(metrics.interestCoverage)}x</span>
            </div>
          </div>

          <div>
            <h3 style={{ fontSize: '16px', marginBottom: '12px', color: '#6b7280' }}>Profitability</h3>
            <div className="metric">
              <span className="metric-label">ROE</span>
              <span className="metric-value">{formatPercent(metrics.roe)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">ROIC</span>
              <span className="metric-value">{formatPercent(metrics.roic)}</span>
            </div>
            <div className="metric">
              <span className="metric-label">ROA</span>
              <span className="metric-value">{formatPercent(metrics.roa)}</span>
            </div>
          </div>

          <div>
            <h3 style={{ fontSize: '16px', marginBottom: '12px', color: '#6b7280' }}>Cash Flow</h3>
            <div className="metric">
              <span className="metric-label">FCF Margin</span>
              <span className="metric-value">{formatPercent(metrics.fcfMargin / 100)}</span>
            </div>
          </div>
        </div>
      ) : (
        <div style={{ 
          padding: '20px', 
          backgroundColor: '#f9fafb', 
          borderRadius: '8px', 
          textAlign: 'center',
          color: '#6b7280'
        }}>
          <p style={{ margin: 0, fontSize: '14px' }}>
            Detailed financial metrics are available in the full analysis view.
          </p>
          <p style={{ margin: '8px 0 0 0', fontSize: '12px' }}>
            Click "Analyze" to see comprehensive financial health metrics.
          </p>
        </div>
      )}
    </div>
  )
}

