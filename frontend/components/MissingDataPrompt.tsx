'use client'

import { useState, useEffect } from 'react'
import { MissingDataInfo } from '@/types/analysis'
import { stockApi } from '@/lib/api'

interface MissingDataPromptProps {
  ticker: string
  missingData: MissingDataInfo
  onDataAdded?: () => void
}

export default function MissingDataPrompt({ ticker, missingData, onDataAdded }: MissingDataPromptProps) {
  const [showForm, setShowForm] = useState(false)
  const [selectedDataType, setSelectedDataType] = useState<string>('')
  const [selectedPeriod, setSelectedPeriod] = useState<string>('')
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const [message, setMessage] = useState<string>('')

  const getDataTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      'income_statement': 'Income Statement',
      'balance_sheet': 'Balance Sheet',
      'cashflow': 'Cash Flow Statement',
      'key_metrics': 'Key Metrics'
    }
    return labels[type] || type
  }

  const getCommonFields = (type: string): string[] => {
    const fields: Record<string, string[]> = {
      'income_statement': ['Total Revenue', 'Net Income', 'Operating Income', 'EBIT', 'Income Before Tax'],
      'balance_sheet': ['Total Assets', 'Total Liabilities', 'Total Stockholder Equity', 'Cash And Cash Equivalents', 'Total Debt'],
      'cashflow': ['Operating Cash Flow', 'Capital Expenditures', 'Free Cash Flow', 'Cash From Financing Activities'],
      'key_metrics': ['Shares Outstanding', 'Market Cap']
    }
    return fields[type] || []
  }

  // Automatically set period to 'latest' when key_metrics is selected
  useEffect(() => {
    if (selectedDataType === 'key_metrics' && selectedPeriod !== 'latest') {
      setSelectedPeriod('latest')
    }
  }, [selectedDataType, selectedPeriod])

  const handleFieldChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate data type is selected
    if (!selectedDataType) {
      setMessage('Please select a data type')
      return
    }
    
    // For key_metrics, period should always be 'latest', for others it must be provided
    const period = selectedDataType === 'key_metrics' ? 'latest' : selectedPeriod
    if (!period) {
      setMessage('Please enter a period (e.g., 2024-12-31)')
      return
    }

    setSubmitting(true)
    setMessage('')

    try {
      // Convert string values to numbers
      const numericData: Record<string, number> = {}
      for (const [key, value] of Object.entries(formData)) {
        if (value.trim()) {
          const numValue = parseFloat(value.replace(/,/g, ''))
          if (!isNaN(numValue)) {
            // Map display names to backend field names for key_metrics
            if (selectedDataType === 'key_metrics') {
              if (key === 'Shares Outstanding') {
                numericData['shares_outstanding'] = numValue
              } else if (key === 'Market Cap') {
                numericData['market_cap'] = numValue
              } else {
                // Use the key as-is for other fields
                numericData[key] = numValue
              }
            } else {
              numericData[key] = numValue
            }
          }
        }
      }

      if (Object.keys(numericData).length === 0) {
        setMessage('Please enter at least one value')
        setSubmitting(false)
        return
      }

      // Use 'latest' period for key_metrics
      const period = selectedDataType === 'key_metrics' ? 'latest' : selectedPeriod
      const result = await stockApi.addManualData(ticker, selectedDataType, period, numericData)
      setMessage(result.message || 'Data added successfully!')
      
      if (onDataAdded) {
        setTimeout(() => {
          onDataAdded()
        }, 2000)
      }
    } catch (error: any) {
      setMessage(error.response?.data?.detail || error.message || 'Error adding data')
    } finally {
      setSubmitting(false)
    }
  }

  // Show prompt if there's missing data OR if we're being called (which means fair value is 0)
  const hasMissingData = missingData.has_missing_data || 
    (missingData.income_statement.length > 0 || 
     missingData.balance_sheet.length > 0 || 
     missingData.cashflow.length > 0 || 
     missingData.key_metrics.length > 0)

  if (!hasMissingData) {
    return null
  }

  return (
    <div style={{
      marginBottom: '24px',
      padding: '20px',
      backgroundColor: '#fee2e2',
      border: '2px solid #dc2626',
      borderRadius: '8px',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h3 style={{ margin: 0, color: '#991b1b', fontSize: '20px', fontWeight: '600' }}>
            ⚠️ Unable to Calculate Fair Value - Missing Financial Data
          </h3>
          <p style={{ margin: '8px 0 0', color: '#7f1d1d', fontSize: '15px', fontWeight: '500' }}>
            The system cannot calculate a fair value because essential financial data is missing. 
            Please add the missing data below to enable accurate valuation.
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          style={{
            padding: '8px 16px',
            backgroundColor: showForm ? '#dc2626' : '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: '500'
          }}
        >
          {showForm ? 'Cancel' : 'Add Data Manually'}
        </button>
      </div>

      <div style={{ marginBottom: '16px' }}>
        {missingData.income_statement.length > 0 && (
          <div style={{ marginBottom: '8px' }}>
            <strong>Income Statement:</strong> {missingData.income_statement.join(', ')}
          </div>
        )}
        {missingData.balance_sheet.length > 0 && (
          <div style={{ marginBottom: '8px' }}>
            <strong>Balance Sheet:</strong> {missingData.balance_sheet.join(', ')}
          </div>
        )}
        {missingData.cashflow.length > 0 && (
          <div style={{ marginBottom: '8px' }}>
            <strong>Cash Flow:</strong> {missingData.cashflow.join(', ')}
          </div>
        )}
        {missingData.key_metrics.length > 0 && (
          <div style={{ marginBottom: '8px' }}>
            <strong>Key Metrics:</strong> {missingData.key_metrics.join(', ')}
          </div>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} style={{
          marginTop: '20px',
          padding: '20px',
          backgroundColor: 'white',
          borderRadius: '8px',
          border: '1px solid #d1d5db'
        }}>
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
              Data Type:
            </label>
            <select
              value={selectedDataType}
              onChange={(e) => {
                const newDataType = e.target.value
                setSelectedDataType(newDataType)
                setFormData({})
                // Set period to 'latest' for key_metrics, clear for others
                if (newDataType === 'key_metrics') {
                  setSelectedPeriod('latest')
                } else {
                  setSelectedPeriod('')
                }
              }}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #d1d5db',
                borderRadius: '6px',
                fontSize: '14px'
              }}
            >
              <option value="">Select data type...</option>
              <option value="income_statement">Income Statement</option>
              <option value="balance_sheet">Balance Sheet</option>
              <option value="cashflow">Cash Flow Statement</option>
              <option value="key_metrics">Key Metrics</option>
            </select>
          </div>

          {selectedDataType && (
            <>
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  {selectedDataType === 'key_metrics' ? 'Period (use "latest" for key metrics):' : 'Period (e.g., 2024-12-31):'}
                </label>
                <input
                  type="text"
                  value={selectedDataType === 'key_metrics' ? 'latest' : selectedPeriod}
                  onChange={(e) => {
                    if (selectedDataType !== 'key_metrics') {
                      setSelectedPeriod(e.target.value)
                    }
                  }}
                  placeholder={selectedDataType === 'key_metrics' ? 'latest' : '2024-12-31'}
                  disabled={selectedDataType === 'key_metrics'}
                  style={{
                    width: '100%',
                    padding: '8px',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    fontSize: '14px',
                    backgroundColor: selectedDataType === 'key_metrics' ? '#f3f4f6' : 'white',
                    color: selectedDataType === 'key_metrics' ? '#6b7280' : '#111827'
                  }}
                />
                {selectedDataType === 'key_metrics' && (
                  <p style={{ marginTop: '4px', fontSize: '12px', color: '#6b7280' }}>
                    Key metrics use period "latest" (not a date)
                  </p>
                )}
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  Financial Data (enter values):
                </label>
                {getCommonFields(selectedDataType).map(field => (
                  <div key={field} style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px' }}>
                      {field}:
                    </label>
                    <input
                      type="text"
                      value={formData[field] || ''}
                      onChange={(e) => handleFieldChange(field, e.target.value)}
                      placeholder="Enter value (numbers only)"
                      style={{
                        width: '100%',
                        padding: '8px',
                        border: '1px solid #d1d5db',
                        borderRadius: '6px',
                        fontSize: '14px'
                      }}
                    />
                  </div>
                ))}
              </div>

              {message && (
                <div style={{
                  padding: '12px',
                  marginBottom: '16px',
                  backgroundColor: message.includes('Error') ? '#fee2e2' : '#d1fae5',
                  color: message.includes('Error') ? '#991b1b' : '#065f46',
                  borderRadius: '6px',
                  fontSize: '14px'
                }}>
                  {message}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                style={{
                  width: '100%',
                  padding: '12px',
                  backgroundColor: submitting ? '#9ca3af' : '#2563eb',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '16px',
                  fontWeight: '500',
                  cursor: submitting ? 'not-allowed' : 'pointer'
                }}
              >
                {submitting ? 'Submitting...' : 'Add Data'}
              </button>
            </>
          )}
        </form>
      )}
    </div>
  )
}

