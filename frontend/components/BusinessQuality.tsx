'use client'

import { StockAnalysis } from '@/types/analysis'

interface BusinessQualityProps {
  analysis: StockAnalysis
}

export default function BusinessQuality({ analysis }: BusinessQualityProps) {
  // Handle both full analysis and simplified watchlist data
  const businessQuality = analysis.businessQuality
  
  if (!businessQuality) {
    return (
      <div className="card">
        <h3 className="card-title">Business Quality</h3>
        <p style={{ color: '#6b7280', fontStyle: 'italic' }}>
          Business quality data not available
        </p>
      </div>
    )
  }

  const score = businessQuality.score || 0
  const moats = businessQuality.moatIndicators || []
  const position = businessQuality.competitivePosition || 'Not available'
  
  // Check if we have detailed business quality data
  const hasDetailedData = moats.length > 0 || (position && position !== 'Not available')

  const getScoreClass = (s: number) => {
    if (s >= 70) return 'score-high'
    if (s >= 50) return 'score-medium'
    return 'score-low'
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '24px', margin: 0 }}>Business Quality</h2>
        <span className={`score ${getScoreClass(score)}`}>
          {score.toFixed(0)}/100
        </span>
      </div>

      {hasDetailedData ? (
        <>
          <div style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '16px', marginBottom: '12px', color: '#6b7280' }}>Competitive Position</h3>
            <p style={{ fontSize: '18px', fontWeight: '600', color: '#111827' }}>{position}</p>
          </div>

          {moats.length > 0 ? (
            <div>
              <h3 style={{ fontSize: '16px', marginBottom: '12px', color: '#6b7280' }}>Competitive Moats</h3>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {moats.map((moat, index) => (
                  <span
                    key={index}
                    style={{
                      padding: '6px 12px',
                      background: '#d1fae5',
                      color: '#065f46',
                      borderRadius: '6px',
                      fontSize: '14px',
                      fontWeight: '500'
                    }}
                  >
                    {moat}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div style={{ padding: '16px', background: '#fef3c7', borderRadius: '6px' }}>
              <p style={{ fontSize: '14px', color: '#92400e' }}>
                No significant competitive moats identified. This may indicate higher competition risk.
              </p>
            </div>
          )}
        </>
      ) : (
        <div style={{ 
          padding: '20px', 
          backgroundColor: '#f9fafb', 
          borderRadius: '8px', 
          textAlign: 'center',
          color: '#6b7280'
        }}>
          <p style={{ margin: 0, fontSize: '14px' }}>
            Detailed business quality analysis is available in the full analysis view.
          </p>
          <p style={{ margin: '8px 0 0 0', fontSize: '12px' }}>
            Click "Analyze" to see competitive moats and positioning details.
          </p>
        </div>
      )}

      <div style={{ marginTop: '24px', padding: '16px', background: '#f9fafb', borderRadius: '6px' }}>
        <p style={{ fontSize: '14px', color: '#6b7280', lineHeight: '1.6' }}>
          Business quality is assessed based on competitive moats (brand strength, network effects, 
          cost advantages, regulatory barriers), market position, business model quality, and 
          financial characteristics. Higher scores indicate more durable competitive advantages.
        </p>
      </div>
    </div>
  )
}

