'use client'

import { useState, useRef } from 'react'
import { stockApi } from '@/lib/api'

interface PDFUploadProps {
  ticker: string
  onDataExtracted?: () => void
}

interface PDFImage {
  page_number: number
  image_base64: string
  width: number
  height: number
}

interface ExtractedData {
  income_statement?: Record<string, Record<string, number>>
  balance_sheet?: Record<string, Record<string, number>>
  cashflow?: Record<string, Record<string, number>>
  key_metrics?: Record<string, number>
}

export default function PDFUpload({ ticker, onDataExtracted }: PDFUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<string>('')
  const [error, setError] = useState<string>('')
  const [processingStatus, setProcessingStatus] = useState<string>('')
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please select a PDF file')
      return
    }

    if (file.size > 50 * 1024 * 1024) {
      setError('File size must be less than 50MB')
      return
    }

    setError('')
    setMessage('')
    setProcessingStatus('')
    setUploading(true)
    setExtractedData(null)

    // Declare progress interval outside try block so it's accessible in catch/finally
    let progressInterval: NodeJS.Timeout | null = null
    let elapsedSeconds = 0

    try {
      // Process PDF directly with AWS Textract (no image conversion needed)
      setProcessingStatus('📄 Processing PDF with AWS Textract...')
      
      // Update progress every 15 seconds while processing
      progressInterval = setInterval(() => {
        elapsedSeconds += 15
        const minutes = Math.floor(elapsedSeconds / 60)
        const seconds = elapsedSeconds % 60
        const timeStr = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`
        setProcessingStatus(`📄 Processing PDF with AWS Textract... (${timeStr} elapsed)`)
      }, 15000) // Update every 15 seconds
      
      try {
        const result = await stockApi.uploadPDF(ticker, file)
        
        // Clear progress interval when done
        if (progressInterval) {
          clearInterval(progressInterval)
        }
        
        // Update processing status
        if (result.updated_periods && result.updated_periods > 0) {
          setProcessingStatus(`✅ Textract processing complete: Extracted ${result.updated_periods} data period(s)`)
        } else {
          setProcessingStatus(`⚠️ Textract processing completed but no financial data was extracted`)
        }
        
        setMessage(result.message || 'PDF processed successfully!')
        
        // Store extracted data if available
        if (result.extracted_data) {
          setExtractedData(result.extracted_data as ExtractedData)
        }
        
        if (onDataExtracted) {
          setTimeout(() => {
            onDataExtracted()
          }, 2000)
        }
      } catch (err: any) {
        // Clear progress interval on error
        if (progressInterval) {
          clearInterval(progressInterval)
        }
        setError(err.response?.data?.detail || err.message || 'Error uploading PDF')
        setProcessingStatus('❌ Processing failed')
      }
    } catch (err: any) {
      // Clear progress interval on error (outer catch for any other errors)
      if (progressInterval) {
        clearInterval(progressInterval)
      }
      setError(err.response?.data?.detail || err.message || 'Error uploading PDF')
      setProcessingStatus('❌ Processing failed')
    } finally {
      // Clear progress interval in finally as well (safety)
      if (progressInterval) {
        clearInterval(progressInterval)
      }
      setUploading(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    
    const file = e.dataTransfer.files?.[0]
    if (file && file.name.toLowerCase().endsWith('.pdf')) {
      if (fileInputRef.current) {
        // Create a new FileList-like object and trigger change
        const dataTransfer = new DataTransfer()
        dataTransfer.items.add(file)
        fileInputRef.current.files = dataTransfer.files
        fileInputRef.current.dispatchEvent(new Event('change', { bubbles: true }))
      }
    } else {
      setError('Please drop a PDF file')
    }
  }

  return (
    <div style={{
      marginBottom: '24px',
      padding: '20px',
      backgroundColor: '#f0f9ff',
      border: '2px dashed #3b82f6',
      borderRadius: '8px'
    }}>
      <h3 style={{ margin: '0 0 12px 0', color: '#1e40af', fontSize: '18px', fontWeight: '600' }}>
        📄 Upload Financial Statement PDF
      </h3>
      <p style={{ margin: '0 0 16px 0', color: '#1e3a8a', fontSize: '14px' }}>
        Upload a PDF financial statement (annual report, 10-K, quarterly report, etc.) 
        and our AI will automatically extract the financial data for {ticker}.
      </p>

      <div
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        style={{
          padding: '24px',
          backgroundColor: 'white',
          border: '2px dashed #93c5fd',
          borderRadius: '8px',
          textAlign: 'center',
          cursor: uploading ? 'not-allowed' : 'pointer',
          transition: 'all 0.2s',
          opacity: uploading ? 0.6 : 1
        }}
        onClick={() => !uploading && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
          disabled={uploading}
        />
        
        {uploading ? (
          <div>
            <div style={{ fontSize: '32px', marginBottom: '12px' }}>⏳</div>
            <p style={{ color: '#3b82f6', fontWeight: '500' }}>Processing PDF...</p>
            <p style={{ color: '#6b7280', fontSize: '12px', marginTop: '8px' }}>
              Processing PDF directly with AWS Textract to extract financial data. This may take a moment.
            </p>
          </div>
        ) : (
          <div>
            <div style={{ fontSize: '48px', marginBottom: '12px' }}>📎</div>
            <p style={{ color: '#3b82f6', fontWeight: '500', marginBottom: '4px' }}>
              Click to upload or drag and drop
            </p>
            <p style={{ color: '#6b7280', fontSize: '12px' }}>
              PDF files only (max 50MB)
            </p>
          </div>
        )}
      </div>

      {/* Processing Status */}
      {processingStatus && (
        <div style={{
          marginTop: '16px',
          padding: '12px',
          paddingRight: '32px',
          position: 'relative',
          backgroundColor: processingStatus.includes('✅') ? '#d1fae5' : processingStatus.includes('⚠️') ? '#fef3c7' : '#e0f2fe',
          border: processingStatus.includes('✅') ? '1px solid #10b981' : processingStatus.includes('⚠️') ? '1px solid #f59e0b' : '1px solid #3b82f6',
          borderRadius: '6px',
          color: processingStatus.includes('✅') ? '#065f46' : processingStatus.includes('⚠️') ? '#92400e' : '#1e40af',
          fontSize: '14px'
        }}>
          <button
            onClick={() => setProcessingStatus('')}
            style={{
              position: 'absolute',
              top: '8px',
              right: '8px',
              background: 'none',
              border: 'none',
              fontSize: '18px',
              cursor: 'pointer',
              color: 'inherit',
              opacity: 0.7,
              padding: '0',
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              lineHeight: '1'
            }}
            title="Close"
          >
            ×
          </button>
          {processingStatus}
        </div>
      )}

      {message && (
        <div style={{
          marginTop: '16px',
          padding: '12px',
          paddingRight: '32px',
          position: 'relative',
          backgroundColor: '#d1fae5',
          border: '1px solid #10b981',
          borderRadius: '6px',
          color: '#065f46',
          fontSize: '14px'
        }}>
          <button
            onClick={() => setMessage('')}
            style={{
              position: 'absolute',
              top: '8px',
              right: '8px',
              background: 'none',
              border: 'none',
              fontSize: '18px',
              cursor: 'pointer',
              color: 'inherit',
              opacity: 0.7,
              padding: '0',
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              lineHeight: '1'
            }}
            title="Close"
          >
            ×
          </button>
          ✅ {message}
        </div>
      )}

      {error && (
        <div style={{
          marginTop: '16px',
          padding: '12px',
          paddingRight: '32px',
          position: 'relative',
          backgroundColor: '#fee2e2',
          border: '1px solid #ef4444',
          borderRadius: '6px',
          color: '#991b1b',
          fontSize: '14px'
        }}>
          <button
            onClick={() => setError('')}
            style={{
              position: 'absolute',
              top: '8px',
              right: '8px',
              background: 'none',
              border: 'none',
              fontSize: '18px',
              cursor: 'pointer',
              color: 'inherit',
              opacity: 0.7,
              padding: '0',
              width: '20px',
              height: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              lineHeight: '1'
            }}
            title="Close"
          >
            ×
          </button>
          ❌ {error}
        </div>
      )}

      {/* Extracted Fields Display */}
      {extractedData && (
        <div style={{
          marginTop: '24px',
          padding: '20px',
          backgroundColor: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: '8px'
        }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', color: '#111827', margin: '0 0 16px 0' }}>
            📊 Extracted Financial Fields
          </h4>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
            {/* Income Statement Fields */}
            {extractedData.income_statement && Object.keys(extractedData.income_statement).length > 0 && (
              <div style={{
                padding: '12px',
                backgroundColor: '#f0f9ff',
                border: '1px solid #3b82f6',
                borderRadius: '6px'
              }}>
                <div style={{ fontSize: '14px', fontWeight: '600', color: '#1e40af', marginBottom: '8px' }}>
                  Income Statement
                </div>
                <div style={{ fontSize: '12px', color: '#6b7280' }}>
                  {Object.keys(extractedData.income_statement).length} period(s)
                </div>
                <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '8px' }}>
                  Fields: {Object.values(extractedData.income_statement)[0] ? Object.keys(Object.values(extractedData.income_statement)[0]).join(', ') : 'N/A'}
                </div>
              </div>
            )}

            {/* Balance Sheet Fields */}
            {extractedData.balance_sheet && Object.keys(extractedData.balance_sheet).length > 0 && (
              <div style={{
                padding: '12px',
                backgroundColor: '#f0fdf4',
                border: '1px solid #10b981',
                borderRadius: '6px'
              }}>
                <div style={{ fontSize: '14px', fontWeight: '600', color: '#065f46', marginBottom: '8px' }}>
                  Balance Sheet
                </div>
                <div style={{ fontSize: '12px', color: '#6b7280' }}>
                  {Object.keys(extractedData.balance_sheet).length} period(s)
                </div>
                <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '8px' }}>
                  Fields: {Object.values(extractedData.balance_sheet)[0] ? Object.keys(Object.values(extractedData.balance_sheet)[0]).join(', ') : 'N/A'}
                </div>
              </div>
            )}

            {/* Cash Flow Fields */}
            {extractedData.cashflow && Object.keys(extractedData.cashflow).length > 0 && (
              <div style={{
                padding: '12px',
                backgroundColor: '#fef3c7',
                border: '1px solid #f59e0b',
                borderRadius: '6px'
              }}>
                <div style={{ fontSize: '14px', fontWeight: '600', color: '#92400e', marginBottom: '8px' }}>
                  Cash Flow Statement
                </div>
                <div style={{ fontSize: '12px', color: '#6b7280' }}>
                  {Object.keys(extractedData.cashflow).length} period(s)
                </div>
                <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '8px' }}>
                  Fields: {Object.values(extractedData.cashflow)[0] ? Object.keys(Object.values(extractedData.cashflow)[0]).join(', ') : 'N/A'}
                </div>
              </div>
            )}

            {/* Key Metrics */}
            {extractedData.key_metrics && Object.keys(extractedData.key_metrics).length > 0 && (
              <div style={{
                padding: '12px',
                backgroundColor: '#f5f3ff',
                border: '1px solid #8b5cf6',
                borderRadius: '6px'
              }}>
                <div style={{ fontSize: '14px', fontWeight: '600', color: '#6b21a8', marginBottom: '8px' }}>
                  Key Metrics
                </div>
                <div style={{ fontSize: '12px', color: '#6b7280' }}>
                  {Object.keys(extractedData.key_metrics).length} metric(s)
                </div>
                <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '8px' }}>
                  Fields: {Object.keys(extractedData.key_metrics).join(', ')}
                </div>
              </div>
            )}
          </div>

          {/* Summary */}
          <div style={{
            marginTop: '16px',
            padding: '12px',
            backgroundColor: '#f9fafb',
            border: '1px solid #e5e7eb',
            borderRadius: '6px',
            fontSize: '12px',
            color: '#6b7280'
          }}>
            <strong>Summary:</strong> Extracted data from {[
              extractedData.income_statement && Object.keys(extractedData.income_statement).length > 0 ? 'Income Statement' : null,
              extractedData.balance_sheet && Object.keys(extractedData.balance_sheet).length > 0 ? 'Balance Sheet' : null,
              extractedData.cashflow && Object.keys(extractedData.cashflow).length > 0 ? 'Cash Flow' : null,
              extractedData.key_metrics && Object.keys(extractedData.key_metrics).length > 0 ? 'Key Metrics' : null
            ].filter(Boolean).join(', ') || 'PDF'}
          </div>
        </div>
      )}

      <div style={{
        marginTop: '12px',
        padding: '12px',
        backgroundColor: '#fef3c7',
        border: '1px solid #fbbf24',
        borderRadius: '6px',
        fontSize: '12px',
        color: '#92400e'
      }}>
        <strong>💡 Tip:</strong> Supported documents include annual reports (10-K), quarterly reports (10-Q), 
        earnings releases, and other financial statements. The AI will extract income statements, 
        balance sheets, cash flow statements, and key metrics automatically.
      </div>
    </div>
  )
}

