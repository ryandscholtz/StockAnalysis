'use client'

import { useState, useRef } from 'react'
import { stockApi, SearchResult } from '@/lib/api'

interface PDFUploadItem {
  id: string
  ticker: string
  file: File | null
  uploading: boolean
  message: string
  error: string
  status: 'pending' | 'uploading' | 'success' | 'error'
  extractedData?: any
}

interface MultiplePDFUploadProps {
  onAllComplete?: () => void
  onItemComplete?: (ticker: string) => void
}

export default function MultiplePDFUpload({ onAllComplete, onItemComplete }: MultiplePDFUploadProps) {
  const [items, setItems] = useState<PDFUploadItem[]>([
    { id: '1', ticker: '', file: null, uploading: false, message: '', error: '', status: 'pending' }
  ])
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [suggestions, setSuggestions] = useState<SearchResult[]>([])
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false)
  const [searchLoading, setSearchLoading] = useState<boolean>(false)
  const [selectedIndex, setSelectedIndex] = useState<number>(-1)
  const [activeSearchIndex, setActiveSearchIndex] = useState<number>(-1)
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)
  const fileInputRefs = useRef<{ [key: string]: HTMLInputElement | null }>({})

  // Search for tickers with debounce
  const handleSearch = (query: string, itemIndex: number) => {
    setActiveSearchIndex(itemIndex)
    setSearchQuery(query)
    
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    if (query.trim().length >= 1) {
      setSearchLoading(true)
      searchTimeoutRef.current = setTimeout(async () => {
        try {
          const results = await stockApi.searchTickers(query.trim())
          // Ensure results is always an array
          const safeResults = Array.isArray(results) ? results : []
          setSuggestions(safeResults)
          setShowSuggestions(safeResults.length > 0)
          setSelectedIndex(-1)
        } catch (error) {
          console.error('Search error:', error)
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
  }

  const handleSelectSuggestion = (suggestion: SearchResult, itemIndex: number) => {
    setItems(prev => prev.map((item, idx) => 
      idx === itemIndex ? { ...item, ticker: suggestion.ticker } : item
    ))
    setSearchQuery('')
    setShowSuggestions(false)
    setSelectedIndex(-1)
  }

  const addNewItem = () => {
    const newId = `${Date.now()}`
    setItems(prev => [...prev, {
      id: newId,
      ticker: '',
      file: null,
      uploading: false,
      message: '',
      error: '',
      status: 'pending'
    }])
  }

  const removeItem = (id: string) => {
    setItems(prev => prev.filter(item => item.id !== id))
  }

  const handleFileSelect = async (file: File, itemId: string) => {
    const item = items.find(i => i.id === itemId)
    if (!item) return

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setItems(prev => prev.map(i => 
        i.id === itemId ? { ...i, error: 'Please select a PDF file' } : i
      ))
      return
    }

    if (file.size > 50 * 1024 * 1024) {
      setItems(prev => prev.map(i => 
        i.id === itemId ? { ...i, error: 'File size must be less than 50MB' } : i
      ))
      return
    }

    if (!item.ticker || item.ticker.trim().length === 0) {
      setItems(prev => prev.map(i => 
        i.id === itemId ? { ...i, error: 'Please enter a ticker symbol' } : i
      ))
      return
    }

    setItems(prev => prev.map(i => 
      i.id === itemId ? { 
        ...i, 
        file, 
        uploading: true, 
        error: '', 
        message: '', 
        status: 'uploading' 
      } : i
    ))

    let progressInterval: NodeJS.Timeout | null = null
    let elapsedSeconds = 0

    try {
      // Step 1: Convert PDF to images
      let imageCount = 0
      try {
        const imageResult = await stockApi.extractPDFImages(file)
        if (imageResult.success && imageResult.images.length > 0) {
          imageCount = imageResult.total_pages
        }
      } catch (imgErr: any) {
        console.warn('Image extraction failed (non-critical):', imgErr)
      }

      // Step 2: Process images with LLM vision
      progressInterval = setInterval(() => {
        elapsedSeconds += 15
        const minutes = Math.floor(elapsedSeconds / 60)
        const seconds = elapsedSeconds % 60
        const timeStr = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`
        setItems(prev => prev.map(i => 
          i.id === itemId ? { 
            ...i, 
            message: `Processing... (${timeStr} elapsed, ${imageCount} page(s))` 
          } : i
        ))
      }, 15000)

      const result = await stockApi.uploadPDF(item.ticker.trim().toUpperCase(), file)
      
      if (progressInterval) {
        clearInterval(progressInterval)
      }

      setItems(prev => prev.map(i => {
        if (i.id === itemId) {
          const status: 'success' | 'error' = result.updated_periods && result.updated_periods > 0 ? 'success' : 'error'
          const newItem: PDFUploadItem = {
            ...i,
            uploading: false,
            status,
            message: result.message || (result.updated_periods && result.updated_periods > 0 
              ? `✅ Extracted ${result.updated_periods} data period(s)` 
              : '⚠️ No data extracted'),
            extractedData: result.extracted_data
          }
          
          if (onItemComplete) {
            setTimeout(() => onItemComplete(item.ticker), 500)
          }
          
          return newItem
        }
        return i
      }))

      // Check if all items are complete (already updated above)
      const updatedItems = items.map(i => {
        if (i.id === itemId) {
          const status: 'success' | 'error' = result.updated_periods && result.updated_periods > 0 ? 'success' : 'error'
          return { ...i, uploading: false, status }
        }
        return i
      })
      
      const allComplete = updatedItems.every(i => 
        i.status === 'success' || i.status === 'error' || !i.file
      )
      
      if (allComplete && onAllComplete) {
        setTimeout(() => onAllComplete(), 1000)
      }

    } catch (err: any) {
      if (progressInterval) {
        clearInterval(progressInterval)
      }
      setItems(prev => prev.map(i => 
        i.id === itemId ? { 
          ...i, 
          uploading: false, 
          error: err.response?.data?.detail || err.message || 'Error uploading PDF',
          status: 'error'
        } : i
      ))
    } finally {
      if (progressInterval) {
        clearInterval(progressInterval)
      }
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: React.DragEvent, itemId: string) => {
    e.preventDefault()
    e.stopPropagation()
    
    const file = e.dataTransfer.files?.[0]
    if (file && file.name.toLowerCase().endsWith('.pdf')) {
      handleFileSelect(file, itemId)
    } else {
      setItems(prev => prev.map(i => 
        i.id === itemId ? { ...i, error: 'Please drop a PDF file' } : i
      ))
    }
  }

  const completedCount = items.filter(i => i.status === 'success').length
  const totalWithFiles = items.filter(i => i.file).length

  return (
    <div style={{ marginTop: '32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h2 style={{ fontSize: '24px', fontWeight: '600', color: '#111827' }}>
          Upload PDF Financial Statements
        </h2>
        <button
          onClick={addNewItem}
          style={{
            padding: '8px 16px',
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: '500'
          }}
        >
          + Add Another PDF
        </button>
      </div>

      <p style={{ fontSize: '14px', color: '#6b7280', marginBottom: '24px' }}>
        Upload PDF financial statements for each ticker. The AI will extract financial data automatically.
        {totalWithFiles > 0 && (
          <span style={{ marginLeft: '8px', fontWeight: '500', color: '#059669' }}>
            {completedCount} of {totalWithFiles} completed
          </span>
        )}
      </p>

      {items.map((item, index) => (
        <div
          key={item.id}
          style={{
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            padding: '20px',
            marginBottom: '16px',
            backgroundColor: item.status === 'success' ? '#f0fdf4' : item.status === 'error' ? '#fef2f2' : 'white'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#111827', margin: 0 }}>
              PDF #{index + 1}
            </h3>
            {items.length > 1 && (
              <button
                onClick={() => removeItem(item.id)}
                style={{
                  padding: '4px 8px',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '12px'
                }}
              >
                Remove
              </button>
            )}
          </div>

          {/* Ticker Input */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#374151' }}>
              Ticker Symbol *
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                value={item.ticker}
                onChange={(e) => {
                  setItems(prev => prev.map(i => 
                    i.id === item.id ? { ...i, ticker: e.target.value } : i
                  ))
                  handleSearch(e.target.value, index)
                }}
                onFocus={() => {
                  if (suggestions.length > 0) {
                    setShowSuggestions(true)
                  }
                }}
                placeholder="Enter or search ticker (e.g., AAPL, MSFT)"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '6px',
                  fontSize: '14px',
                  outline: 'none'
                }}
              />
              
              {showSuggestions && activeSearchIndex === index && suggestions.length > 0 && (
                <div
                  ref={suggestionsRef}
                  style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    right: 0,
                    backgroundColor: 'white',
                    border: '1px solid #d1d5db',
                    borderRadius: '6px',
                    marginTop: '4px',
                    maxHeight: '200px',
                    overflowY: 'auto',
                    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                    zIndex: 1000
                  }}
                >
                  {suggestions.map((suggestion, idx) => (
                    <div
                      key={`${suggestion.ticker}-${idx}`}
                      onClick={() => handleSelectSuggestion(suggestion, index)}
                      style={{
                        padding: '10px 12px',
                        cursor: 'pointer',
                        borderBottom: idx < suggestions.length - 1 ? '1px solid #e5e7eb' : 'none',
                        backgroundColor: selectedIndex === idx ? '#f3f4f6' : 'white'
                      }}
                    >
                      <div style={{ fontWeight: '600', fontSize: '14px' }}>{suggestion.ticker}</div>
                      {suggestion.companyName && (
                        <div style={{ fontSize: '12px', color: '#6b7280' }}>{suggestion.companyName}</div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* File Upload */}
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500', color: '#374151' }}>
              PDF File *
            </label>
            <div
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, item.id)}
              style={{
                border: '2px dashed #d1d5db',
                borderRadius: '8px',
                padding: '24px',
                textAlign: 'center',
                cursor: 'pointer',
                backgroundColor: item.file ? '#f9fafb' : 'white',
                transition: 'border-color 0.2s'
              }}
              onClick={() => fileInputRefs.current[item.id]?.click()}
            >
              <input
                ref={(el) => { fileInputRefs.current[item.id] = el }}
                type="file"
                accept=".pdf"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) {
                    handleFileSelect(file, item.id)
                  }
                }}
              />
              
              {item.file ? (
                <div>
                  <div style={{ fontSize: '14px', fontWeight: '500', color: '#111827', marginBottom: '4px' }}>
                    {item.file.name}
                  </div>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>
                    {(item.file.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: '14px', color: '#6b7280', marginBottom: '8px' }}>
                    Click to select or drag and drop PDF file
                  </div>
                  <div style={{ fontSize: '12px', color: '#9ca3af' }}>
                    Maximum file size: 50MB
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Status Messages */}
          {item.uploading && item.message && (
            <div style={{ marginTop: '12px', padding: '12px', backgroundColor: '#eff6ff', borderRadius: '6px', fontSize: '14px', color: '#1e40af' }}>
              {item.message}
            </div>
          )}

          {item.status === 'success' && item.message && (
            <div style={{ marginTop: '12px', padding: '12px', backgroundColor: '#d1fae5', borderRadius: '6px', fontSize: '14px', color: '#065f46' }}>
              {item.message}
            </div>
          )}

          {item.error && (
            <div style={{ marginTop: '12px', padding: '12px', backgroundColor: '#fee2e2', borderRadius: '6px', fontSize: '14px', color: '#991b1b' }}>
              {item.error}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

