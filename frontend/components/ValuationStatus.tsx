'use client'

import { StockAnalysis } from '@/types/analysis'

interface ValuationStatusProps {
  analysis: StockAnalysis
}

export default function ValuationStatus({ analysis }: ValuationStatusProps) {
  const margin = analysis.marginOfSafety
  const isValid = margin !== null && margin !== undefined && !isNaN(margin) && isFinite(margin)
  
  const getValuationStatus = () => {
    if (!isValid) return { text: 'Unknown', color: '#6b7280' }
    
    const absMargin = Math.abs(margin)
    
    if (margin > 0) {
      // Undervalued
      if (absMargin > 50) return { text: `${absMargin.toFixed(1)}% Undervalued`, color: '#059669' }
      if (absMargin > 30) return { text: `${absMargin.toFixed(1)}% Undervalued`, color: '#0d9488' }
      if (absMargin > 10) return { text: `${absMargin.toFixed(1)}% Undervalued`, color: '#d97706' }
      return { text: `${absMargin.toFixed(1)}% Undervalued`, color: '#059669' }
    } else {
      // Overvalued
      return { text: `${absMargin.toFixed(1)}% Overvalued`, color: '#dc2626' }
    }
  }

  const getWidth = () => {
    if (!isValid) return 0
    // Use absolute value for display width, clamp between 0 and 100
    return Math.min(Math.max(Math.abs(margin), 0), 100)
  }

  const status = getValuationStatus()

  return (
    <div className="card">
      <h2 style={{ fontSize: '24px', marginBottom: '24px' }}>Valuation Status</h2>
      
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '14px', color: '#6b7280' }}>Current Valuation</span>
          <span style={{ fontSize: '24px', fontWeight: '700', color: status.color }}>
            {status.text}
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
            background: status.color,
            transition: 'width 0.3s ease'
          }} />
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            color: 'white',
            fontWeight: '600',
            fontSize: '12px',
            textShadow: '0 1px 2px rgba(0,0,0,0.5)'
          }}>
            {isValid && margin > 0 ? 'Undervalued' : isValid && margin < 0 ? 'Overvalued' : 'Fair Value'}
          </div>
        </div>
      </div>

      <div style={{ fontSize: '14px', color: '#6b7280', lineHeight: '1.6' }}>
        <p>
          Valuation status compares the current market price to the calculated intrinsic value. 
          Undervalued stocks trade below their estimated fair value, while overvalued stocks 
          trade above their intrinsic worth.
        </p>
        {isValid && margin > 0 && margin < 30 && (
          <p style={{ marginTop: '12px', color: '#d97706' }}>
            💡 Moderately undervalued. Consider additional analysis before investing.
          </p>
        )}
        {isValid && margin > 30 && (
          <p style={{ marginTop: '12px', color: '#059669' }}>
            ✅ Significantly undervalued. Potential value opportunity.
          </p>
        )}
        {isValid && margin < 0 && (
          <p style={{ marginTop: '12px', color: '#dc2626' }}>
            ⚠️ Stock appears overvalued. Exercise caution.
          </p>
        )}
        {!isValid && (
          <p style={{ marginTop: '12px', color: '#6b7280' }}>
            Valuation status cannot be determined due to missing data.
          </p>
        )}
      </div>
    </div>
  )
}

