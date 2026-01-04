'use client'

import { useState } from 'react'
import { formatPrice } from '@/lib/currency'

interface ExtractedData {
  income_statement?: Record<string, Record<string, number>>
  balance_sheet?: Record<string, Record<string, number>>
  cashflow?: Record<string, Record<string, number>>
  key_metrics?: Record<string, number>
}

interface ExtractedDataViewerProps {
  data: ExtractedData
  ticker: string
}

export default function ExtractedDataViewer({ data, ticker }: ExtractedDataViewerProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    income_statement: true,
    balance_sheet: true,
    cashflow: true,
    key_metrics: true
  })

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }

  const formatValue = (value: number, fieldName?: string): string => {
    // Shares outstanding should not have currency symbol
    const isSharesOutstanding = fieldName?.toLowerCase().includes('shares') || fieldName?.toLowerCase() === 'shares_outstanding'
    
    if (isSharesOutstanding) {
      // Format as number without currency symbol
      if (Math.abs(value) >= 1_000_000_000) {
        return `${(value / 1_000_000_000).toFixed(2)}B`
      } else if (Math.abs(value) >= 1_000_000) {
        return `${(value / 1_000_000).toFixed(2)}M`
      } else if (Math.abs(value) >= 1_000) {
        return `${(value / 1_000).toFixed(2)}K`
      } else {
        return value.toLocaleString()
      }
    }
    
    // Financial values with currency symbol
    if (Math.abs(value) >= 1_000_000_000) {
      return `$${(value / 1_000_000_000).toFixed(2)}B`
    } else if (Math.abs(value) >= 1_000_000) {
      return `$${(value / 1_000_000).toFixed(2)}M`
    } else if (Math.abs(value) >= 1_000) {
      return `$${(value / 1_000).toFixed(2)}K`
    } else {
      return formatPrice(value, 'USD')
    }
  }

  const formatFieldName = (fieldName: string): string => {
    // Convert snake_case to Title Case
    return fieldName
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const renderStatement = (
    title: string,
    sectionKey: string,
    statementData: Record<string, Record<string, number>> | undefined,
    color: string,
    bgColor: string,
    borderColor: string
  ) => {
    if (!statementData || Object.keys(statementData).length === 0) {
      return null
    }

    const periods = Object.keys(statementData).sort().reverse() // Most recent first
    const allFields = new Set<string>()
    periods.forEach(period => {
      Object.keys(statementData[period]).forEach(field => allFields.add(field))
    })
    const fields = Array.from(allFields).sort()

    const isExpanded = expandedSections[sectionKey]

    return (
      <div style={{
        marginBottom: '24px',
        border: `1px solid ${borderColor}`,
        borderRadius: '8px',
        overflow: 'hidden',
        backgroundColor: 'white'
      }}>
        <div
          onClick={() => toggleSection(sectionKey)}
          style={{
            padding: '16px 20px',
            backgroundColor: bgColor,
            cursor: 'pointer',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderBottom: isExpanded ? `1px solid ${borderColor}` : 'none'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h3 style={{
              margin: 0,
              fontSize: '18px',
              fontWeight: '600',
              color: color
            }}>
              {title}
            </h3>
            <span style={{
              padding: '4px 12px',
              backgroundColor: 'white',
              borderRadius: '12px',
              fontSize: '12px',
              fontWeight: '500',
              color: color
            }}>
              {periods.length} period{periods.length !== 1 ? 's' : ''} • {fields.length} field{fields.length !== 1 ? 's' : ''}
            </span>
          </div>
          <span style={{ fontSize: '20px', color: color }}>
            {isExpanded ? '▼' : '▶'}
          </span>
        </div>

        {isExpanded && (
          <div style={{ padding: '20px', overflowX: 'auto' }}>
            <table style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: '14px'
            }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{
                    textAlign: 'left',
                    padding: '12px',
                    fontWeight: '600',
                    color: '#374151',
                    position: 'sticky',
                    left: 0,
                    backgroundColor: 'white',
                    zIndex: 1
                  }}>
                    Field
                  </th>
                  {periods.map(period => (
                    <th
                      key={period}
                      style={{
                        textAlign: 'right',
                        padding: '12px',
                        fontWeight: '600',
                        color: '#374151',
                        minWidth: '120px'
                      }}
                    >
                      {period}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {fields.map((field, idx) => (
                  <tr
                    key={field}
                    style={{
                      borderBottom: idx < fields.length - 1 ? '1px solid #f3f4f6' : 'none',
                      backgroundColor: idx % 2 === 0 ? 'white' : '#f9fafb'
                    }}
                  >
                    <td style={{
                      padding: '12px',
                      fontWeight: '500',
                      color: '#111827',
                      position: 'sticky',
                      left: 0,
                      backgroundColor: idx % 2 === 0 ? 'white' : '#f9fafb',
                      zIndex: 1
                    }}>
                      {field}
                    </td>
                    {periods.map(period => {
                      const value = statementData[period]?.[field]
                      return (
                        <td
                          key={period}
                          style={{
                            textAlign: 'right',
                            padding: '12px',
                            color: value !== undefined ? '#111827' : '#9ca3af',
                            fontFamily: 'monospace'
                          }}
                        >
                          {value !== undefined ? formatValue(value, field) : '—'}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    )
  }

  const renderKeyMetrics = () => {
    if (!data.key_metrics || Object.keys(data.key_metrics).length === 0) {
      return null
    }

    const isExpanded = expandedSections.key_metrics
    const metrics = Object.entries(data.key_metrics).sort()

    return (
      <div style={{
        marginBottom: '24px',
        border: '1px solid #8b5cf6',
        borderRadius: '8px',
        overflow: 'hidden',
        backgroundColor: 'white'
      }}>
        <div
          onClick={() => toggleSection('key_metrics')}
          style={{
            padding: '16px 20px',
            backgroundColor: '#f5f3ff',
            cursor: 'pointer',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderBottom: isExpanded ? '1px solid #8b5cf6' : 'none'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h3 style={{
              margin: 0,
              fontSize: '18px',
              fontWeight: '600',
              color: '#6b21a8'
            }}>
              Key Metrics
            </h3>
            <span style={{
              padding: '4px 12px',
              backgroundColor: 'white',
              borderRadius: '12px',
              fontSize: '12px',
              fontWeight: '500',
              color: '#6b21a8'
            }}>
              {metrics.length} metric{metrics.length !== 1 ? 's' : ''}
            </span>
          </div>
          <span style={{ fontSize: '20px', color: '#6b21a8' }}>
            {isExpanded ? '▼' : '▶'}
          </span>
        </div>

        {isExpanded && (
          <div style={{ padding: '20px' }}>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
              gap: '16px'
            }}>
              {metrics.map(([key, value]) => (
                <div
                  key={key}
                  style={{
                    padding: '16px',
                    backgroundColor: '#f9fafb',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px'
                  }}
                >
                  <div style={{
                    fontSize: '12px',
                    color: '#6b7280',
                    marginBottom: '8px',
                    fontWeight: '500'
                  }}>
                    {formatFieldName(key)}
                  </div>
                  <div style={{
                    fontSize: '20px',
                    fontWeight: '600',
                    color: '#111827',
                    fontFamily: 'monospace'
                  }}>
                    {formatValue(value, key)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  // Check if there's any data to display
  const hasData = 
    (data.income_statement && Object.keys(data.income_statement).length > 0) ||
    (data.balance_sheet && Object.keys(data.balance_sheet).length > 0) ||
    (data.cashflow && Object.keys(data.cashflow).length > 0) ||
    (data.key_metrics && Object.keys(data.key_metrics).length > 0)

  if (!hasData) {
    return null
  }

  return (
    <div style={{
      marginTop: '24px',
      marginBottom: '24px',
      padding: '24px',
      backgroundColor: '#f9fafb',
      border: '1px solid #e5e7eb',
      borderRadius: '8px'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px'
      }}>
        <h2 style={{
          margin: 0,
          fontSize: '24px',
          fontWeight: '700',
          color: '#111827'
        }}>
          📊 Extracted Financial Data for {ticker}
        </h2>
        <button
          onClick={() => {
            const allExpanded = Object.values(expandedSections).every(v => v)
            setExpandedSections({
              income_statement: !allExpanded,
              balance_sheet: !allExpanded,
              cashflow: !allExpanded,
              key_metrics: !allExpanded
            })
          }}
          style={{
            padding: '8px 16px',
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: '500',
            cursor: 'pointer'
          }}
        >
          {Object.values(expandedSections).every(v => v) ? 'Collapse All' : 'Expand All'}
        </button>
      </div>

      {renderStatement(
        'Income Statement',
        'income_statement',
        data.income_statement,
        '#1e40af',
        '#f0f9ff',
        '#3b82f6'
      )}

      {renderStatement(
        'Balance Sheet',
        'balance_sheet',
        data.balance_sheet,
        '#065f46',
        '#f0fdf4',
        '#10b981'
      )}

      {renderStatement(
        'Cash Flow Statement',
        'cashflow',
        data.cashflow,
        '#92400e',
        '#fef3c7',
        '#f59e0b'
      )}

      {renderKeyMetrics()}
    </div>
  )
}

