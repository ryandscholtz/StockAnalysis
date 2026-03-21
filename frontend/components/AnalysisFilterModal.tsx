'use client'

import React from 'react'

// ─── Shared types ─────────────────────────────────────────────────────────────

export interface FilterRange { min: string; max: string }

export interface AnalysisFilterState {
  peRatio:         FilterRange
  pbRatio:         FilterRange
  psRatio:         FilterRange
  evToEbitda:      FilterRange
  marginOfSafety:  FilterRange
  upsidePotential: FilterRange
  price:           FilterRange
  fairValue:       FilterRange
}

export type RecFilterType = 'overall' | 'model' | 'ai'

export const EMPTY_ANALYSIS_FILTERS: AnalysisFilterState = {
  peRatio:         { min: '', max: '' },
  pbRatio:         { min: '', max: '' },
  psRatio:         { min: '', max: '' },
  evToEbitda:      { min: '', max: '' },
  marginOfSafety:  { min: '', max: '' },
  upsidePotential: { min: '', max: '' },
  price:           { min: '', max: '' },
  fairValue:       { min: '', max: '' },
}

export const REC_OPTIONS = ['Strong Buy', 'Buy', 'Hold', 'Reduce', 'Avoid', 'Unrated'] as const

export const REC_COLOR: Record<string, string> = {
  'Strong Buy': '#10b981',
  'Buy':        '#3b82f6',
  'Hold':       '#f59e0b',
  'Reduce':     '#f97316',
  'Avoid':      '#ef4444',
  'Unrated':    '#6b7280',
}

const FILTER_GROUPS: {
  label: string
  rows: { key: keyof AnalysisFilterState; label: string; unit?: string; placeholder?: string }[]
}[] = [
  { label: 'Valuation Ratios', rows: [
    { key: 'peRatio',    label: 'P/E Ratio',  placeholder: 'e.g. 15' },
    { key: 'pbRatio',    label: 'P/B Ratio',  placeholder: 'e.g. 2'  },
    { key: 'psRatio',    label: 'P/S Ratio',  placeholder: 'e.g. 3'  },
    { key: 'evToEbitda', label: 'EV/EBITDA',  placeholder: 'e.g. 10' },
  ]},
  { label: 'Intrinsic Value', rows: [
    { key: 'marginOfSafety',  label: 'Margin of Safety',  unit: '%', placeholder: 'e.g. 20'  },
    { key: 'upsidePotential', label: 'Upside Potential',  unit: '%', placeholder: 'e.g. 30'  },
    { key: 'fairValue',       label: 'Fair Value',                   placeholder: 'e.g. 100' },
  ]},
  { label: 'Price', rows: [
    { key: 'price', label: 'Current Price', placeholder: 'e.g. 50' },
  ]},
]

const REC_TYPE_OPTIONS: { value: RecFilterType; label: string }[] = [
  { value: 'overall', label: 'Overall'     },
  { value: 'model',   label: 'Model'       },
  { value: 'ai',      label: 'AI Analyst'  },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Returns true if `rec` satisfies the selected recommendation filters. */
export function recMatches(
  rec: string | null | undefined,
  selectedRecs: string[],
): boolean {
  if (selectedRecs.length === 0) return true
  const isUnrated = !rec || rec === 'AI Conflict'
  return isUnrated ? selectedRecs.includes('Unrated') : selectedRecs.includes(rec)
}

/** Count how many filters are active (for badge display). */
export function countActiveFilters(
  filters: AnalysisFilterState,
  selectedRecs: string[],
): number {
  return Object.values(filters).filter(({ min, max }) => min !== '' || max !== '').length
    + (selectedRecs.length > 0 ? 1 : 0)
}

// ─── Filter content (no overlay — embed inside any modal) ─────────────────────

interface FilterContentProps {
  filters: AnalysisFilterState
  onChange: (f: AnalysisFilterState) => void
  selectedRecs: string[]
  onRecsChange: (recs: string[]) => void
  recFilterType: RecFilterType
  onRecFilterTypeChange: (t: RecFilterType) => void
}

export function AnalysisFilterContent({
  filters, onChange, selectedRecs, onRecsChange, recFilterType, onRecFilterTypeChange,
}: FilterContentProps) {
  const set = (key: keyof AnalysisFilterState, side: 'min' | 'max', val: string) =>
    onChange({ ...filters, [key]: { ...filters[key], [side]: val } })

  const toggleRec = (rec: string) =>
    onRecsChange(selectedRecs.includes(rec) ? selectedRecs.filter(r => r !== rec) : [...selectedRecs, rec])

  const inputStyle: React.CSSProperties = {
    padding: '5px 8px', borderRadius: '6px',
    backgroundColor: 'var(--bg-surface)', color: 'var(--text-primary)',
    fontSize: '13px', width: '100%', boxSizing: 'border-box', outline: 'none',
  }

  return (
    <>
      {/* Recommendation */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '10px', paddingTop: '12px' }}>
          Recommendation
        </div>
        {/* Overall / Model / AI toggle */}
        <div style={{ display: 'flex', gap: '4px', marginBottom: '10px', backgroundColor: 'var(--bg-hover)', borderRadius: '8px', padding: '3px' }}>
          {REC_TYPE_OPTIONS.map(({ value, label }) => (
            <button key={value} onClick={() => onRecFilterTypeChange(value)} style={{
              flex: 1, padding: '4px 8px', borderRadius: '6px', border: 'none',
              backgroundColor: recFilterType === value ? 'var(--bg-surface)' : 'transparent',
              color: recFilterType === value ? 'var(--text-primary)' : 'var(--text-muted)',
              fontSize: '12px', fontWeight: recFilterType === value ? '600' : '400', cursor: 'pointer',
              boxShadow: recFilterType === value ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              transition: 'all 0.15s ease',
            }}>
              {label}
            </button>
          ))}
        </div>
        {/* Rec pills */}
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {REC_OPTIONS.map((rec) => {
            const active = selectedRecs.includes(rec)
            return (
              <button key={rec} onClick={() => toggleRec(rec)} style={{
                padding: '5px 12px', borderRadius: '20px',
                border: `2px solid ${active ? REC_COLOR[rec] : 'var(--border-input)'}`,
                backgroundColor: active ? REC_COLOR[rec] : 'transparent',
                color: active ? '#fff' : 'var(--text-secondary)',
                fontSize: '12px', fontWeight: '600', cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}>
                {rec}
              </button>
            )
          })}
        </div>
      </div>

      {/* Numeric filters */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 110px 110px', gap: '8px', marginBottom: '4px' }}>
        <div />
        <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600', textAlign: 'center' }}>MIN</span>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '600', textAlign: 'center' }}>MAX</span>
      </div>
      {FILTER_GROUPS.map((group) => (
        <div key={group.label} style={{ marginBottom: '20px' }}>
          <div style={{ fontSize: '11px', fontWeight: '700', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px', paddingTop: '12px', borderTop: '1px solid var(--border-default)' }}>
            {group.label}
          </div>
          {group.rows.map(({ key, label, unit, placeholder }) => (
            <div key={key} style={{ display: 'grid', gridTemplateColumns: '1fr 110px 110px', gap: '8px', alignItems: 'center', marginBottom: '6px' }}>
              <label style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                {label}{unit && <span style={{ color: 'var(--text-muted)', fontSize: '11px', marginLeft: '4px' }}>{unit}</span>}
              </label>
              {(['min', 'max'] as const).map((side) => {
                const range = filters[key]
                return (
                  <input key={side} type="number" value={range[side]}
                    onChange={e => set(key, side, e.target.value)}
                    placeholder={side === 'min' ? (placeholder || '—') : '—'}
                    style={{ ...inputStyle, border: `1px solid ${range[side] ? 'var(--color-primary)' : 'var(--border-input)'}` }}
                  />
                )
              })}
            </div>
          ))}
        </div>
      ))}
    </>
  )
}

// ─── Full overlay modal (used by watchlist page) ───────────────────────────────

interface AnalysisFilterModalProps extends FilterContentProps {
  onClose: () => void
  onClear: () => void
  activeCount: number
}

export function AnalysisFilterModal({
  filters, onChange, onClose, onClear, activeCount,
  selectedRecs, onRecsChange, recFilterType, onRecFilterTypeChange,
}: AnalysisFilterModalProps) {
  return (
    <div onClick={onClose} style={{ position: 'fixed', inset: 0, zIndex: 1000, backgroundColor: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
      <div onClick={e => e.stopPropagation()} style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '12px', width: '100%', maxWidth: '500px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 60px rgba(0,0,0,0.3)' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '18px 20px 14px', borderBottom: '1px solid var(--border-default)', flexShrink: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-primary)' }}>Filters</span>
            {activeCount > 0 && (
              <span style={{ backgroundColor: 'var(--color-primary)', color: '#fff', borderRadius: '10px', fontSize: '11px', padding: '2px 8px', fontWeight: '700' }}>
                {activeCount} active
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {activeCount > 0 && (
              <button onClick={onClear} style={{ padding: '4px 12px', borderRadius: '6px', border: '1px solid var(--border-input)', backgroundColor: 'transparent', color: 'var(--text-muted)', fontSize: '12px', cursor: 'pointer' }}>
                Clear all
              </button>
            )}
            <button onClick={onClose} style={{ width: '28px', height: '28px', borderRadius: '6px', border: 'none', backgroundColor: 'var(--bg-hover)', color: 'var(--text-muted)', fontSize: '16px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              ×
            </button>
          </div>
        </div>

        {/* Scrollable content */}
        <div style={{ overflowY: 'auto', padding: '0 20px 20px', flexGrow: 1 }}>
          <AnalysisFilterContent
            filters={filters} onChange={onChange}
            selectedRecs={selectedRecs} onRecsChange={onRecsChange}
            recFilterType={recFilterType} onRecFilterTypeChange={onRecFilterTypeChange}
          />
        </div>

        {/* Footer */}
        <div style={{ padding: '14px 20px', borderTop: '1px solid var(--border-default)', flexShrink: 0 }}>
          <button onClick={onClose} style={{ width: '100%', padding: '8px', borderRadius: '8px', border: 'none', backgroundColor: 'var(--color-primary)', color: '#fff', fontSize: '14px', fontWeight: '600', cursor: 'pointer' }}>
            Apply
          </button>
        </div>
      </div>
    </div>
  )
}
