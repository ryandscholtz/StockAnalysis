'use client'

import { useState } from 'react'

interface FinancialData {
  income_statement?: Record<string, Record<string, number>>
  balance_sheet?: Record<string, Record<string, number>>
  cashflow?: Record<string, Record<string, number>>
  key_metrics?: Record<string, Record<string, number>>
}

interface FinancialDataDisplayProps {
  ticker: string
  financialData?: FinancialData
  onDataUpdate?: () => void
}

export default function FinancialDataDisplay({ ticker, financialData, onDataUpdate }: FinancialDataDisplayProps) {
  console.log('📊 FinancialDataDisplay component rendered for ticker:', ticker, 'with data:', financialData);
  
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})
  const [editingField, setEditingField] = useState<string | null>(null)
  const [editValue, setEditValue] = useState<string>('')

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }))
  }

  const formatNumber = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return 'N/A'
    if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(2)}B`
    if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(2)}M`
    if (Math.abs(value) >= 1e3) return `$${(value / 1e3).toFixed(2)}K`
    return `$${value.toFixed(2)}`
  }

  const formatPercentage = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return 'N/A'
    return `${(value * 100).toFixed(2)}%`
  }

  const formatRatio = (value: number | undefined | null): string => {
    if (value === undefined || value === null) return 'N/A'
    return value.toFixed(2)
  }

  const handleEdit = async (section: string, period: string, field: string, currentValue: number | undefined) => {
    setEditingField(`${section}_${period}_${field}`)
    setEditValue(currentValue?.toString() || '')
  }

  const handleSave = async (section: string, period: string, field: string) => {
    try {
      const numericValue = parseFloat(editValue)
      if (isNaN(numericValue)) {
        alert('Please enter a valid number')
        return
      }

      // Create the data object for this field
      const existingData = financialData?.[section as keyof FinancialData]?.[period] || {}
      const updatedData = {
        ...existingData,
        [field]: numericValue
      }

      // Save to API
      const response = await fetch('/api/manual-data', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ticker,
          data_type: section,
          period,
          data: updatedData
        })
      })

      if (response.ok) {
        setEditingField(null)
        setEditValue('')
        if (onDataUpdate) {
          onDataUpdate()
        }
      } else {
        alert('Failed to save data')
      }
    } catch (error) {
      console.error('Error saving data:', error)
      alert('Error saving data')
    }
  }

  const handleCancel = () => {
    setEditingField(null)
    setEditValue('')
  }

  const renderField = (
    section: string,
    period: string,
    field: string,
    label: string,
    value: number | undefined,
    formatter: (val: number | undefined) => string = formatNumber
  ) => {
    const fieldKey = `${section}_${period}_${field}`
    const isEditing = editingField === fieldKey

    return (
      <div key={fieldKey} style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '8px 0',
        borderBottom: '1px solid #f0f0f0'
      }}>
        <span style={{ fontWeight: '500', color: '#374151' }}>{label}:</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {isEditing ? (
            <>
              <input
                type="number"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                style={{
                  padding: '4px 8px',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  width: '120px'
                }}
                autoFocus
              />
              <button
                onClick={() => handleSave(section, period, field)}
                style={{
                  padding: '4px 8px',
                  backgroundColor: '#10b981',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  fontSize: '12px',
                  cursor: 'pointer'
                }}
              >
                Save
              </button>
              <button
                onClick={handleCancel}
                style={{
                  padding: '4px 8px',
                  backgroundColor: '#6b7280',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  fontSize: '12px',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
            </>
          ) : (
            <>
              <span style={{
                color: value !== undefined ? '#111827' : '#9ca3af',
                fontFamily: 'monospace',
                minWidth: '100px',
                textAlign: 'right'
              }}>
                {formatter(value)}
              </span>
              <button
                onClick={() => handleEdit(section, period, field, value)}
                style={{
                  padding: '2px 6px',
                  backgroundColor: '#f3f4f6',
                  color: '#6b7280',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  fontSize: '10px',
                  cursor: 'pointer'
                }}
              >
                Edit
              </button>
            </>
          )}
        </div>
      </div>
    )
  }

  const renderSection = (
    sectionKey: string,
    title: string,
    icon: string,
    fields: Array<{ key: string; label: string; formatter?: (val: number | undefined) => string }>
  ) => {
    const sectionData = financialData?.[sectionKey as keyof FinancialData] || {}
    const periods = Object.keys(sectionData).sort().reverse() // Most recent first
    const isExpanded = expandedSections[sectionKey]
    const hasData = periods.length > 0

    return (
      <div key={sectionKey} style={{
        marginBottom: '16px',
        border: '1px solid #e5e7eb',
        borderRadius: '8px',
        overflow: 'hidden'
      }}>
        <div
          onClick={() => toggleSection(sectionKey)}
          style={{
            padding: '16px',
            backgroundColor: hasData ? '#f9fafb' : '#fef3c7',
            cursor: 'pointer',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderBottom: isExpanded ? '1px solid #e5e7eb' : 'none'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '20px' }}>{icon}</span>
            <div>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600', color: '#111827' }}>
                {title}
              </h3>
              <p style={{ margin: 0, fontSize: '12px', color: '#6b7280' }}>
                {hasData ? `${periods.length} period(s) available` : 'No data available - click to add'}
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {hasData && (
              <span style={{
                padding: '2px 8px',
                backgroundColor: '#10b981',
                color: 'white',
                borderRadius: '12px',
                fontSize: '10px',
                fontWeight: '600'
              }}>
                ✓ Data Available
              </span>
            )}
            <span style={{ fontSize: '16px', color: '#6b7280' }}>
              {isExpanded ? '▼' : '▶'}
            </span>
          </div>
        </div>

        {isExpanded && (
          <div style={{ padding: '16px' }}>
            {periods.length > 0 ? (
              periods.map(period => (
                <div key={period} style={{ marginBottom: '24px' }}>
                  <h4 style={{
                    margin: '0 0 12px 0',
                    fontSize: '14px',
                    fontWeight: '600',
                    color: '#374151',
                    padding: '8px 12px',
                    backgroundColor: '#f3f4f6',
                    borderRadius: '6px'
                  }}>
                    Period: {period}
                  </h4>
                  <div style={{ paddingLeft: '12px' }}>
                    {fields.map(field => {
                      const value = sectionData[period]?.[field.key]
                      return renderField(
                        sectionKey,
                        period,
                        field.key,
                        field.label,
                        value,
                        field.formatter
                      )
                    })}
                  </div>
                </div>
              ))
            ) : (
              <div style={{
                padding: '24px',
                textAlign: 'center',
                color: '#6b7280',
                backgroundColor: '#fefce8',
                borderRadius: '6px'
              }}>
                <p style={{ margin: '0 0 12px 0', fontSize: '14px' }}>
                  No {title.toLowerCase()} data available for {ticker}
                </p>
                <p style={{ margin: 0, fontSize: '12px' }}>
                  Add data manually or upload a PDF financial statement to enable fair value calculations
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="card">
      <h2 style={{ fontSize: '24px', marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '12px' }}>
        📊 Financial Data Overview
        <span style={{
          fontSize: '12px',
          fontWeight: '400',
          color: '#6b7280',
          backgroundColor: '#f3f4f6',
          padding: '4px 8px',
          borderRadius: '12px'
        }}>
          {ticker}
        </span>
      </h2>

      <div style={{ marginBottom: '16px', padding: '12px', backgroundColor: '#eff6ff', borderRadius: '6px', border: '1px solid #bfdbfe' }}>
        <p style={{ margin: 0, fontSize: '14px', color: '#1e40af' }}>
          💡 <strong>Fair value calculations require financial statement data.</strong> Expand sections below to view available data or add missing information.
        </p>
      </div>

      {renderSection('income_statement', 'Income Statement', '📈', [
        { key: 'revenue', label: 'Revenue' },
        { key: 'gross_profit', label: 'Gross Profit' },
        { key: 'operating_income', label: 'Operating Income' },
        { key: 'earnings_before_tax', label: 'Earnings Before Tax' },
        { key: 'net_income', label: 'Net Income' },
        { key: 'earnings_per_share', label: 'Earnings Per Share', formatter: formatRatio },
        { key: 'diluted_eps', label: 'Diluted EPS', formatter: formatRatio }
      ])}

      {renderSection('balance_sheet', 'Balance Sheet', '⚖️', [
        { key: 'total_assets', label: 'Total Assets' },
        { key: 'current_assets', label: 'Current Assets' },
        { key: 'cash_and_equivalents', label: 'Cash & Equivalents' },
        { key: 'total_liabilities', label: 'Total Liabilities' },
        { key: 'current_liabilities', label: 'Current Liabilities' },
        { key: 'long_term_debt', label: 'Long-term Debt' },
        { key: 'shareholders_equity', label: 'Shareholders Equity' },
        { key: 'retained_earnings', label: 'Retained Earnings' }
      ])}

      {renderSection('cashflow', 'Cash Flow Statement', '💰', [
        { key: 'operating_cash_flow', label: 'Operating Cash Flow' },
        { key: 'investing_cash_flow', label: 'Investing Cash Flow' },
        { key: 'financing_cash_flow', label: 'Financing Cash Flow' },
        { key: 'free_cash_flow', label: 'Free Cash Flow' },
        { key: 'capital_expenditures', label: 'Capital Expenditures' },
        { key: 'dividends_paid', label: 'Dividends Paid' }
      ])}

      {renderSection('key_metrics', 'Key Metrics', '🔑', [
        { key: 'shares_outstanding', label: 'Shares Outstanding', formatter: (val) => val ? `${(val / 1e6).toFixed(2)}M` : 'N/A' },
        { key: 'market_cap', label: 'Market Cap' },
        { key: 'pe_ratio', label: 'P/E Ratio', formatter: formatRatio },
        { key: 'pb_ratio', label: 'P/B Ratio', formatter: formatRatio },
        { key: 'debt_to_equity', label: 'Debt-to-Equity', formatter: formatRatio },
        { key: 'current_ratio', label: 'Current Ratio', formatter: formatRatio },
        { key: 'roe', label: 'Return on Equity', formatter: formatPercentage },
        { key: 'roa', label: 'Return on Assets', formatter: formatPercentage },
        { key: 'book_value_per_share', label: 'Book Value Per Share', formatter: formatRatio }
      ])}
    </div>
  )
}