'use client'

import { useState } from 'react'
import { getCurrencySymbol } from '@/lib/currency'
import { stockApi } from '@/lib/api'

interface SectionMeta {
  last_updated: string | null
  source: string
  period_count: number
}

interface FinancialDataDisplayProps {
  ticker: string
  financialData: Record<string, Record<string, Record<string, number>>>
  metadata: Record<string, SectionMeta>
  financialCurrency?: string
  onPeriodDeleted?: () => void
}

// Human-readable labels for common field names (both snake_case and title case)
const FIELD_LABELS: Record<string, string> = {
  // Income statement
  revenue: 'Revenue',
  'Total Revenue': 'Revenue',
  gross_profit: 'Gross Profit',
  'Gross Profit': 'Gross Profit',
  operating_income: 'Operating Income',
  'Operating Income': 'Operating Income',
  earnings_before_tax: 'Earnings Before Tax',
  'Income Before Tax': 'Earnings Before Tax',
  net_income: 'Net Income',
  'Net Income': 'Net Income',
  earnings_per_share: 'EPS',
  'Basic EPS': 'Basic EPS',
  diluted_eps: 'Diluted EPS',
  'Diluted EPS': 'Diluted EPS',
  // Balance sheet
  total_assets: 'Total Assets',
  'Total Assets': 'Total Assets',
  current_assets: 'Current Assets',
  'Current Assets': 'Current Assets',
  cash_and_equivalents: 'Cash & Equivalents',
  'Cash And Cash Equivalents': 'Cash & Equivalents',
  total_liabilities: 'Total Liabilities',
  'Total Liabilities Net Minority Interest': 'Total Liabilities',
  current_liabilities: 'Current Liabilities',
  'Current Liabilities': 'Current Liabilities',
  long_term_debt: 'Long-term Debt',
  'Long Term Debt': 'Long-term Debt',
  shareholders_equity: 'Shareholders Equity',
  'Total Stockholder Equity': 'Shareholders Equity',
  retained_earnings: 'Retained Earnings',
  'Retained Earnings': 'Retained Earnings',
  // Cash flow
  operating_cash_flow: 'Operating Cash Flow',
  'Operating Cash Flow': 'Operating Cash Flow',
  investing_cash_flow: 'Investing Cash Flow',
  financing_cash_flow: 'Financing Cash Flow',
  free_cash_flow: 'Free Cash Flow',
  'Free Cash Flow': 'Free Cash Flow',
  capital_expenditures: 'Capital Expenditures',
  'Capital Expenditure': 'Capital Expenditures',
  dividends_paid: 'Dividends Paid',
  'Common Stock Dividends Paid': 'Dividends Paid',
  // Key metrics
  shares_outstanding: 'Shares Outstanding',
  market_cap: 'Market Cap',
  pe_ratio: 'P/E Ratio',
  pb_ratio: 'P/B Ratio',
  debt_to_equity: 'Debt / Equity',
  current_ratio: 'Current Ratio',
  roe: 'Return on Equity',
  roa: 'Return on Assets',
  book_value_per_share: 'Book Value / Share',
}

const SECTION_CONFIG: Record<string, { title: string; icon: string }> = {
  income_statement: { title: 'Income Statement', icon: '📈' },
  balance_sheet:    { title: 'Balance Sheet',    icon: '⚖️' },
  cashflow:         { title: 'Cash Flow Statement', icon: '💰' },
  key_metrics:      { title: 'Key Metrics',       icon: '🔑' },
}

const SOURCE_LABELS: Record<string, string> = {
  manual_entry:    'Manual Entry',
  pdf_upload:      'PDF Upload',
  ai_fetch:        'AI Retrieved',
  ai_bedrock:      'AI Retrieved',
  yahoo_finance:   'Yahoo Finance',
  sec_edgar:       'SEC EDGAR',
  unknown:         'Unknown',
}

// Fields that are dimensionless ratios, percentages, or counts — no currency symbol
function isNonMonetary(field: string): boolean {
  const f = field.toLowerCase()
  return (
    f.includes('roe') || f.includes('roa') || f.includes('margin') ||
    f.includes('ratio') || f === 'pe_ratio' || f === 'pb_ratio' ||
    f === 'current_ratio' || f === 'debt_to_equity' ||
    f === 'shares_outstanding' || f.startsWith('shares_')
  )
}

function formatValue(field: string, value: number, currencySymbol: string = ''): string {
  const f = field.toLowerCase()
  if (f.includes('roe') || f.includes('roa') || f.includes('margin')) {
    if (Math.abs(value) < 2) return `${(value * 100).toFixed(2)}%`
    return `${value.toFixed(2)}%`
  }
  if (f.includes('ratio') || f === 'pe_ratio' || f === 'pb_ratio' ||
      f === 'current_ratio' || f === 'debt_to_equity') {
    return value.toFixed(2)
  }
  if (f === 'shares_outstanding' || f.startsWith('shares_')) {
    const abs = Math.abs(value)
    const sign = value < 0 ? '-' : ''
    if (abs >= 1e9)  return `${sign}${(abs / 1e9).toFixed(2)}B`
    if (abs >= 1e6)  return `${sign}${(abs / 1e6).toFixed(2)}M`
    if (abs >= 1e3)  return `${sign}${(abs / 1e3).toFixed(2)}K`
    return `${sign}${abs.toFixed(0)}`
  }
  // Monetary values — prefix with currency symbol
  const sym = isNonMonetary(field) ? '' : currencySymbol
  const abs = Math.abs(value)
  const sign = value < 0 ? '-' : ''
  if (abs >= 1e12) return `${sign}${sym}${(abs / 1e12).toFixed(2)}T`
  if (abs >= 1e9)  return `${sign}${sym}${(abs / 1e9).toFixed(2)}B`
  if (abs >= 1e6)  return `${sign}${sym}${(abs / 1e6).toFixed(2)}M`
  if (abs >= 1e3)  return `${sign}${sym}${(abs / 1e3).toFixed(2)}K`
  return `${sign}${sym}${abs.toFixed(2)}`
}

function formatDate(iso: string | null): string {
  if (!iso) return 'Unknown'
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    })
  } catch {
    return iso
  }
}

export default function FinancialDataDisplay({ ticker, financialData, metadata, financialCurrency, onPeriodDeleted }: FinancialDataDisplayProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [deleting, setDeleting] = useState<string | null>(null) // "section:period"
  // Local overrides: sections/periods hidden after optimistic delete
  const [deleted, setDeleted] = useState<Set<string>>(new Set()) // "section:period"
  const currencySymbol = getCurrencySymbol(financialCurrency)

  const toggle = (key: string) => setExpanded(prev => ({ ...prev, [key]: !prev[key] }))

  const handleDeletePeriod = async (e: React.MouseEvent, section: string, period: string) => {
    e.stopPropagation()
    const key = `${section}:${period}`
    if (!confirm(`Remove ${period} from ${section.replace(/_/g, ' ')}?`)) return
    setDeleting(key)
    try {
      await stockApi.deleteFinancialPeriod(ticker, section, period)
      setDeleted(prev => new Set([...prev, key]))
      onPeriodDeleted?.()
    } catch (err: any) {
      alert(`Failed to delete: ${err?.message || 'Unknown error'}`)
    } finally {
      setDeleting(null)
    }
  }

  // Determine which sections to show — always show all four in order
  const sectionKeys = ['income_statement', 'balance_sheet', 'cashflow', 'key_metrics']

  const hasAnyData = sectionKeys.some(k => financialData[k] && Object.keys(financialData[k]).length > 0)

  if (!hasAnyData) {
    return (
      <div className="card" style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>
          Stored Financial Data
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '14px', margin: 0 }}>
          No financial data stored yet. Run an analysis, upload a PDF, or use manual data entry to add data.
        </p>
      </div>
    )
  }

  return (
    <div className="card" style={{ marginBottom: '24px' }}>
      <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px' }}>
        Stored Financial Data
        <span style={{ fontSize: '13px', fontWeight: '400', color: 'var(--text-muted)', marginLeft: '8px' }}>
          {ticker}
        </span>
        {financialCurrency && (
          <span style={{
            fontSize: '12px', fontWeight: '500', color: 'var(--text-secondary)',
            backgroundColor: 'var(--bg-hover)', border: '1px solid var(--border-default)',
            padding: '1px 7px', borderRadius: '10px', marginLeft: '8px'
          }}>
            {financialCurrency}
          </span>
        )}
      </h2>

      {/* Summary notice when any section is missing data */}
      {(() => {
        const missingSections = sectionKeys
          .filter(k => !(financialData[k] && Object.keys(financialData[k]).length > 0))
          .map(k => SECTION_CONFIG[k]?.title)
          .filter(Boolean)
        if (missingSections.length === 0) return null
        return (
          <div style={{
            display: 'flex', alignItems: 'flex-start', gap: '10px',
            padding: '10px 14px', borderRadius: '6px', marginBottom: '14px',
            backgroundColor: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)',
          }}>
            <span style={{ fontSize: '15px', lineHeight: '1.5', flexShrink: 0 }}>⚠️</span>
            <div>
              <span style={{ color: 'var(--status-warning-text)', fontSize: '13px', fontWeight: '600' }}>
                Incomplete financial data —{' '}
              </span>
              <span style={{ color: 'var(--status-warning-text)', fontSize: '13px' }}>
                {missingSections.join(', ')} could not be retrieved automatically.
                Add the missing data manually or re-run the analysis to try again.
              </span>
            </div>
          </div>
        )
      })()}

      {sectionKeys.map(sectionKey => {
        const cfg = SECTION_CONFIG[sectionKey]
        const sectionData = financialData[sectionKey] || {}
        const meta = metadata[sectionKey]
        const periods = Object.keys(sectionData)
          .sort().reverse()
          .filter(p => !deleted.has(`${sectionKey}:${p}`))
        const hasData = periods.length > 0
        const isOpen = expanded[sectionKey] ?? false

        return (
          <div key={sectionKey} style={{
            marginBottom: '10px',
            border: `1px solid ${hasData ? 'var(--border-default)' : 'var(--status-warning-border)'}`,
            borderRadius: '8px',
            overflow: 'hidden',
          }}>
            {/* Section header — always visible, click to toggle */}
            <div
              onClick={() => toggle(sectionKey)}
              style={{
                padding: '12px 16px',
                backgroundColor: hasData ? 'var(--bg-surface-subtle)' : 'var(--status-warning-bg)',
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                userSelect: 'none',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '18px' }}>{cfg.icon}</span>
                <div>
                  <span style={{ fontWeight: '600', fontSize: '15px', color: hasData ? 'var(--text-primary)' : 'var(--status-warning-text)' }}>
                    {cfg.title}
                  </span>
                  {hasData && meta ? (
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '10px' }}>
                      {periods.length} period{periods.length !== 1 ? 's' : ''}
                      {' · '}
                      <span style={{ color: 'var(--text-subtle)' }}>
                        Updated {formatDate(meta.last_updated)}
                      </span>
                      {' · '}
                      <span style={{
                        backgroundColor: 'var(--color-primary-bg)', color: 'var(--color-primary)',
                        padding: '1px 6px', borderRadius: '10px', fontSize: '11px'
                      }}>
                        {SOURCE_LABELS[meta.source] ?? meta.source}
                      </span>
                    </span>
                  ) : (
                    <span style={{ fontSize: '12px', color: 'var(--status-warning-text)', marginLeft: '10px', fontWeight: '500' }}>
                      ⚠ Data unavailable — add manually
                    </span>
                  )}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {hasData && (
                  <span style={{
                    backgroundColor: 'var(--status-success-bg)', color: 'var(--status-success-text)',
                    padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: '600'
                  }}>
                    {periods.length} period{periods.length !== 1 ? 's' : ''}
                  </span>
                )}
                <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
                  {isOpen ? '▼' : '▶'}
                </span>
              </div>
            </div>

            {/* Expanded content */}
            {isOpen && (
              <div style={{ padding: '16px', overflowX: 'auto' }}>
                {!hasData ? (
                  <div style={{
                    display: 'flex', alignItems: 'flex-start', gap: '10px',
                    padding: '12px 14px', borderRadius: '6px',
                    backgroundColor: 'var(--status-warning-bg)', border: '1px solid var(--status-warning-border)',
                  }}>
                    <span style={{ fontSize: '16px', lineHeight: '1.4' }}>⚠️</span>
                    <div>
                      <p style={{ color: 'var(--status-warning-text)', fontSize: '13px', fontWeight: '600', margin: '0 0 2px' }}>
                        Data unavailable
                      </p>
                      <p style={{ color: 'var(--status-warning-text)', fontSize: '12px', margin: 0 }}>
                        Could not be retrieved automatically from Yahoo Finance or AI.
                        Add it manually using the data entry form, or re-run the analysis to try again.
                      </p>
                    </div>
                  </div>
                ) : (
                  /* Table: rows = fields, columns = periods */
                  (() => {
                    // Collect all field names across all periods
                    const allFields = Array.from(
                      new Set(periods.flatMap(p => Object.keys(sectionData[p] || {})))
                    )

                    return (
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                        <thead>
                          <tr style={{ backgroundColor: 'var(--bg-hover)' }}>
                            <th style={{
                              textAlign: 'left', padding: '8px 12px',
                              fontWeight: '600', color: 'var(--text-secondary)',
                              borderBottom: '1px solid var(--border-default)', minWidth: '180px'
                            }}>
                              Field
                            </th>
                            {periods.map(p => {
                              const dk = `${sectionKey}:${p}`
                              const isDeleting = deleting === dk
                              return (
                                <th key={p} style={{
                                  textAlign: 'right', padding: '8px 12px',
                                  fontWeight: '600', color: 'var(--text-secondary)',
                                  borderBottom: '1px solid var(--border-default)', minWidth: '120px'
                                }}>
                                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                                    {p}
                                    <button
                                      onClick={e => handleDeletePeriod(e, sectionKey, p)}
                                      disabled={isDeleting}
                                      title={`Remove ${p}`}
                                      style={{
                                        background: 'none', border: 'none', cursor: 'pointer',
                                        color: '#9ca3af', fontSize: '14px', lineHeight: 1,
                                        padding: '1px 3px', borderRadius: '3px',
                                        opacity: isDeleting ? 0.4 : 1,
                                      }}
                                      onMouseEnter={e => (e.currentTarget.style.color = '#ef4444')}
                                      onMouseLeave={e => (e.currentTarget.style.color = '#9ca3af')}
                                    >
                                      ×
                                    </button>
                                  </span>
                                </th>
                              )
                            })}
                          </tr>
                        </thead>
                        <tbody>
                          {allFields.map((field, idx) => (
                            <tr key={field} style={{ backgroundColor: idx % 2 === 0 ? 'var(--bg-surface)' : 'var(--bg-surface-subtle)' }}>
                              <td style={{
                                padding: '7px 12px', color: 'var(--text-secondary)', fontWeight: '500',
                                borderBottom: '1px solid var(--border-default)'
                              }}>
                                {FIELD_LABELS[field] ?? field}
                              </td>
                              {periods.map(p => {
                                const val = sectionData[p]?.[field]
                                return (
                                  <td key={p} style={{
                                    padding: '7px 12px', textAlign: 'right',
                                    fontFamily: 'monospace', color: val !== undefined ? 'var(--text-primary)' : 'var(--border-input)',
                                    borderBottom: '1px solid var(--border-default)'
                                  }}>
                                    {val !== undefined ? formatValue(field, val, currencySymbol) : '—'}
                                  </td>
                                )
                              })}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )
                  })()
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
