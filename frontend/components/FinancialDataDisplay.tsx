'use client'

import { useState } from 'react'

interface SectionMeta {
  last_updated: string | null
  source: string
  period_count: number
}

interface FinancialDataDisplayProps {
  ticker: string
  financialData: Record<string, Record<string, Record<string, number>>>
  metadata: Record<string, SectionMeta>
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
  unknown:         'Unknown',
}

function formatValue(field: string, value: number): string {
  const f = field.toLowerCase()
  if (f.includes('roe') || f.includes('roa') || f.includes('margin')) {
    // If stored as decimal (< 2), treat as percentage
    if (Math.abs(value) < 2) return `${(value * 100).toFixed(2)}%`
    return `${value.toFixed(2)}%`
  }
  if (f.includes('eps') || f.includes('per_share') || f.includes('ratio') || f === 'pe_ratio' || f === 'pb_ratio' || f === 'current_ratio' || f === 'debt_to_equity') {
    return value.toFixed(2)
  }
  // Monetary values
  const abs = Math.abs(value)
  const sign = value < 0 ? '-' : ''
  if (abs >= 1e12) return `${sign}${(abs / 1e12).toFixed(2)}T`
  if (abs >= 1e9)  return `${sign}${(abs / 1e9).toFixed(2)}B`
  if (abs >= 1e6)  return `${sign}${(abs / 1e6).toFixed(2)}M`
  if (abs >= 1e3)  return `${sign}${(abs / 1e3).toFixed(2)}K`
  return value.toFixed(2)
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

export default function FinancialDataDisplay({ ticker, financialData, metadata }: FinancialDataDisplayProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const toggle = (key: string) => setExpanded(prev => ({ ...prev, [key]: !prev[key] }))

  // Determine which sections to show — always show all four in order
  const sectionKeys = ['income_statement', 'balance_sheet', 'cashflow', 'key_metrics']

  const hasAnyData = sectionKeys.some(k => financialData[k] && Object.keys(financialData[k]).length > 0)

  if (!hasAnyData) {
    return (
      <div className="card" style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '8px' }}>
          Stored Financial Data
        </h2>
        <p style={{ color: '#6b7280', fontSize: '14px', margin: 0 }}>
          No financial data stored yet. Run an analysis, upload a PDF, or use manual data entry to add data.
        </p>
      </div>
    )
  }

  return (
    <div className="card" style={{ marginBottom: '24px' }}>
      <h2 style={{ fontSize: '18px', fontWeight: '600', marginBottom: '16px' }}>
        Stored Financial Data
        <span style={{ fontSize: '13px', fontWeight: '400', color: '#6b7280', marginLeft: '8px' }}>
          {ticker}
        </span>
      </h2>

      {sectionKeys.map(sectionKey => {
        const cfg = SECTION_CONFIG[sectionKey]
        const sectionData = financialData[sectionKey] || {}
        const meta = metadata[sectionKey]
        const periods = Object.keys(sectionData).sort().reverse()
        const hasData = periods.length > 0
        const isOpen = expanded[sectionKey] ?? false

        return (
          <div key={sectionKey} style={{
            marginBottom: '10px',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            overflow: 'hidden',
          }}>
            {/* Section header — always visible, click to toggle */}
            <div
              onClick={() => toggle(sectionKey)}
              style={{
                padding: '12px 16px',
                backgroundColor: hasData ? '#f9fafb' : '#fafafa',
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
                  <span style={{ fontWeight: '600', fontSize: '15px', color: '#111827' }}>
                    {cfg.title}
                  </span>
                  {hasData && meta ? (
                    <span style={{ fontSize: '12px', color: '#6b7280', marginLeft: '10px' }}>
                      {periods.length} period{periods.length !== 1 ? 's' : ''}
                      {' · '}
                      <span style={{ color: '#9ca3af' }}>
                        Updated {formatDate(meta.last_updated)}
                      </span>
                      {' · '}
                      <span style={{
                        backgroundColor: '#dbeafe', color: '#1d4ed8',
                        padding: '1px 6px', borderRadius: '10px', fontSize: '11px'
                      }}>
                        {SOURCE_LABELS[meta.source] ?? meta.source}
                      </span>
                    </span>
                  ) : (
                    <span style={{ fontSize: '12px', color: '#9ca3af', marginLeft: '10px' }}>
                      No data stored
                    </span>
                  )}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {hasData && (
                  <span style={{
                    backgroundColor: '#d1fae5', color: '#065f46',
                    padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: '600'
                  }}>
                    {periods.length} period{periods.length !== 1 ? 's' : ''}
                  </span>
                )}
                <span style={{ color: '#6b7280', fontSize: '14px' }}>
                  {isOpen ? '▼' : '▶'}
                </span>
              </div>
            </div>

            {/* Expanded content */}
            {isOpen && (
              <div style={{ padding: '16px', overflowX: 'auto' }}>
                {!hasData ? (
                  <p style={{ color: '#9ca3af', fontSize: '13px', margin: 0 }}>
                    No data stored for this section.
                  </p>
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
                          <tr style={{ backgroundColor: '#f3f4f6' }}>
                            <th style={{
                              textAlign: 'left', padding: '8px 12px',
                              fontWeight: '600', color: '#374151',
                              borderBottom: '1px solid #e5e7eb', minWidth: '180px'
                            }}>
                              Field
                            </th>
                            {periods.map(p => (
                              <th key={p} style={{
                                textAlign: 'right', padding: '8px 12px',
                                fontWeight: '600', color: '#374151',
                                borderBottom: '1px solid #e5e7eb', minWidth: '120px'
                              }}>
                                {p}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {allFields.map((field, idx) => (
                            <tr key={field} style={{ backgroundColor: idx % 2 === 0 ? 'white' : '#f9fafb' }}>
                              <td style={{
                                padding: '7px 12px', color: '#374151', fontWeight: '500',
                                borderBottom: '1px solid #f3f4f6'
                              }}>
                                {FIELD_LABELS[field] ?? field}
                              </td>
                              {periods.map(p => {
                                const val = sectionData[p]?.[field]
                                return (
                                  <td key={p} style={{
                                    padding: '7px 12px', textAlign: 'right',
                                    fontFamily: 'monospace', color: val !== undefined ? '#111827' : '#d1d5db',
                                    borderBottom: '1px solid #f3f4f6'
                                  }}>
                                    {val !== undefined ? formatValue(field, val) : '—'}
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
