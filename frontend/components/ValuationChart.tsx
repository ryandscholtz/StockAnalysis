'use client'

import { StockAnalysis } from '@/lib/api'
import { formatPrice } from '@/lib/currency'

interface ValuationChartProps {
  analysis: StockAnalysis
}

export default function ValuationChart({ analysis }: ValuationChartProps) {
  const maxValue = Math.max(analysis.currentPrice, analysis.fairValue, ...Object.values(analysis.valuation))

  const getBarWidth = (value: number) => {
    return (value / maxValue) * 100
  }

  const Bar = ({ label, value, color }: { label: string; value: number; color: string }) => (
    <div style={{ marginBottom: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
        <span style={{ fontSize: '14px', fontWeight: '500' }}>{label}</span>
        <span style={{ fontSize: '14px', color: '#6b7280' }}>{formatPrice(value, analysis.currency)}</span>
      </div>
      <div style={{
        width: '100%',
        height: '24px',
        background: '#e5e7eb',
        borderRadius: '4px',
        overflow: 'hidden'
      }}>
        <div style={{
          width: `${getBarWidth(value)}%`,
          height: '100%',
          background: color,
          transition: 'width 0.3s ease'
        }} />
      </div>
    </div>
  )

  return (
    <div className="card">
      <h2 style={{ fontSize: '24px', marginBottom: '24px' }}>Valuation Breakdown</h2>
      
      <Bar label="Current Price" value={analysis.currentPrice} color="#dc2626" />
      <Bar label="Fair Value (Weighted)" value={analysis.fairValue} color="#059669" />
      <Bar label="DCF Model" value={analysis.valuation.dcf} color="#0d9488" />
      <Bar label="Earnings Power Value" value={analysis.valuation.earningsPower} color="#0891b2" />
      <Bar label="Asset-Based" value={analysis.valuation.assetBased} color="#0284c7" />

      <div style={{ marginTop: '24px', padding: '16px', background: '#f9fafb', borderRadius: '6px' }}>
        <p style={{ fontSize: '14px', color: '#6b7280', lineHeight: '1.6' }}>
          The fair value is calculated using a weighted average of three valuation methods:
          Discounted Cash Flow (DCF), Earnings Power Value (EPV), and Asset-Based valuation.
          The weights depend on the business type (growth, mature, asset-heavy, or distressed).
        </p>
      </div>
    </div>
  )
}

