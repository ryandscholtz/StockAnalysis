'use client'

import { StockAnalysis } from '@/types/analysis'
import { formatPrice } from '@/lib/currency'

interface ValuationChartProps {
  analysis: StockAnalysis
  availablePresets?: string[]
  currentPreset?: string | null
  onPresetChange?: (preset: string) => void
  fmtPrice?: (amount: number | null | undefined) => string
}

const MODEL_COLORS = {
  dcf:  '#f59e0b',  // amber
  pe:   '#7c3aed',  // violet
  epv:  '#0891b2',  // cyan
  book: '#4f46e5',  // indigo
}

const formatPreset = (key: string) =>
  key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())

export default function ValuationChart({
  analysis,
  availablePresets,
  currentPreset,
  onPresetChange,
  fmtPrice,
}: ValuationChartProps) {
  const fmt = fmtPrice ?? ((v: number | null | undefined) => formatPrice(v, analysis.currency))
  const currentPrice = (analysis.currentPrice && Math.abs(analysis.currentPrice - 1.0) > 0.01)
    ? analysis.currentPrice
    : 0

  const dcfValue = analysis.valuation?.dcf ?? null
  const peValue = analysis.valuation?.peValue ?? null
  const earningsPowerValue = analysis.valuation?.earningsPower ?? null
  const bookValue = analysis.valuation?.bookValue ?? null

  const w = analysis.analysisWeights ?? { dcf_weight: 0.40, epv_weight: 0.20, asset_weight: 0.10 }
  const peWeight = Math.max(0, 1 - w.dcf_weight - w.epv_weight - w.asset_weight)

  const validValues = [
    currentPrice > 0 ? currentPrice : null,
    analysis.fairValue,
    dcfValue,
    peValue,
    earningsPowerValue,
    bookValue,
  ].filter((v): v is number => v !== null && v !== undefined && !isNaN(v) && isFinite(v) && v > 0)

  const maxValue = validValues.length > 0 ? Math.max(...validValues) : 1

  const getBarWidth = (value: number | null | undefined) => {
    if (value === null || value === undefined || isNaN(value) || !isFinite(value) || value <= 0) return 0
    return (value / maxValue) * 100
  }

  const Bar = ({
    label,
    weight,
    value,
    color,
  }: {
    label: string
    weight?: number
    value: number | null | undefined
    color: string
  }) => {
    const isValidNumber = value !== null && value !== undefined && !isNaN(value) && isFinite(value)
    const showBar = isValidNumber && value > 0
    return (
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', alignItems: 'baseline' }}>
          <span style={{ fontSize: '14px', fontWeight: '500' }}>
            {label}
            {weight !== undefined && (
              <span style={{ fontSize: '11px', color: '#9ca3af', marginLeft: '6px', fontWeight: 400 }}>
                {(weight * 100).toFixed(0)}%
              </span>
            )}
          </span>
          <span style={{ fontSize: '14px', color: isValidNumber ? '#6b7280' : '#9ca3af' }}>
            {fmt(value)}
          </span>
        </div>
        <div style={{ width: '100%', height: '24px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
          {showBar && (
            <div style={{ width: `${getBarWidth(value)}%`, height: '100%', background: color, transition: 'width 0.3s ease' }} />
          )}
        </div>
      </div>
    )
  }

  const StackedFairValueBar = () => {
    const fairValue = analysis.fairValue
    const fairBarWidth = getBarWidth(fairValue)

    const segments = [
      { key: 'dcf',  value: dcfValue,          weight: w.dcf_weight,   color: MODEL_COLORS.dcf },
      { key: 'pe',   value: peValue,            weight: peWeight,       color: MODEL_COLORS.pe },
      { key: 'epv',  value: earningsPowerValue, weight: w.epv_weight,   color: MODEL_COLORS.epv },
      { key: 'book', value: bookValue,          weight: w.asset_weight, color: MODEL_COLORS.book },
    ]

    return (
      <div style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
          <span style={{ fontSize: '14px', fontWeight: '600' }}>Fair Value (Weighted)</span>
          <span style={{ fontSize: '14px', color: fairValue ? '#6b7280' : '#9ca3af' }}>
            {fmt(fairValue ?? null)}
          </span>
        </div>
        <div style={{ width: '100%', height: '24px', background: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
          <div style={{ display: 'flex', height: '100%', width: `${fairBarWidth}%` }}>
            {segments.map(seg => {
              if (!seg.value || seg.value <= 0 || !fairValue || fairValue <= 0) return null
              const contribution = seg.value * seg.weight
              const segPct = (contribution / fairValue) * 100
              return (
                <div
                  key={seg.key}
                  style={{ width: `${segPct}%`, height: '100%', background: seg.color, flexShrink: 0 }}
                  title={`${formatPreset(seg.key)}: ${fmt(contribution)} (${(seg.weight * 100).toFixed(0)}% weight)`}
                />
              )
            })}
          </div>
        </div>
      </div>
    )
  }

  const Legend = () => (
    <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '20px' }}>
      {[
        { color: MODEL_COLORS.dcf,  label: 'DCF' },
        { color: MODEL_COLORS.pe,   label: 'P/E' },
        { color: MODEL_COLORS.epv,  label: 'EPV' },
        { color: MODEL_COLORS.book, label: 'Book Value' },
      ].map(({ color, label }) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#6b7280' }}>
          <div style={{ width: '12px', height: '12px', borderRadius: '2px', background: color, flexShrink: 0 }} />
          {label}
        </div>
      ))}
    </div>
  )

  return (
    <div className="card">
      {/* Header row: title + preset selector */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '8px' }}>
        <h2 style={{ fontSize: '24px', margin: 0 }}>Valuation Breakdown</h2>
        {availablePresets && availablePresets.length > 0 && onPresetChange && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: '#6b7280' }}>Preset</span>
            <select
              value={currentPreset ?? 'automatic'}
              onChange={e => onPresetChange(e.target.value)}
              style={{
                fontSize: '13px',
                fontWeight: '500',
                padding: '4px 28px 4px 10px',
                borderRadius: '6px',
                border: '1px solid #d1d5db',
                background: 'white',
                color: '#111827',
                cursor: 'pointer',
                appearance: 'auto',
              }}
            >
              <option value="automatic">— Automatic —</option>
              {availablePresets.map(p => (
                <option key={p} value={p}>{formatPreset(p)}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      <Legend />

      <Bar label="Current Price" value={currentPrice > 0 ? currentPrice : 0} color="#334155" />
      <StackedFairValueBar />
      <div style={{ borderLeft: '3px solid #e5e7eb', marginLeft: '12px', paddingLeft: '16px' }}>
        <Bar label="DCF Model"            weight={w.dcf_weight}   value={dcfValue}           color={MODEL_COLORS.dcf} />
        <Bar label="P/E Model"            weight={peWeight}       value={peValue}            color={MODEL_COLORS.pe} />
        <Bar label="Earnings Power Value" weight={w.epv_weight}   value={earningsPowerValue} color={MODEL_COLORS.epv} />
        <Bar label="Book Value"           weight={w.asset_weight} value={bookValue}          color={MODEL_COLORS.book} />
      </div>

      <div style={{ marginTop: '24px', padding: '16px', background: '#f9fafb', borderRadius: '6px' }}>
        <p style={{ fontSize: '14px', color: '#6b7280', lineHeight: '1.6', margin: 0 }}>
          The fair value bar shows the weighted contribution of each model. Hover over each segment to see its individual contribution.
        </p>
      </div>
    </div>
  )
}
