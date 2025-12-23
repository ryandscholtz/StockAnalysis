'use client'

import { GrowthMetrics } from '@/types/analysis'

interface GrowthMetricsProps {
  growthMetrics?: GrowthMetrics | null
  currency?: string
}

export default function GrowthMetricsComponent({ growthMetrics, currency }: GrowthMetricsProps) {
  if (!growthMetrics) {
    return null
  }

  const formatPercent = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return 'N/A'
    const sign = value >= 0 ? '+' : ''
    return `${sign}${value.toFixed(1)}%`
  }

  const getColor = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return '#6b7280'
    if (value > 15) return '#10b981' // Green for high growth
    if (value > 5) return '#3b82f6' // Blue for moderate growth
    if (value > 0) return '#f59e0b' // Yellow for low growth
    return '#ef4444' // Red for negative
  }

  return (
    <div style={{
      background: 'white',
      borderRadius: '8px',
      padding: '24px',
      boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
      marginBottom: '20px'
    }}>
      <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '20px', color: '#111827' }}>
        Growth Metrics
      </h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
        {/* Revenue Growth */}
        <div>
          <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#6b7280', marginBottom: '12px' }}>
            Revenue Growth
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {growthMetrics.revenueGrowth1Y !== null && growthMetrics.revenueGrowth1Y !== undefined && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', color: '#6b7280' }}>1 Year:</span>
                <span style={{ fontSize: '16px', fontWeight: '600', color: getColor(growthMetrics.revenueGrowth1Y) }}>
                  {formatPercent(growthMetrics.revenueGrowth1Y)}
                </span>
              </div>
            )}
            {growthMetrics.revenueGrowth3Y !== null && growthMetrics.revenueGrowth3Y !== undefined && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', color: '#6b7280' }}>3 Year CAGR:</span>
                <span style={{ fontSize: '16px', fontWeight: '600', color: getColor(growthMetrics.revenueGrowth3Y) }}>
                  {formatPercent(growthMetrics.revenueGrowth3Y)}
                </span>
              </div>
            )}
            {growthMetrics.revenueGrowth5Y !== null && growthMetrics.revenueGrowth5Y !== undefined && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', color: '#6b7280' }}>5 Year CAGR:</span>
                <span style={{ fontSize: '16px', fontWeight: '600', color: getColor(growthMetrics.revenueGrowth5Y) }}>
                  {formatPercent(growthMetrics.revenueGrowth5Y)}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Earnings Growth */}
        <div>
          <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#6b7280', marginBottom: '12px' }}>
            Earnings Growth
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {growthMetrics.earningsGrowth1Y !== null && growthMetrics.earningsGrowth1Y !== undefined && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', color: '#6b7280' }}>1 Year:</span>
                <span style={{ fontSize: '16px', fontWeight: '600', color: getColor(growthMetrics.earningsGrowth1Y) }}>
                  {formatPercent(growthMetrics.earningsGrowth1Y)}
                </span>
              </div>
            )}
            {growthMetrics.earningsGrowth3Y !== null && growthMetrics.earningsGrowth3Y !== undefined && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', color: '#6b7280' }}>3 Year CAGR:</span>
                <span style={{ fontSize: '16px', fontWeight: '600', color: getColor(growthMetrics.earningsGrowth3Y) }}>
                  {formatPercent(growthMetrics.earningsGrowth3Y)}
                </span>
              </div>
            )}
            {growthMetrics.earningsGrowth5Y !== null && growthMetrics.earningsGrowth5Y !== undefined && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', color: '#6b7280' }}>5 Year CAGR:</span>
                <span style={{ fontSize: '16px', fontWeight: '600', color: getColor(growthMetrics.earningsGrowth5Y) }}>
                  {formatPercent(growthMetrics.earningsGrowth5Y)}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* FCF Growth */}
        <div>
          <h3 style={{ fontSize: '14px', fontWeight: '500', color: '#6b7280', marginBottom: '12px' }}>
            Free Cash Flow Growth
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {growthMetrics.fcfGrowth1Y !== null && growthMetrics.fcfGrowth1Y !== undefined && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', color: '#6b7280' }}>1 Year:</span>
                <span style={{ fontSize: '16px', fontWeight: '600', color: getColor(growthMetrics.fcfGrowth1Y) }}>
                  {formatPercent(growthMetrics.fcfGrowth1Y)}
                </span>
              </div>
            )}
            {growthMetrics.fcfGrowth3Y !== null && growthMetrics.fcfGrowth3Y !== undefined && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', color: '#6b7280' }}>3 Year CAGR:</span>
                <span style={{ fontSize: '16px', fontWeight: '600', color: getColor(growthMetrics.fcfGrowth3Y) }}>
                  {formatPercent(growthMetrics.fcfGrowth3Y)}
                </span>
              </div>
            )}
            {growthMetrics.fcfGrowth5Y !== null && growthMetrics.fcfGrowth5Y !== undefined && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '13px', color: '#6b7280' }}>5 Year CAGR:</span>
                <span style={{ fontSize: '16px', fontWeight: '600', color: getColor(growthMetrics.fcfGrowth5Y) }}>
                  {formatPercent(growthMetrics.fcfGrowth5Y)}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

