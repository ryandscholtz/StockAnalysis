'use client'

import { useState } from 'react'
import { DataQualityWarning } from '@/types/analysis'

interface DataQualityWarningsProps {
  warnings?: DataQualityWarning[]
}

export default function DataQualityWarnings({ warnings }: DataQualityWarningsProps) {
  const [isVisible, setIsVisible] = useState(true)
  
  if (!warnings || warnings.length === 0 || !isVisible) {
    return null
  }

  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'high':
        return '#ef4444' // Red
      case 'medium':
        return '#f59e0b' // Yellow
      case 'low':
        return '#3b82f6' // Blue
      default:
        return '#6b7280' // Gray
    }
  }

  const getSeverityBg = (severity: string): string => {
    switch (severity) {
      case 'high':
        return '#fee2e2' // Light red
      case 'medium':
        return '#fef3c7' // Light yellow
      case 'low':
        return '#dbeafe' // Light blue
      default:
        return '#f3f4f6' // Light gray
    }
  }

  const getCategoryIcon = (category: string): string => {
    switch (category) {
      case 'assumption':
        return '⚠️'
      case 'missing_data':
        return '❌'
      case 'estimated':
        return '📊'
      default:
        return 'ℹ️'
    }
  }

  // Group warnings by severity
  const highWarnings = warnings.filter(w => w.severity === 'high')
  const mediumWarnings = warnings.filter(w => w.severity === 'medium')
  const lowWarnings = warnings.filter(w => w.severity === 'low')

  return (
    <div style={{
      marginBottom: '24px',
      padding: '20px',
      paddingRight: '48px',
      position: 'relative',
      backgroundColor: highWarnings.length > 0 ? '#fee2e2' : '#fef3c7',
      border: `2px solid ${highWarnings.length > 0 ? '#ef4444' : '#f59e0b'}`,
      borderRadius: '8px'
    }}>
      <button
        onClick={() => setIsVisible(false)}
        style={{
          position: 'absolute',
          top: '16px',
          right: '16px',
          background: 'none',
          border: 'none',
          fontSize: '24px',
          cursor: 'pointer',
          color: '#111827',
          opacity: 0.7,
          padding: '0',
          width: '24px',
          height: '24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          lineHeight: '1'
        }}
        title="Close"
      >
        ×
      </button>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
        <span style={{ fontSize: '24px', marginRight: '12px' }}>⚠️</span>
        <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#111827', margin: 0 }}>
          Data Quality Warnings
        </h3>
      </div>
      
      <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '16px' }}>
        This analysis uses some assumptions and estimated values due to missing data. 
        The accuracy of the valuation may be affected.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {warnings.map((warning, index) => (
          <div
            key={index}
            style={{
              padding: '12px',
              backgroundColor: getSeverityBg(warning.severity),
              border: `1px solid ${getSeverityColor(warning.severity)}`,
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '12px'
            }}
          >
            <span style={{ fontSize: '20px' }}>{getCategoryIcon(warning.category)}</span>
            <div style={{ flex: 1 }}>
              <div style={{ 
                fontSize: '14px', 
                fontWeight: '600', 
                color: getSeverityColor(warning.severity),
                marginBottom: '4px',
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                {warning.severity} - {warning.category.replace('_', ' ')}
              </div>
              <div style={{ fontSize: '14px', color: '#374151', marginBottom: '4px' }}>
                <strong>{warning.field}:</strong> {warning.message}
              </div>
              {warning.assumed_value !== null && warning.assumed_value !== undefined && (
                <div style={{ fontSize: '12px', color: '#6b7280', fontStyle: 'italic' }}>
                  Assumed value: {typeof warning.assumed_value === 'number' 
                    ? warning.assumed_value.toLocaleString() 
                    : '-'}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div style={{ 
        marginTop: '16px', 
        padding: '12px', 
        backgroundColor: 'white', 
        borderRadius: '6px',
        fontSize: '13px',
        color: '#6b7280'
      }}>
        <strong>💡 Tip:</strong> You can provide missing data manually to improve accuracy. 
        Click "Add Missing Data" below to enter financial information.
      </div>
    </div>
  )
}

