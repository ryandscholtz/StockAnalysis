'use client'

import { useState, useRef } from 'react'
import { stockApi } from '@/lib/api'

interface PDFUploadProps {
  ticker: string
  onDataExtracted?: () => void
}

export default function PDFUpload({ ticker, onDataExtracted }: PDFUploadProps) {
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<string>('')
  const [error, setError] = useState<string>('')
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
    setUploading(true)

    try {
      const result = await stockApi.uploadPDF(ticker, file)
      setMessage(result.message || 'PDF processed successfully!')
      
      if (onDataExtracted) {
        setTimeout(() => {
          onDataExtracted()
        }, 2000)
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Error uploading PDF')
    } finally {
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
              Extracting financial data with AI. This may take a moment.
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

      {message && (
        <div style={{
          marginTop: '16px',
          padding: '12px',
          backgroundColor: '#d1fae5',
          border: '1px solid #10b981',
          borderRadius: '6px',
          color: '#065f46',
          fontSize: '14px'
        }}>
          ✅ {message}
        </div>
      )}

      {error && (
        <div style={{
          marginTop: '16px',
          padding: '12px',
          backgroundColor: '#fee2e2',
          border: '1px solid #ef4444',
          borderRadius: '6px',
          color: '#991b1b',
          fontSize: '14px'
        }}>
          ❌ {error}
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

