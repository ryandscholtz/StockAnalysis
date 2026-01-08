'use client'

import { StockAnalysis } from '@/types/analysis'
import { formatPrice } from '@/lib/currency'

interface ValuationChartProps {
  analysis: StockAnalysis
}

export default function ValuationChart({ analysis }: ValuationChartProps) {
  // Get current price - use 0 if not available or is placeholder (1.0)
  const currentPrice = (analysis.currentPrice && Math.abs(analysis.currentPrice - 1.0) > 0.01) 
    ? analysis.currentPrice 
    : 0
  
  // Filter out null/undefined/NaN values for max calculation (include currentPrice even if 0 for scaling)
  const validValues = [
    currentPrice > 0 ? currentPrice : null,
    analysis.fairValue,
    analysis.valuation.dcf,
    analysis.valuation.earningsPower,
    analysis.valuation.assetBased
  ].filter((v): v is number => v !== null && v !== undefined && !isNaN(v) && isFinite(v) && v > 0)
  
  const maxValue = validValues.length > 0 ? Math.max(...validValues) : 1

  const getBarWidth = (value: number | null | undefined) => {
    if (value === null || value === undefined || isNaN(value) || !isFinite(value) || value <= 0) return 0
    return (value / maxValue) * 100
  }

  const Bar = ({ label, value, color }: { label: string; value: number | null | undefined; color: string }) => {
    // Value is valid if it's a number (including 0), but bar only shows if > 0
    const isValidNumber = value !== null && value !== undefined && !isNaN(value) && isFinite(value)
    const showBar = isValidNumber && value > 0
    return (
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span style={{ fontSize: '14px', fontWeight: '500' }}>{label}</span>
          <span style={{ fontSize: '14px', color: isValidNumber ? '#6b7280' : '#9ca3af' }}>
            {formatPrice(value, analysis.currency)}
          </span>
        </div>
        <div style={{
          width: '100%',
          height: '24px',
          background: '#e5e7eb',
          borderRadius: '4px',
          overflow: 'hidden'
        }}>
          {showBar && (
            <div style={{
              width: `${getBarWidth(value)}%`,
              height: '100%',
              background: color,
              transition: 'width 0.3s ease'
            }} />
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <h2 style={{ fontSize: '24px', marginBottom: '24px' }}>Valuation Breakdown</h2>
      
      {/* Always show current price above Fair Value - show 0 if not available */}
      <Bar label="Current Price" value={currentPrice > 0 ? currentPrice : 0} color="#dc2626" />
      <Bar label="Fair Value (Weighted)" value={analysis.fairValue ?? null} color="#059669" />
      <Bar label="DCF Model" value={analysis.valuation?.dcf ?? null} color="#0d9488" />
      <Bar label="Earnings Power Value" value={analysis.valuation?.earningsPower ?? null} color="#0891b2" />
      <Bar label="Asset-Based" value={analysis.valuation?.assetBased ?? null} color="#0284c7" />

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

