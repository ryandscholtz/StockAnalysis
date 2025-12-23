'use client'

import { PriceRatios } from '@/types/analysis'

interface PriceRatiosProps {
  priceRatios?: PriceRatios | null
}

export default function PriceRatiosComponent({ priceRatios }: PriceRatiosProps) {
  if (!priceRatios) {
    return null
  }

  const formatRatio = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return 'N/A'
    return value.toFixed(2)
  }

  const getRatioColor = (ratio: string, value: number | null | undefined): string => {
    if (value === null || value === undefined) return '#6b7280'
    
    // Different thresholds for different ratios
    switch (ratio) {
      case 'P/E':
        if (value < 15) return '#10b981' // Green for low P/E
        if (value < 25) return '#3b82f6' // Blue for moderate
        return '#f59e0b' // Yellow for high
      case 'P/B':
        if (value < 1.5) return '#10b981'
        if (value < 3) return '#3b82f6'
        return '#f59e0b'
      case 'P/S':
        if (value < 2) return '#10b981'
        if (value < 5) return '#3b82f6'
        return '#f59e0b'
      case 'P/FCF':
        if (value < 15) return '#10b981'
        if (value < 25) return '#3b82f6'
        return '#f59e0b'
      case 'EV/EBITDA':
        if (value < 10) return '#10b981'
        if (value < 15) return '#3b82f6'
        return '#f59e0b'
      default:
        return '#6b7280'
    }
  }

  const ratios = [
    { label: 'Price-to-Earnings (P/E)', key: 'priceToEarnings', value: priceRatios.priceToEarnings, abbr: 'P/E' },
    { label: 'Price-to-Book (P/B)', key: 'priceToBook', value: priceRatios.priceToBook, abbr: 'P/B' },
    { label: 'Price-to-Sales (P/S)', key: 'priceToSales', value: priceRatios.priceToSales, abbr: 'P/S' },
    { label: 'Price-to-FCF (P/FCF)', key: 'priceToFCF', value: priceRatios.priceToFCF, abbr: 'P/FCF' },
    { label: 'EV/EBITDA', key: 'enterpriseValueToEBITDA', value: priceRatios.enterpriseValueToEBITDA, abbr: 'EV/EBITDA' },
  ]

  return (
    <div style={{
      background: 'white',
      borderRadius: '8px',
      padding: '24px',
      boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
      marginBottom: '20px'
    }}>
      <h2 style={{ fontSize: '20px', fontWeight: '600', marginBottom: '20px', color: '#111827' }}>
        Valuation Ratios
      </h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px' }}>
        {ratios.map((ratio) => {
          if (ratio.value === null || ratio.value === undefined) return null
          
          return (
            <div
              key={ratio.key}
              style={{
                padding: '16px',
                background: '#f9fafb',
                borderRadius: '6px',
                border: '1px solid #e5e7eb'
              }}
            >
              <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '8px' }}>
                {ratio.label}
              </div>
              <div style={{ fontSize: '24px', fontWeight: '700', color: getRatioColor(ratio.abbr, ratio.value) }}>
                {formatRatio(ratio.value)}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

