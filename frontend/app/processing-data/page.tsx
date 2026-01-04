'use client'

import { useState, useRef, useEffect } from 'react'
import { stockApi, SearchResult } from '@/lib/api'

interface ExtractedData {
  income_statement?: Record<string, Record<string, number>>
  balance_sheet?: Record<string, Record<string, number>>
  cashflow?: Record<string, Record<string, number>>
  key_metrics?: Record<string, number>
}

interface PDFImage {
  page_number: number
  image_base64: string
  width: number
  height: number
}

export default function ProcessingDataPage() {
  const [ticker, setTicker] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [suggestions, setSuggestions] = useState<SearchResult[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [searchLoading, setSearchLoading] = useState<boolean>(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<string>('')
  const [error, setError] = useState<string>('')
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null)
  const [processingStatus, setProcessingStatus] = useState<string>('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Search for tickers with debounce
  useEffect(() => {
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    if (searchQuery.trim().length >= 1) {
      setSearchLoading(true)
      searchTimeoutRef.current = setTimeout(async () => {
        try {
          const results = await stockApi.searchTickers(searchQuery.trim())
          setSuggestions(results)
          // Show suggestions if we have results and the input is likely focused
          if (results.length > 0 && searchQuery.trim().length > 0) {
            setShowSuggestions(true)
          } else {
            setShowSuggestions(false)
          }
          setSelectedIndex(-1)
        } catch (error: any) {
          // Only log non-network errors (network errors are expected when backend is down)
          if (error?.code !== 'ERR_NETWORK' && error?.code !== 'ECONNREFUSED') {
            console.error('Search error:', error)
          }
          setSuggestions([])
          setShowSuggestions(false)
        } finally {
          setSearchLoading(false)
        }
      }, 300)
    } else {
      setSuggestions([])
      setShowSuggestions(false)
      setSearchLoading(false)
    }

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [searchQuery])

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showSuggestions])

  const handleSelectSuggestion = (suggestion: SearchResult) => {
    setTicker(suggestion.ticker)
    setSearchQuery(suggestion.ticker)
    setShowSuggestions(false)
    setSelectedIndex(-1)
    // Blur the input to prevent it from refocusing
    if (inputRef.current) {
      inputRef.current.blur()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIndex(prev => 
        prev < suggestions.length - 1 ? prev + 1 : prev
      )
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIndex(prev => prev > 0 ? prev - 1 : -1)
    } else if (e.key === 'Enter' && selectedIndex >= 0 && suggestions[selectedIndex]) {
      e.preventDefault()
      handleSelectSuggestion(suggestions[selectedIndex])
    } else if (e.key === 'Enter' && searchQuery.trim()) {
      e.preventDefault()
      setTicker(searchQuery.trim().toUpperCase())
      setShowSuggestions(false)
    }
  }

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

    if (!ticker || ticker.trim().length === 0) {
      setError('Please enter a ticker symbol')
      return
    }

    setError('')
    setMessage('')
    setProcessingStatus('')
    setUploading(true)
    setExtractedData(null)

    // Progress update interval
    let progressInterval: NodeJS.Timeout | null = null
    let elapsedSeconds = 0
    
    try {
      // Upload PDF and process with AWS Textract (no image conversion needed)
      setProcessingStatus('📄 Processing PDF with AWS Textract...')
      console.log('Starting PDF upload for ticker:', ticker)
      
      // Start progress updates every 5 seconds
      progressInterval = setInterval(() => {
        elapsedSeconds += 5
        const minutes = Math.floor(elapsedSeconds / 60)
        const seconds = elapsedSeconds % 60
        const timeStr = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`
        
        // Add helpful hints after certain time thresholds
        let hint = ''
        if (elapsedSeconds > 120) {
          hint = ' (This is taking longer than expected. Large PDFs may take a few minutes)'
        } else if (elapsedSeconds > 60) {
          hint = ' (Processing large PDF with AWS Textract - this may take a few minutes)'
        }
        
        setProcessingStatus(`📄 Processing PDF with AWS Textract... (${timeStr} elapsed)${hint}`)
      }, 5000)
      
      const uploadResult = await stockApi.uploadPDF(ticker.trim().toUpperCase(), file)
      console.log('Upload result:', uploadResult)
      
      // Clear progress interval when done
      if (progressInterval) {
        clearInterval(progressInterval)
        progressInterval = null
      }
      
      if (!uploadResult.success) {
        const errorMsg = uploadResult.message || 'Failed to process PDF'
        console.error('Upload failed:', errorMsg)
        throw new Error(errorMsg)
      }

      // Processing is complete
      setUploading(false)
      if (uploadResult.updated_periods && uploadResult.updated_periods > 0) {
        setProcessingStatus(`✅ Textract processing complete: Extracted ${uploadResult.updated_periods} data period(s)`)
      } else {
        setProcessingStatus('✅ Textract processing complete')
      }
      
      if (uploadResult.extracted_data) {
        setExtractedData(uploadResult.extracted_data as ExtractedData)
      }
      
      if (uploadResult.updated_periods !== undefined) {
        if (uploadResult.updated_periods > 0) {
          setMessage(`✅ Successfully extracted ${uploadResult.updated_periods} data period(s) for ${ticker.trim().toUpperCase()}`)
        } else {
          // Build detailed error message from extraction_details
          let errorMsg = `⚠️ ⚠️ Processing completed but no financial data was extracted for ${ticker.trim().toUpperCase()}.`
          
          if (uploadResult.extraction_details) {
            const details = uploadResult.extraction_details
            
            // Build diagnostics from extraction_details
            const detailParts = []
            
            if (details.error_type) {
              detailParts.push(`Error Type: ${details.error_type}`)
            }
            if (details.error_message) {
              detailParts.push(`Error: ${details.error_message}`)
            }
            if (details.llm_response_analysis && Array.isArray(details.llm_response_analysis)) {
              detailParts.push(...details.llm_response_analysis)
            }
            if (details.financial_keywords_detected) {
              const keywords = details.financial_keywords_detected
              if (Object.keys(keywords).length > 0) {
                detailParts.push(`Financial keywords found: ${Object.entries(keywords).map(([k, v]) => `${k} (${v} matches)`).join(', ')}`)
              }
            }
            if (details.pdf_text_length) {
              detailParts.push(`PDF text length: ${details.pdf_text_length} characters`)
            }
            if (details.llama_api_url) {
              detailParts.push(`Ollama URL: ${details.llama_api_url}`)
            }
            if (details.llama_model) {
              detailParts.push(`Model: ${details.llama_model}`)
            }
            
            if (detailParts.length > 0) {
              errorMsg += `\n\n${detailParts.map(p => `  • ${p}`).join('\n')}`
            }
            
            // Add LLM response preview if available
            if (details.raw_llm_response_preview) {
              errorMsg += `\n\nLLM Response Preview:\n${details.raw_llm_response_preview.substring(0, 500)}...`
            }
          }
          
          setMessage(errorMsg)
        }
      } else if (uploadResult.message) {
        setMessage(uploadResult.message)
      }
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (err: any) {
      // Clear progress interval on error
      if (progressInterval) {
        clearInterval(progressInterval)
        progressInterval = null
      }
      
      setUploading(false)
      
      // Handle network errors (backend not running)
      if (err?.code === 'ERR_NETWORK' || err?.code === 'ECONNREFUSED') {
        setError('Cannot connect to backend server. Please ensure the backend is running on http://localhost:8000')
        setProcessingStatus('❌ Connection failed')
        console.warn('Backend connection error:', err.message)
      } else if (err?.code === 'ECONNABORTED' || err.message?.includes('timeout') || err.message?.includes('Timeout')) {
        setError('Request timed out after 10 minutes. The PDF may be too large or Ollama may not be responding. Please try a smaller PDF or check if Ollama is running at http://localhost:11434')
        setProcessingStatus('⏱️ Request timed out')
        console.error('Upload timeout:', err)
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail)
        setProcessingStatus('❌ Processing failed')
        console.error('Upload error:', err)
      } else if (err.message) {
        setError(err.message)
        setProcessingStatus('❌ Processing failed')
        console.error('Upload error:', err)
      } else {
        setError('Failed to process PDF. Please check the backend logs.')
        setProcessingStatus('❌ Processing failed')
        console.error('Upload error:', err)
      }
      
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

  const formatNumber = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return 'N/A'
    if (Math.abs(value) >= 1e9) {
      return `$${(value / 1e9).toFixed(2)}B`
    } else if (Math.abs(value) >= 1e6) {
      return `$${(value / 1e6).toFixed(2)}M`
    } else if (Math.abs(value) >= 1e3) {
      return `$${(value / 1e3).toFixed(2)}K`
    }
    return `$${value.toFixed(2)}`
  }

  return (
    <div className="container" style={{ maxWidth: '1200px', margin: '40px auto', padding: '20px' }}>
      <h1 style={{ fontSize: '36px', marginBottom: '8px', color: '#111827' }}>
        AI Process Data
      </h1>
      <p style={{ fontSize: '16px', color: '#6b7280', marginBottom: '32px' }}>
        Upload a financial statement PDF and test the LLM agent to extract all required fields for analysis.
      </p>

      {/* Fields Being Extracted */}
      <div style={{
        marginBottom: '32px',
        padding: '20px',
        backgroundColor: '#f0f9ff',
        border: '1px solid #3b82f6',
        borderRadius: '8px'
      }}>
        <h3 style={{ fontSize: '18px', marginBottom: '16px', color: '#1e40af', fontWeight: '600' }}>
          📋 Fields Being Extracted
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px' }}>
          <div>
            <h4 style={{ fontSize: '14px', fontWeight: '600', color: '#111827', marginBottom: '8px' }}>
              Income Statement
            </h4>
            <ul style={{ fontSize: '13px', color: '#374151', lineHeight: '1.6', paddingLeft: '20px', margin: 0 }}>
              <li>Total Revenue</li>
              <li>Net Income</li>
              <li>Operating Income</li>
              <li>EBIT</li>
              <li>Income Before Tax</li>
            </ul>
          </div>
          <div>
            <h4 style={{ fontSize: '14px', fontWeight: '600', color: '#111827', marginBottom: '8px' }}>
              Balance Sheet
            </h4>
            <ul style={{ fontSize: '13px', color: '#374151', lineHeight: '1.6', paddingLeft: '20px', margin: 0 }}>
              <li>Total Assets</li>
              <li>Total Liabilities</li>
              <li>Total Stockholder Equity</li>
              <li>Cash And Cash Equivalents</li>
              <li>Total Debt</li>
            </ul>
          </div>
          <div>
            <h4 style={{ fontSize: '14px', fontWeight: '600', color: '#111827', marginBottom: '8px' }}>
              Cash Flow Statement
            </h4>
            <ul style={{ fontSize: '13px', color: '#374151', lineHeight: '1.6', paddingLeft: '20px', margin: 0 }}>
              <li>Operating Cash Flow</li>
              <li>Capital Expenditures</li>
              <li>Free Cash Flow</li>
              <li>Cash From Financing Activities</li>
            </ul>
          </div>
          <div>
            <h4 style={{ fontSize: '14px', fontWeight: '600', color: '#111827', marginBottom: '8px' }}>
              Key Metrics
            </h4>
            <ul style={{ fontSize: '13px', color: '#374151', lineHeight: '1.6', paddingLeft: '20px', margin: 0 }}>
              <li>Shares Outstanding</li>
              <li>Market Cap</li>
            </ul>
          </div>
        </div>
        <p style={{ fontSize: '12px', color: '#6b7280', marginTop: '16px', marginBottom: 0 }}>
          The LLM will extract data for multiple periods when available (e.g., 2024, 2023, 2022).
        </p>
      </div>

      {/* Ticker Search */}
      <div style={{ marginBottom: '24px' }}>
        <label htmlFor="ticker-search" style={{ display: 'block', marginBottom: '8px', fontWeight: '600', color: '#374151' }}>
          Stock Ticker Symbol
        </label>
        <div style={{ position: 'relative', maxWidth: '500px' }}>
          <input
            ref={inputRef}
            id="ticker-search"
            type="text"
            value={searchQuery}
            onChange={(e) => {
              const value = e.target.value
              setSearchQuery(value)
              // Show suggestions dropdown when user starts typing
              if (value.trim().length > 0) {
                // Will be set by useEffect when results arrive
              } else {
                setShowSuggestions(false)
              }
            }}
            onKeyDown={handleKeyDown}
            onFocus={(e) => {
              if (suggestions.length > 0 && searchQuery.trim().length > 0) {
                setShowSuggestions(true)
              }
              e.currentTarget.style.borderColor = '#2563eb'
            }}
            placeholder="Search by ticker or company name (e.g., AAPL or Apple)"
            style={{
              width: '100%',
              padding: '12px 16px',
              border: '1px solid #d1d5db',
              borderRadius: '8px',
              fontSize: '16px',
              outline: 'none',
              transition: 'border-color 0.2s'
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = '#d1d5db'
            }}
          />
          
          {searchLoading && (
            <div style={{
              position: 'absolute',
              right: '16px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#6b7280',
              fontSize: '14px'
            }}>
              Searching...
            </div>
          )}

          {/* Suggestions Dropdown */}
          {(showSuggestions || searchLoading) && (suggestions.length > 0 || searchLoading) && (
            <div
              ref={suggestionsRef}
              style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                right: 0,
                backgroundColor: 'white',
                border: '1px solid #d1d5db',
                borderRadius: '8px',
                marginTop: '4px',
                maxHeight: '300px',
                overflowY: 'auto',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                zIndex: 10000
              }}
            >
              {searchLoading ? (
                <div style={{ padding: '16px', textAlign: 'center', color: '#6b7280' }}>
                  Searching...
                </div>
              ) : (
                suggestions.map((suggestion, index) => (
                <div
                  key={`${suggestion.ticker}-${index}`}
                  onMouseDown={(e) => {
                    e.preventDefault() // Prevent input from losing focus before click
                  }}
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    handleSelectSuggestion(suggestion)
                  }}
                  onMouseEnter={() => setSelectedIndex(index)}
                  style={{
                    padding: '12px 16px',
                    cursor: 'pointer',
                    borderBottom: index < suggestions.length - 1 ? '1px solid #e5e7eb' : 'none',
                    backgroundColor: selectedIndex === index ? '#f3f4f6' : 'white',
                    transition: 'background-color 0.15s'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: '600', fontSize: '16px', color: '#111827' }}>
                        {suggestion.ticker}
                      </div>
                      {suggestion.companyName && (
                        <div style={{ fontSize: '14px', color: '#6b7280', marginTop: '2px' }}>
                          {suggestion.companyName}
                        </div>
                      )}
                    </div>
                    {suggestion.exchange && (
                      <div style={{ fontSize: '12px', color: '#9ca3af', textTransform: 'uppercase' }}>
                        {suggestion.exchange}
                      </div>
                    )}
                  </div>
                </div>
                ))
              )}
            </div>
          )}
        </div>
        {ticker && (
          <p style={{ fontSize: '14px', color: '#6b7280', marginTop: '8px' }}>
            Selected: <strong>{ticker}</strong>
          </p>
        )}
      </div>

      {/* File Upload Section */}
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
          and our AI agent will automatically extract all financial data fields required for analysis.
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
              <p style={{ color: '#3b82f6', fontWeight: '500' }}>Processing PDF with AI Vision...</p>
              <p style={{ color: '#6b7280', fontSize: '12px', marginTop: '8px' }}>
                Converting PDF to images and extracting financial data with AI vision model. This may take a moment.
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


      {/* Extracted Fields Summary - Right after images */}
      {extractedData && (
        <div style={{
          marginTop: '24px',
          padding: '20px',
          backgroundColor: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: '8px'
        }}>
          <h4 style={{ fontSize: '18px', fontWeight: '600', color: '#111827', margin: '0 0 16px 0' }}>
            📊 Extracted Financial Fields (LLM)
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
                <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '8px', lineHeight: '1.4' }}>
                  Fields: {Object.values(extractedData.income_statement)[0] ? Object.keys(Object.values(extractedData.income_statement)[0]).slice(0, 3).join(', ') + (Object.keys(Object.values(extractedData.income_statement)[0]).length > 3 ? '...' : '') : 'N/A'}
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
                <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '8px', lineHeight: '1.4' }}>
                  Fields: {Object.values(extractedData.balance_sheet)[0] ? Object.keys(Object.values(extractedData.balance_sheet)[0]).slice(0, 3).join(', ') + (Object.keys(Object.values(extractedData.balance_sheet)[0]).length > 3 ? '...' : '') : 'N/A'}
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
                <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '8px', lineHeight: '1.4' }}>
                  Fields: {Object.values(extractedData.cashflow)[0] ? Object.keys(Object.values(extractedData.cashflow)[0]).slice(0, 3).join(', ') + (Object.keys(Object.values(extractedData.cashflow)[0]).length > 3 ? '...' : '') : 'N/A'}
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
                <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '8px', lineHeight: '1.4' }}>
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

      {message && (
          <div style={{
            marginTop: '16px',
            padding: '16px',
            paddingRight: '32px',
            position: 'relative',
            backgroundColor: message.includes('no financial data') || message.includes('0 data period') ? '#fef3c7' : '#d1fae5',
            border: message.includes('no financial data') || message.includes('0 data period') ? '1px solid #f59e0b' : '1px solid #10b981',
            borderRadius: '6px',
            color: message.includes('no financial data') || message.includes('0 data period') ? '#92400e' : '#065f46',
            fontSize: '14px',
            lineHeight: '1.8',
            whiteSpace: 'pre-wrap',
            fontFamily: 'monospace'
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
            {message.includes('no financial data') || message.includes('0 data period') ? '⚠️' : '✅'} {message}
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
      </div>

      {/* Extracted Data Display */}
      {extractedData && (
        <div style={{ marginTop: '32px' }}>
          <h2 style={{ fontSize: '24px', marginBottom: '20px', color: '#111827' }}>
            Extracted Financial Data
          </h2>

          {/* Income Statement */}
          {extractedData.income_statement && Object.keys(extractedData.income_statement).length > 0 && (
            <div style={{
              marginBottom: '24px',
              padding: '20px',
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px'
            }}>
              <h3 style={{ fontSize: '20px', marginBottom: '16px', color: '#111827', fontWeight: '600' }}>
                Income Statement
              </h3>
              {Object.entries(extractedData.income_statement).map(([period, data]) => (
                <div key={period} style={{ marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid #e5e7eb' }}>
                  <h4 style={{ fontSize: '16px', marginBottom: '12px', color: '#374151', fontWeight: '600' }}>
                    Period: {period}
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '12px' }}>
                    {Object.entries(data).map(([key, value]) => (
                      <div key={key} style={{
                        padding: '12px',
                        backgroundColor: '#f9fafb',
                        borderRadius: '6px',
                        border: '1px solid #e5e7eb'
                      }}>
                        <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>
                          {key}
                        </div>
                        <div style={{ fontSize: '16px', fontWeight: '600', color: '#111827' }}>
                          {formatNumber(value)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Balance Sheet */}
          {extractedData.balance_sheet && Object.keys(extractedData.balance_sheet).length > 0 && (
            <div style={{
              marginBottom: '24px',
              padding: '20px',
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px'
            }}>
              <h3 style={{ fontSize: '20px', marginBottom: '16px', color: '#111827', fontWeight: '600' }}>
                Balance Sheet
              </h3>
              {Object.entries(extractedData.balance_sheet).map(([period, data]) => (
                <div key={period} style={{ marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid #e5e7eb' }}>
                  <h4 style={{ fontSize: '16px', marginBottom: '12px', color: '#374151', fontWeight: '600' }}>
                    Period: {period}
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '12px' }}>
                    {Object.entries(data).map(([key, value]) => (
                      <div key={key} style={{
                        padding: '12px',
                        backgroundColor: '#f9fafb',
                        borderRadius: '6px',
                        border: '1px solid #e5e7eb'
                      }}>
                        <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>
                          {key}
                        </div>
                        <div style={{ fontSize: '16px', fontWeight: '600', color: '#111827' }}>
                          {formatNumber(value)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Cash Flow */}
          {extractedData.cashflow && Object.keys(extractedData.cashflow).length > 0 && (
            <div style={{
              marginBottom: '24px',
              padding: '20px',
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px'
            }}>
              <h3 style={{ fontSize: '20px', marginBottom: '16px', color: '#111827', fontWeight: '600' }}>
                Cash Flow Statement
              </h3>
              {Object.entries(extractedData.cashflow).map(([period, data]) => (
                <div key={period} style={{ marginBottom: '20px', paddingBottom: '20px', borderBottom: '1px solid #e5e7eb' }}>
                  <h4 style={{ fontSize: '16px', marginBottom: '12px', color: '#374151', fontWeight: '600' }}>
                    Period: {period}
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '12px' }}>
                    {Object.entries(data).map(([key, value]) => (
                      <div key={key} style={{
                        padding: '12px',
                        backgroundColor: '#f9fafb',
                        borderRadius: '6px',
                        border: '1px solid #e5e7eb'
                      }}>
                        <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>
                          {key}
                        </div>
                        <div style={{ fontSize: '16px', fontWeight: '600', color: '#111827' }}>
                          {formatNumber(value)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Key Metrics */}
          {extractedData.key_metrics && Object.keys(extractedData.key_metrics).length > 0 && (
            <div style={{
              marginBottom: '24px',
              padding: '20px',
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px'
            }}>
              <h3 style={{ fontSize: '20px', marginBottom: '16px', color: '#111827', fontWeight: '600' }}>
                Key Metrics
              </h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '12px' }}>
                {Object.entries(extractedData.key_metrics).map(([key, value]) => (
                  <div key={key} style={{
                    padding: '12px',
                    backgroundColor: '#f9fafb',
                    borderRadius: '6px',
                    border: '1px solid #e5e7eb'
                  }}>
                    <div style={{ fontSize: '12px', color: '#6b7280', marginBottom: '4px' }}>
                      {key}
                    </div>
                    <div style={{ fontSize: '16px', fontWeight: '600', color: '#111827' }}>
                      {typeof value === 'number' ? formatNumber(value) : String(value)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Raw JSON View */}
          <div style={{
            marginTop: '24px',
            padding: '20px',
            backgroundColor: '#f9fafb',
            border: '1px solid #e5e7eb',
            borderRadius: '8px'
          }}>
            <h3 style={{ fontSize: '18px', marginBottom: '12px', color: '#111827', fontWeight: '600' }}>
              Raw Extracted Data (JSON)
            </h3>
            <pre style={{
              padding: '16px',
              backgroundColor: 'white',
              border: '1px solid #d1d5db',
              borderRadius: '6px',
              overflow: 'auto',
              fontSize: '12px',
              maxHeight: '400px'
            }}>
              {JSON.stringify(extractedData, null, 2)}
            </pre>
          </div>
        </div>
      )}

      {/* Info Section */}
      <div style={{ marginTop: '40px', padding: '20px', backgroundColor: '#f9fafb', borderRadius: '8px' }}>
        <h3 style={{ fontSize: '18px', marginBottom: '12px', color: '#111827' }}>How It Works:</h3>
        <ul style={{ color: '#6b7280', lineHeight: '1.8', paddingLeft: '20px' }}>
          <li>Enter a stock ticker symbol and upload a PDF financial statement</li>
          <li>The LLM agent analyzes the PDF and extracts all financial data fields</li>
          <li>Extracted data includes Income Statements, Balance Sheets, Cash Flow Statements, and Key Metrics</li>
          <li>All extracted values are displayed on this page for review</li>
          <li>The data is automatically stored and will be used in subsequent stock analyses</li>
        </ul>
      </div>
    </div>
  )
}

