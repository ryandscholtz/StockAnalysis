'use client'

import { StockAnalysis } from '@/lib/api'

interface FinancialHealthProps {
  analysis: StockAnalysis
}

export default function FinancialHealth({ analysis }: FinancialHealthProps) {
  const score = analysis.financialHealth.score
  const metrics = analysis.financialHealth.metrics

  const getScoreClass = (s: number) => {
    if (s >= 70) return 'score-high'
    if (s >= 50) return 'score-medium'
    return 'score-low'
  }

  const formatRatio = (value: number, decimals: number = 2) => {
    return value.toFixed(decimals)
  }

  const formatPercent = (value: number) => {
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
    </div>
  )
}

