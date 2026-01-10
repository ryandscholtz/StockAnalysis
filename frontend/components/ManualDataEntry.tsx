'use client'

import { useState } from 'react'
import { stockApi } from '@/lib/api'

interface ManualDataEntryProps {
  ticker: string
  onDataAdded?: () => void
}

export default function ManualDataEntry({ ticker, onDataAdded }: ManualDataEntryProps) {
  console.log('🔧 ManualDataEntry component rendered for ticker:', ticker);
  
  const [isOpen, setIsOpen] = useState(false)
  const [selectedDataType, setSelectedDataType] = useState('income_statement')
  const [period, setPeriod] = useState('2023-12-31')
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)

  const dataTypeOptions = [
    { value: 'income_statement', label: 'Income Statement', icon: '📈' },
    { value: 'balance_sheet', label: 'Balance Sheet', icon: '⚖️' },
    { value: 'cashflow', label: 'Cash Flow Statement', icon: '💰' },
    { value: 'key_metrics', label: 'Key Metrics', icon: '🔑' }
  ]

  const fieldTemplates = {
    income_statement: [
      { key: 'revenue', label: 'Revenue', placeholder: '100000000' },
      { key: 'gross_profit', label: 'Gross Profit', placeholder: '40000000' },
      { key: 'operating_income', label: 'Operating Income', placeholder: '20000000' },
      { key: 'earnings_before_tax', label: 'Earnings Before Tax', placeholder: '18000000' },
      { key: 'net_income', label: 'Net Income', placeholder: '15000000' },
      { key: 'earnings_per_share', label: 'Earnings Per Share', placeholder: '1.50' },
      { key: 'diluted_eps', label: 'Diluted EPS', placeholder: '1.48' }
    ],
    balance_sheet: [
      { key: 'total_assets', label: 'Total Assets', placeholder: '500000000' },
      { key: 'current_assets', label: 'Current Assets', placeholder: '200000000' },
      { key: 'cash_and_equivalents', label: 'Cash & Equivalents', placeholder: '50000000' },
      { key: 'total_liabilities', label: 'Total Liabilities', placeholder: '200000000' },
      { key: 'current_liabilities', label: 'Current Liabilities', placeholder: '100000000' },
      { key: 'long_term_debt', label: 'Long-term Debt', placeholder: '80000000' },
      { key: 'shareholders_equity', label: 'Shareholders Equity', placeholder: '300000000' },
      { key: 'retained_earnings', label: 'Retained Earnings', placeholder: '250000000' }
    ],
    cashflow: [
      { key: 'operating_cash_flow', label: 'Operating Cash Flow', placeholder: '25000000' },
      { key: 'investing_cash_flow', label: 'Investing Cash Flow', placeholder: '-10000000' },
      { key: 'financing_cash_flow', label: 'Financing Cash Flow', placeholder: '-8000000' },
      { key: 'free_cash_flow', label: 'Free Cash Flow', placeholder: '18000000' },
      { key: 'capital_expenditures', label: 'Capital Expenditures', placeholder: '7000000' },
      { key: 'dividends_paid', label: 'Dividends Paid', placeholder: '5000000' }
    ],
    key_metrics: [
      { key: 'shares_outstanding', label: 'Shares Outstanding', placeholder: '10000000' },
      { key: 'market_cap', label: 'Market Cap', placeholder: '1000000000' },
      { key: 'pe_ratio', label: 'P/E Ratio', placeholder: '20' },
      { key: 'pb_ratio', label: 'P/B Ratio', placeholder: '3.5' },
      { key: 'debt_to_equity', label: 'Debt-to-Equity', placeholder: '0.5' },
      { key: 'current_ratio', label: 'Current Ratio', placeholder: '2.0' },
      { key: 'roe', label: 'Return on Equity (decimal)', placeholder: '0.15' },
      { key: 'roa', label: 'Return on Assets (decimal)', placeholder: '0.08' },
      { key: 'book_value_per_share', label: 'Book Value Per Share', placeholder: '30' }
    ]
  }

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)

    try {
      // Convert string values to numbers
      const numericData: Record<string, number> = {}
      Object.entries(formData).forEach(([key, value]) => {
        const numValue = parseFloat(value)
        if (!isNaN(numValue)) {
          numericData[key] = numValue
        }
      })

      if (Object.keys(numericData).length === 0) {
        alert('Please enter at least one valid numeric value')
        return
      }

      const finalPeriod = selectedDataType === 'key_metrics' ? 'latest' : period

      const result = await stockApi.addManualData(ticker, selectedDataType, finalPeriod, numericData)

      if (result.success) {
        alert(`Successfully added ${selectedDataType.replace('_', ' ')} data for ${ticker}`)
        setFormData({})
        setIsOpen(false)
        if (onDataAdded) {
          onDataAdded()
        }
      } else {
        alert(`Failed to add data: ${result.message}`)
      }
    } catch (error: any) {
      alert(`Error adding data: ${error.message}`)
    } finally {
      setSaving(false)
    }
  }

  const currentFields = fieldTemplates[selectedDataType as keyof typeof fieldTemplates] || []

  if (!isOpen) {
    return (
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: '0 0 8px 0', fontSize: '18px', fontWeight: '600' }}>
              📝 Manual Data Entry
            </h3>
            <p style={{ margin: 0, fontSize: '14px', color: '#6b7280' }}>
              Add financial statement data to enable fair value calculations
            </p>
          </div>
          <button
            onClick={() => setIsOpen(true)}
            style={{
              padding: '10px 20px',
              backgroundColor: '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            Add Data
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="card" style={{ marginBottom: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h3 style={{ margin: 0, fontSize: '18px', fontWeight: '600' }}>
          📝 Add Financial Data for {ticker}
        </h3>
        <button
          onClick={() => setIsOpen(false)}
          style={{
            padding: '6px 12px',
            backgroundColor: '#f3f4f6',
            color: '#6b7280',
            border: '1px solid #d1d5db',
            borderRadius: '6px',
            fontSize: '14px',
            cursor: 'pointer'
          }}
        >
          Cancel
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>
              Data Type
            </label>
            <select
              value={selectedDataType}
              onChange={(e) => {
                setSelectedDataType(e.target.value)
                setFormData({}) // Clear form when changing data type
              }}
              style={{
                width: '100%',
                padding: '8px 12px',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '14px'
              }}
            >
              {dataTypeOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.icon} {option.label}
                </option>
              ))}
            </select>
          </div>

          {selectedDataType !== 'key_metrics' && (
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>
                Period (Date)
              </label>
              <input
                type="date"
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px'
                }}
              />
            </div>
          )}
        </div>

        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ margin: '0 0 16px 0', fontSize: '16px', fontWeight: '600', color: '#374151' }}>
            Financial Data Fields
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
            {currentFields.map(field => (
              <div key={field.key}>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '13px', fontWeight: '500', color: '#374151' }}>
                  {field.label}
                </label>
                <input
                  type="number"
                  step="any"
                  placeholder={field.placeholder}
                  value={formData[field.key] || ''}
                  onChange={(e) => handleInputChange(field.key, e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    fontSize: '14px'
                  }}
                />
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            style={{
              padding: '10px 20px',
              backgroundColor: '#f3f4f6',
              color: '#374151',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            style={{
              padding: '10px 20px',
              backgroundColor: saving ? '#9ca3af' : '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '14px',
              fontWeight: '500',
              cursor: saving ? 'not-allowed' : 'pointer'
            }}
          >
            {saving ? 'Saving...' : 'Save Data'}
          </button>
        </div>
      </form>
    </div>
  )
}