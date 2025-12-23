'use client'

import { StockAnalysis } from '@/lib/api'

interface MarginOfSafetyProps {
  analysis: StockAnalysis
}

export default function MarginOfSafety({ analysis }: MarginOfSafetyProps) {
  const margin = analysis.marginOfSafety
  const getColor = () => {
    if (margin > 50) return '#059669'
    if (margin > 30) return '#0d9488'
    if (margin > 10) return '#d97706'
    return '#dc2626'
  }

  const getWidth = () => {
    // Clamp between 0 and 100 for display
    return Math.min(Math.max(margin, 0), 100)
  }

  return (
    <div className="card">
      <h2 style={{ fontSize: '24px', marginBottom: '24px' }}>Margin of Safety</h2>
      
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '14px', color: '#6b7280' }}>Margin of Safety</span>
          <span style={{ fontSize: '24px', fontWeight: '700', color: getColor() }}>
            {margin > 0 ? '+' : ''}{margin.toFixed(1)}%
          </span>
        </div>
        <div style={{
          width: '100%',
          height: '32px',
          background: '#e5e7eb',
          borderRadius: '16px',
          overflow: 'hidden',
          position: 'relative'
        }}>
          <div style={{
            width: `${getWidth()}%`,
            height: '100%',
            background: getColor(),
            transition: 'width 0.3s ease'
          }} />
          {margin < 0 && (
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              color: '#dc2626',
              fontWeight: '600',
              fontSize: '12px'
            }}>
              Overvalued
            </div>
          )}
        </div>
      </div>

      <div style={{ fontSize: '14px', color: '#6b7280', lineHeight: '1.6' }}>
        <p>
          Margin of Safety represents the discount between the current market price 
          and the calculated intrinsic value. A higher margin provides a buffer 
          against estimation errors and market volatility.
        </p>
        {margin < 30 && (
          <p style={{ marginTop: '12px', color: '#d97706' }}>
            ⚠️ Margin below recommended 30% threshold. Consider additional risk factors.
          </p>
        )}
      </div>
    </div>
  )
}

