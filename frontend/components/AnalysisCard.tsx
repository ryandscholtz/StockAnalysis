'use client'

import { StockAnalysis } from '@/lib/api'
import { formatPrice } from '@/lib/currency'

interface AnalysisCardProps {
  analysis: StockAnalysis
}

export default function AnalysisCard({ analysis }: AnalysisCardProps) {
  const getRecommendationClass = (rec: string) => {
    const classes: Record<string, string> = {
      'Strong Buy': 'recommendation-strong-buy',
      'Buy': 'recommendation-buy',
      'Hold': 'recommendation-hold',
      'Avoid': 'recommendation-avoid',
    }
    return classes[rec] || ''
  }

  return (
    <div className="card">
      <h2 style={{ fontSize: '24px', marginBottom: '24px' }}>Key Metrics</h2>
      
      <div className="metric">
        <span className="metric-label">Fair Value Per Share</span>
        <span className="metric-value" style={{ color: analysis.fairValue && analysis.fairValue > 0 ? '#059669' : '#6b7280', fontSize: '28px' }}>
          {formatPrice(analysis.fairValue, analysis.currency)}
        </span>
        {(!analysis.fairValue || analysis.fairValue === 0) && (
          <div style={{ marginTop: '8px', fontSize: '12px', color: '#6b7280', fontStyle: 'italic' }}>
            Insufficient data to calculate fair value
          </div>
        )}
      </div>

      {/* Only show price if it's valid (not the 1.0 placeholder) */}
      {analysis.currentPrice && Math.abs(analysis.currentPrice - 1.0) > 0.01 && (
        <div className="metric">
          <span className="metric-label">Current Price Per Share</span>
          <span className="metric-value">
            {formatPrice(analysis.currentPrice, analysis.currency)}
          </span>
        </div>
      )}

      <div className="metric">
        <span className="metric-label">Margin of Safety</span>
        <span className="metric-value" style={{ color: analysis.marginOfSafety && analysis.marginOfSafety > 0 ? '#059669' : analysis.marginOfSafety && analysis.marginOfSafety < 0 ? '#dc2626' : '#6b7280' }}>
          {analysis.marginOfSafety !== null && analysis.marginOfSafety !== undefined && !isNaN(analysis.marginOfSafety)
            ? `${analysis.marginOfSafety > 0 ? '+' : ''}${analysis.marginOfSafety.toFixed(1)}%`
            : '-'}
        </span>
      </div>

      <div className="metric">
        <span className="metric-label">Upside Potential</span>
        <span className="metric-value" style={{ color: analysis.upsidePotential && analysis.upsidePotential > 0 ? '#059669' : analysis.upsidePotential && analysis.upsidePotential < 0 ? '#dc2626' : '#6b7280' }}>
          {analysis.upsidePotential !== null && analysis.upsidePotential !== undefined && !isNaN(analysis.upsidePotential)
            ? `${analysis.upsidePotential > 0 ? '+' : ''}${analysis.upsidePotential.toFixed(1)}%`
            : '-'}
        </span>
      </div>

      <div className="metric">
        <span className="metric-label">Price to Intrinsic Value</span>
        <span className="metric-value">
          {analysis.priceToIntrinsicValue !== null && analysis.priceToIntrinsicValue !== undefined && !isNaN(analysis.priceToIntrinsicValue)
            ? `${analysis.priceToIntrinsicValue.toFixed(2)}x`
            : '-'}
        </span>
      </div>

      <div style={{ marginTop: '24px', padding: '16px', background: '#f9fafb', borderRadius: '6px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <span className="metric-label">Recommendation</span>
          <span className={getRecommendationClass(analysis.recommendation)} style={{ fontSize: '20px' }}>
            {analysis.recommendation}
          </span>
        </div>
        <p style={{ fontSize: '14px', color: '#6b7280', lineHeight: '1.6' }}>
          {analysis.recommendationReasoning}
        </p>
      </div>
    </div>
  )
}

