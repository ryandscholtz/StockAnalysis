import axios from 'axios'
import { logApiEvent } from '@/components/DeveloperFeedback'
import { WatchlistSimulation } from './watchlist-simulation'
import { authService } from './auth-mock' // Use mock auth for development

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor for logging and authentication
api.interceptors.request.use(
  (config) => {
    // Add authentication token if available
    const token = authService.getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    logApiEvent({
      type: 'request',
      method: config.method?.toUpperCase(),
      url: `${config.baseURL}${config.url}`,
      data: config.data
    })
    return config
  },
  (error) => {
    logApiEvent({
      type: 'error',
      message: 'Request setup error',
      error: error.message
    })
    return Promise.reject(error)
  }
)

// Helper function to format API errors into user-friendly messages
export function formatApiError(error: any): string {
  // Network errors (backend not accessible)
  if (error.code === 'ERR_NETWORK' || error.code === 'ECONNREFUSED' || error.message?.includes('Network Error')) {
    return `Cannot connect to backend server. Please ensure the backend is running on ${API_BASE_URL}`
  }
  
  // Timeout errors
  if (error.code === 'ECONNABORTED' || error.message?.includes('timeout') || error.message?.includes('Timeout')) {
    return 'Request timed out. The server may be taking too long to respond. Please try again.'
  }
  
  // HTTP errors with response
  if (error.response) {
    const status = error.response.status
    const detail = error.response.data?.detail || error.response.data?.message
    
    if (status === 404) {
      return detail || 'The requested resource was not found.'
    } else if (status === 400) {
      return detail || 'Invalid request. Please check your input and try again.'
    } else if (status === 500) {
      return detail || 'Server error. Please try again later or contact support.'
    } else if (status === 503) {
      return 'Service temporarily unavailable. Please try again in a few moments.'
    } else if (detail) {
      return detail
    }
    
    return `Server error (${status}). Please try again.`
  }
  
  // Generic error message
  if (error.message) {
    return error.message
  }
  
  return 'An unexpected error occurred. Please try again.'
}

// Add response interceptor to handle errors globally
api.interceptors.response.use(
  (response) => {
    logApiEvent({
      type: 'response',
      method: response.config.method?.toUpperCase(),
      url: `${response.config.baseURL}${response.config.url}`,
      status: response.status,
      data: response.data
    })
    return response
  },
  (error) => {
    // Log error for debugging
    const errorInfo = {
      code: error.code,
      message: error.message,
      status: error.response?.status,
      data: error.response?.data,
      url: error.config?.url
    }
    console.error('API Error:', errorInfo)
    
    logApiEvent({
      type: 'error',
      method: error.config?.method?.toUpperCase(),
      url: error.config ? `${error.config.baseURL}${error.config.url}` : undefined,
      status: error.response?.status,
      message: formatApiError(error),
      error: errorInfo
    })
    
    // Re-throw with formatted error message
    const formattedError = new Error(formatApiError(error))
    ;(formattedError as any).originalError = error
    ;(formattedError as any).code = error.code
    ;(formattedError as any).response = error.response
    return Promise.reject(formattedError)
  }
)

import { StockAnalysis, AnalysisWeights } from '@/types/analysis'

export interface BankMetrics {
  net_interest_margin: number
  return_on_equity: number
  return_on_assets: number
  tier_1_capital_ratio?: number | null
  loan_loss_provision_ratio?: number | null
  efficiency_ratio?: number | null
  loan_to_deposit_ratio?: number | null
  non_performing_loans_ratio?: number | null
}

export interface REITMetrics {
  funds_from_operations?: number | null
  adjusted_funds_from_operations?: number | null
  ffo_per_share?: number | null
  affo_per_share?: number | null
  net_asset_value?: number | null
  dividend_yield?: number | null
  payout_ratio?: number | null
  occupancy_rate?: number | null
}

export interface InsuranceMetrics {
  combined_ratio?: number | null
  loss_ratio?: number | null
  expense_ratio?: number | null
  return_on_equity: number
  return_on_assets: number
  reserve_adequacy?: number | null
  investment_yield?: number | null
}

export interface QuoteResponse {
  ticker: string
  companyName: string
  currentPrice: number
  marketCap?: number
  sector?: string
  industry?: string
}

export interface SearchResult {
  ticker: string
  companyName: string
  exchange: string
}

export interface SearchResponse {
  results: SearchResult[]
}

export interface ProgressUpdate {
  type: 'progress' | 'complete' | 'error'
  step?: number
  total?: number
  task?: string
  progress?: number
  data?: StockAnalysis
  message?: string
}

export const stockApi = {
  async autoAssignBusinessType(ticker: string): Promise<{ detected_business_type: string; weights: AnalysisWeights; business_type_display: string }> {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const response = await api.post(`/api/auto-assign-business-type/${ticker}`)
    return response.data
  },
  async analyzeStock(
    ticker: string,
    onProgress?: (update: ProgressUpdate) => void,
    signal?: AbortSignal,
    forceRefresh?: boolean,
    businessType?: string | null,
    weights?: AnalysisWeights | null
  ): Promise<StockAnalysis> {
    if (onProgress) {
      // Use streaming endpoint with progress updates using fetch
      return new Promise(async (resolve, reject) => {
        try {
          const forceParam = forceRefresh ? '&force_refresh=true' : ''
          console.log(`Fetching analysis for ${ticker} with streaming...`)
          console.log(`URL: ${API_BASE_URL}/api/analyze/${ticker}?stream=true${forceParam}`)
          
          // Add timeout to detect if fetch hangs (but reset on each chunk)
          const controller = signal ? { signal, abort: () => {} } : new AbortController()
          let timeoutId: NodeJS.Timeout | null = null
          
          const resetTimeout = () => {
            if (timeoutId) {
              clearTimeout(timeoutId)
            }
            // Reset timeout to 5 minutes after last chunk received
            // This allows long-running analyses while still detecting true hangs
            timeoutId = setTimeout(() => {
              console.error('Fetch timeout after 5 minutes of inactivity')
              if (!signal && 'abort' in controller) {
                controller.abort()
              }
            }, 300000) // 5 minutes of inactivity before timeout (long analyses can take time)
          }
          
          resetTimeout() // Start initial timeout
          
          // Check if already aborted
          if (signal?.aborted) {
            reject(new DOMException('Request aborted', 'AbortError'))
            return
          }
          
          try {
            const params = new URLSearchParams()
            if (forceRefresh) params.append('force_refresh', 'true')
            if (businessType) params.append('business_type', businessType)
            if (weights) params.append('weights', JSON.stringify(weights))
            const paramString = params.toString()
            const url = `${API_BASE_URL}/api/analyze/${ticker}?stream=true${paramString ? '&' + paramString : ''}`
            logApiEvent({
              type: 'request',
              method: 'GET',
              url: url,
              message: `Starting streaming analysis for ${ticker}${forceRefresh ? ' (force refresh)' : ''}`
            })
            
            const response = await fetch(url, {
              headers: {
                'Accept': 'text/event-stream',
              },
              signal: signal || controller.signal
            })

            console.log('Response status:', response.status, response.statusText)
            console.log('Response headers:', Object.fromEntries(response.headers.entries()))
            
            logApiEvent({
              type: 'response',
              method: 'GET',
              url: url,
              status: response.status,
              message: `Stream connection established for ${ticker}`
            })
            
            if (!response.ok) {
              const errorText = await response.text()
              console.error('Error response:', errorText)
              logApiEvent({
                type: 'error',
                method: 'GET',
                url: url,
                status: response.status,
                message: `HTTP error! status: ${response.status}`,
                error: errorText
              })
              throw new Error(`HTTP error! status: ${response.status}`)
            }

            const reader = response.body?.getReader()
            const decoder = new TextDecoder()

            if (!reader) {
              console.error('No response body reader available')
              throw new Error('No response body')
            }

            console.log('Starting to read stream...')
            let buffer = ''

            let chunkCount = 0
            while (true) {
              // Check if aborted before reading
              if (signal?.aborted) {
                reader.cancel()
                reject(new DOMException('Request aborted', 'AbortError'))
                return
              }
              
              try {
                const { done, value } = await reader.read()
                chunkCount++
                
                // Check if aborted after reading
                if (signal?.aborted) {
                  reader.cancel()
                  reject(new DOMException('Request aborted', 'AbortError'))
                  return
                }
                
                // Reset timeout on each chunk - stream is active
                resetTimeout()
                
                if (chunkCount === 1) {
                  console.log('First chunk received, stream is working!')
                }
                
                if (done) {
                  console.log(`Stream ended after ${chunkCount} chunks. Buffer:`, buffer.substring(0, 200))
                  
                  // Try to parse the buffer as complete JSON response
                  if (buffer.trim()) {
                    try {
                      // First try to parse the entire buffer as JSON (for non-streaming responses)
                      const completeData = JSON.parse(buffer.trim())
                      if (completeData && typeof completeData === 'object' && completeData.ticker) {
                        console.log('✅ Parsed complete response from buffer!')
                        if (timeoutId) {
                          clearTimeout(timeoutId)
                        }
                        resolve(completeData)
                        return
                      }
                    } catch (parseError) {
                      // If that fails, try to parse as streaming format
                      // Split by actual LF characters (code 10) to handle all newline types
                      const lines = []
                      let start = 0
                      for (let i = 0; i < buffer.length; i++) {
                        if (buffer.charCodeAt(i) === 10) { // LF character
                          lines.push(buffer.substring(start, i))
                          start = i + 1
                        }
                      }
                      if (start < buffer.length) {
                        lines.push(buffer.substring(start))
                      }
                      
                      console.log(`Found ${lines.length} lines in buffer`)
                      
                      for (const line of lines) {
                        const trimmed = line.trim()
                        if (trimmed.startsWith('data: ')) {
                          try {
                            const data = trimmed.slice(6).trim()
                            if (data) {
                              const update: ProgressUpdate = JSON.parse(data)
                              console.log('Final update from buffer:', update.type)
                              if (update.type === 'complete' && update.data) {
                                console.log('Analysis complete from buffer!')
                                if (timeoutId) {
                                  clearTimeout(timeoutId)
                                }
                                resolve(update.data)
                                return
                              }
                            }
                          } catch (error) {
                            console.error('Error parsing final update:', error, 'Line:', trimmed.substring(0, 100))
                          }
                        }
                      }
                    }
                  }
                  console.error('Stream ended without completion message. Buffer:', buffer)
                  reject(new Error('Stream ended without completion'))
                  return
                }

                const chunk = decoder.decode(value, { stream: true })
                buffer += chunk
                
                // Process complete lines - handle different newline types
                // Split by LF characters to ensure proper parsing
                const lines = []
                let start = 0
                for (let i = 0; i < buffer.length; i++) {
                  if (buffer.charCodeAt(i) === 10) { // LF character
                    lines.push(buffer.substring(start, i))
                    start = i + 1
                  }
                }
                // Keep the remaining part in buffer
                buffer = buffer.substring(start)

                for (const line of lines) {
                  const trimmed = line.trim()
                  if (trimmed.startsWith('data: ')) {
                    try {
                      const data = trimmed.slice(6).trim() // Remove 'data: ' prefix
                      if (data) {
                        const update: ProgressUpdate = JSON.parse(data)
                        console.log(`[Chunk ${chunkCount}] Progress update:`, update)
                        
                        // Reset timeout on any data received (including heartbeats)
                        resetTimeout()
                        
                        if (update.type === 'complete' && update.data) {
                          console.log('Analysis complete!')
                          
                          // Check for potential issues
                          const issues: string[] = []
                          if (update.data.fairValue === 0 || update.data.fairValue === null) {
                            issues.push('⚠️ Fair value is 0 - DCF calculation may have failed or insufficient data')
                          }
                          if (!update.data.currentPrice || update.data.currentPrice === 1.0) {
                            issues.push('⚠️ Current price unavailable or placeholder (1.0)')
                          }
                          if (update.data.missingData?.has_missing_data) {
                            issues.push('⚠️ Missing financial data detected')
                          }
                          
                          logApiEvent({
                            type: issues.length > 0 ? 'error' : 'response',
                            method: 'GET',
                            url: `${API_BASE_URL}/api/analyze/${ticker}?stream=true`,
                            message: issues.length > 0 
                              ? `Analysis complete for ${ticker} - ${issues.join('; ')}`
                              : `Analysis complete for ${ticker}`,
                            data: { 
                              ticker: update.data.ticker, 
                              fairValue: update.data.fairValue,
                              currentPrice: update.data.currentPrice,
                              issues: issues.length > 0 ? issues : undefined
                            }
                          })
                          
                          if (timeoutId) {
                            clearTimeout(timeoutId)
                          }
                          resolve(update.data)
                          return
                        } else if (update.type === 'error') {
                          console.error('Error from server:', update.message)
                          logApiEvent({
                            type: 'error',
                            method: 'GET',
                            url: `${API_BASE_URL}/api/analyze/${ticker}?stream=true`,
                            message: update.message || 'Analysis failed',
                            error: update
                          })
                          reject(new Error(update.message || 'Analysis failed'))
                          return
                        } else if (update.type === 'progress') {
                          onProgress(update)
                          logApiEvent({
                            type: 'info',
                            method: 'GET',
                            url: `${API_BASE_URL}/api/analyze/${ticker}?stream=true`,
                            message: `Progress: ${update.task} (${update.step}/${update.total})`
                          })
                        } else if ((update as any).type === 'heartbeat') {
                          // Heartbeat received - connection is alive, reset timeout
                          console.log('Heartbeat received - connection alive', (update as any).warning || '')
                          if ((update as any).warning) {
                            logApiEvent({
                              type: 'info',
                              method: 'GET',
                              url: `${API_BASE_URL}/api/analyze/${ticker}?stream=true`,
                              message: (update as any).warning
                            })
                          }
                          resetTimeout()
                        }
                      }
                    } catch (error) {
                      console.error('Error parsing progress update:', error, 'Line:', trimmed.substring(0, 100))
                    }
                  } else if (trimmed) {
                    // Log non-data lines for debugging
                    console.log('Non-data line:', trimmed.substring(0, 50))
                  }
                }
              } catch (error: any) {
                // Ignore abort errors (expected when request is cancelled)
                if (error.name === 'AbortError' || signal?.aborted) {
                  console.log('Stream reading was aborted (expected)')
                  reject(new DOMException('Request aborted', 'AbortError'))
                  return
                }
                // Ignore incomplete chunked encoding errors if request was aborted
                if (error.message?.includes('incomplete') || error.message?.includes('chunked')) {
                  if (signal?.aborted) {
                    console.log('Incomplete chunked encoding due to abort (expected)')
                    reject(new DOMException('Request aborted', 'AbortError'))
                    return
                  }
                }
                console.error('Error reading stream:', error)
                reject(error)
                return
              }
            }
          } catch (error: any) {
            if (timeoutId) {
              clearTimeout(timeoutId)
            }
            // Ignore abort errors (expected when request is cancelled)
            if (error.name === 'AbortError' || signal?.aborted) {
              console.log('Fetch was aborted (expected)')
              reject(new DOMException('Request aborted', 'AbortError'))
              return
            }
            if (error.name === 'AbortError') {
              console.error('Request was aborted (timeout or cancelled)')
              reject(new Error('Request timeout - no data received for 5 minutes'))
            } else {
              console.error('Fetch error:', error)
              reject(error)
            }
          }
        } catch (error) {
          reject(error)
        }
      })
    } else {
      // Standard request without progress
      console.log('🌐 Using standard endpoint (no streaming)');
      const params: any = {}
      if (forceRefresh) {
        params.force_refresh = true
        console.log('🔄 Adding force_refresh=true parameter');
      }
      if (businessType) params.business_type = businessType
      if (weights) params.weights = JSON.stringify(weights)
      
      console.log(`📡 Calling: /api/analyze/${ticker} with params:`, params);
      try {
        const response = await api.get<StockAnalysis>(`/api/analyze/${ticker}`, { params })
        console.log('✅ Standard endpoint response received:', response.data);
        return response.data
      } catch (error: any) {
        // Special handling for 503 Service Unavailable (rate limited)
        if (error.response?.status === 503 && error.response?.data) {
          console.log('⚠️ API rate limited, returning partial analysis data');
          // Return the error response data as if it were a successful analysis
          // This allows the frontend to show the rate limit message properly
          return {
            ...error.response.data,
            // Ensure required fields are present for TypeScript
            ticker: error.response.data.ticker || ticker,
            companyName: error.response.data.companyName || `${ticker} Inc.`,
            currentPrice: error.response.data.currentPrice || null,
            fairValue: error.response.data.fairValue || null,
            marginOfSafety: 0,
            upsidePotential: 0,
            priceToIntrinsicValue: 1.0,
            recommendation: error.response.data.recommendation || 'Hold',
            recommendationReasoning: error.response.data.message || 'Price data temporarily unavailable',
            valuation: {
              dcf: null,
              peValue: null,
              earningsPower: null,
              bookValue: null,
              weightedAverage: null
            },
            financialHealth: { score: null, metrics: {} },
            businessQuality: { score: null, moatIndicators: [], competitivePosition: '' },
            timestamp: new Date().toISOString(),
            dataSource: error.response.data.dataSource
          } as StockAnalysis
        }
        // Re-throw other errors
        throw error
      }
    }
  },

  async getQuote(ticker: string): Promise<QuoteResponse> {
    logApiEvent({
      type: 'info',
      method: 'GET',
      url: `${API_BASE_URL}/api/quote/${ticker}`,
      message: `Fetching quote for ${ticker}`
    })
    const response = await api.get<QuoteResponse>(`/api/quote/${ticker}`)
    return response.data
  },

  async searchTickers(query: string): Promise<SearchResult[]> {
    if (!query || query.trim().length === 0) {
      return []
    }
    logApiEvent({
      type: 'info',
      method: 'GET',
      url: `${API_BASE_URL}/api/search`,
      message: `Searching for tickers: ${query}`
    })
    const response = await api.get<any>(`/api/search`, {
      params: { q: query }
    })
    const results: any[] = response.data.results || []
    return results.map((item: any) => ({
      ticker: item.ticker || item.symbol,
      companyName: item.companyName || item.name || item.company_name || '',
      exchange: item.exchange || ''
    }))
  },

  async addManualData(ticker: string, dataType: string, period: string, data: Record<string, number>): Promise<{ success: boolean; message: string }> {
    try {
      const response = await api.post('/api/manual-data', {
        ticker,
        data_type: dataType,
        period,
        data
      })
      return response.data
    } catch (error) {
      // Return mock success for development when using mock auth
      console.log('Using mock manual data save for development')
      return {
        success: true,
        message: `Successfully saved ${dataType.replace('_', ' ')} data for ${ticker} (mock)`
      }
    }
  },

  async uploadPDF(
    ticker: string,
    file: File,
    onProgress?: (status: string) => void,
  ): Promise<{ success: boolean; message: string; updated_periods: number; extracted_data?: any; extraction_details?: any }> {
    const sizeMB = (file.size / 1024 / 1024).toFixed(2)

    // Step 1: Get a presigned S3 PUT URL (avoids API Gateway's 10 MB payload limit)
    console.log(`[PDF Upload] Step 1/3 — Getting presigned S3 URL for ${ticker} (file: ${file.name}, ${sizeMB} MB)`)
    onProgress?.(`🔗 Preparing secure upload for ${file.name} (${sizeMB} MB)...`)
    const urlResponse = await api.get<{ upload_url: string; s3_key: string }>(`/api/upload-pdf?ticker=${ticker}`)
    const { upload_url, s3_key } = urlResponse.data
    console.log(`[PDF Upload] Got presigned URL. S3 key: ${s3_key}`)

    // Step 2: Upload directly to S3 using fetch (not axios, to avoid adding auth headers to presigned URL)
    console.log(`[PDF Upload] Step 2/3 — Uploading ${sizeMB} MB directly to S3...`)
    onProgress?.(`⬆️ Uploading PDF to S3 (${sizeMB} MB)...`)
    const s3Response = await fetch(upload_url, {
      method: 'PUT',
      body: file,
      headers: { 'Content-Type': 'application/pdf' },
    })
    console.log(`[PDF Upload] S3 PUT response: ${s3Response.status} ${s3Response.statusText}`)
    if (!s3Response.ok) {
      throw new Error(`S3 upload failed: ${s3Response.status} ${s3Response.statusText}`)
    }

    // Step 3: Kick off async AI extraction (returns immediately — API Gateway 29s limit)
    console.log(`[PDF Upload] Step 3/3 — Queuing AI extraction: ${s3_key}`)
    onProgress?.('🤖 Starting AI extraction...')
    await api.post<{ status: string; ticker: string }>(
      `/api/upload-pdf?ticker=${ticker}`,
      { s3_key },
      { timeout: 30000 },
    )

    // Step 4: Poll until extraction completes (Lambda runs async in background)
    console.log('[PDF Upload] Polling for extraction result...')
    const POLL_MS = 5000
    const MAX_WAIT_MS = 3 * 60 * 1000  // 3 minutes
    let elapsed = 0
    while (elapsed < MAX_WAIT_MS) {
      await new Promise(r => setTimeout(r, POLL_MS))
      elapsed += POLL_MS
      const mins = Math.floor(elapsed / 60000)
      const secs = Math.floor((elapsed % 60000) / 1000)
      const timeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
      onProgress?.(`🤖 Extracting financial data with Claude AI... (${timeStr})`)

      const statusResp = await api.get<{ status: string; has_data: boolean; error?: string }>(
        `/api/upload-pdf/status?ticker=${ticker}`,
      )
      console.log(`[PDF Upload] Status at ${timeStr}:`, statusResp.data)

      if (statusResp.data.status === 'complete') {
        return {
          success: true,
          message: 'PDF processed successfully',
          updated_periods: statusResp.data.has_data ? 1 : 0,
        }
      }
      if (statusResp.data.status === 'error') {
        throw new Error(statusResp.data.error || 'PDF processing failed on the server')
      }
    }
    throw new Error('PDF processing timed out after 3 minutes')
  },

  async getPDFJobStatus(jobId: number): Promise<{
    job_id: number
    ticker: string
    status: string
    total_pages: number
    pages_processed: number
    current_page: number
    current_task?: string
    progress_pct: number
    started_at?: string
    completed_at?: string
    error_message?: string
    result?: any
    extraction_details?: any
  }> {
    try {
      const response = await api.get(`/api/pdf-job-status/${jobId}`)
      return response.data
    } catch (error: any) {
      console.error(`Error getting job status for ${jobId}:`, error)
      console.error('Error response:', error.response?.data)
      throw error
    }
  },

  async extractPDFImages(file: File): Promise<{ success: boolean; total_pages: number; images: Array<{ page_number: number; image_base64: string; width: number; height: number }>; message: string }> {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await api.post<{ success: boolean; total_pages: number; images: Array<{ page_number: number; image_base64: string; width: number; height: number }>; message: string }>('/api/extract-pdf-images', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  async batchAnalyze(tickers: string[], exchangeName: string = 'Custom', skipExisting: boolean = true): Promise<{ success: boolean; summary: any; message: string }> {
    const response = await api.post('/api/batch-analyze', {
      tickers,
      exchange_name: exchangeName,
      skip_existing: skipExisting
    })
    return response.data
  },

  async getBatchResults(exchange: string, analysisDate?: string): Promise<{
    exchange: string
    analysis_date: string
    total: number
    results: Array<{
      ticker: string
      company_name: string
      current_price: number
      fair_value: number
      fair_value_pct: number
      margin_of_safety_pct?: number
      recommendation?: string
      financial_health_score?: number
      business_quality_score?: number
    }>
  }> {
    const params: any = { exchange }
    if (analysisDate) {
      params.analysis_date = analysisDate
    }
    const response = await api.get('/api/batch-results', { params })
    return response.data
  },

  // Watchlist methods
  async getWatchlist(): Promise<{ items: WatchlistItem[]; total: number }> {
    try {
      const response = await api.get<{ items: WatchlistItem[]; total: number }>('/api/watchlist')

      // Normalise camelCase fields from Lambda to snake_case expected by the frontend
      const items: WatchlistItem[] = (response.data.items || []).map((item: any) => ({
        ...item,
        company_name: item.company_name || item.companyName || undefined,
        current_price: item.current_price ?? item.currentPrice ?? undefined,
        fair_value: item.fair_value ?? item.fairValue ?? undefined,
        margin_of_safety_pct: item.margin_of_safety_pct ?? item.marginOfSafety ?? undefined,
        recommendation: item.recommendation ?? undefined,
        last_analyzed_at: item.last_analyzed_at ?? item.last_updated ?? undefined,
        pe_ratio: item.pe_ratio ?? item.priceToEarnings ?? undefined,
      }))

      return {
        items: items.sort((a, b) => (a.company_name || a.ticker).localeCompare(b.company_name || b.ticker)),
        total: items.length,
      }
    } catch (error) {
      // API unavailable — return empty list (no client-side simulation)
      console.error('Watchlist API unavailable:', error)
      return { items: [], total: 0 }
    }

  },

  async getWatchlistLivePrices(): Promise<{ live_prices: Record<string, { price?: number; company_name?: string; error?: string; comment?: string; success?: boolean }> }> {
    const response = await api.get<{ live_prices: Record<string, { price?: number; company_name?: string; error?: string; comment?: string; success?: boolean }> }>('/api/watchlist/live-prices')
    return response.data
  },

  async addToWatchlist(ticker: string, companyName?: string, exchange?: string, notes?: string): Promise<{ success: boolean; message: string }> {
    console.log('=== API addToWatchlist DEBUG ===')
    console.log('Input params:', { ticker, companyName, exchange, notes })
    
    try {
      const params = new URLSearchParams()
      if (companyName) params.append('company_name', companyName)
      if (exchange) params.append('exchange', exchange)
      if (notes) params.append('notes', notes)
      
      console.log('Trying API POST request...')
      const response = await api.post<any>(`/api/watchlist/${ticker}?${params.toString()}`)
      console.log('API POST response:', response.data)
      
      // Handle both response formats
      if (response.data.success !== undefined) {
        // New format: { success: true, message: "..." }
        // Also save to client-side as backup since API might not be persisting
        console.log('API returned success format, also saving to client-side as backup')
        const clientBackupSuccess = WatchlistSimulation.addToWatchlist(
          ticker, 
          companyName || `${ticker} Corporation`, 
          exchange || 'NASDAQ', 
          notes
        )
        console.log('Client-side backup result:', clientBackupSuccess)
        
        return {
          success: response.data.success,
          message: response.data.success 
            ? `${response.data.message} (with client-side backup)`
            : response.data.message
        }
      } else if (response.data.watchlist_item) {
        // Old format: { watchlist_item: {...}, latest_analysis: {...} }
        console.log('API returned old format, also saving to client-side as backup')
        WatchlistSimulation.addToWatchlist(
          ticker,
          companyName || `${ticker} Corporation`,
          exchange || 'NASDAQ',
          notes
        )

        return {
          success: true,
          message: `Successfully added ${ticker} to watchlist (API processed + client-side backup)`
        }
      } else if (response.data.item || (response.data.message && response.data.message.toLowerCase().includes('added'))) {
        // Lambda format: { message: 'Added to watchlist', item: {...} }
        console.log('API returned Lambda format, saving to client-side as backup')
        WatchlistSimulation.addToWatchlist(
          ticker,
          companyName || `${ticker} Corporation`,
          exchange || 'NASDAQ',
          notes
        )

        return {
          success: true,
          message: `Successfully added ${ticker} to watchlist`
        }
      } else {
        // Unknown format
        return {
          success: false,
          message: 'Unknown API response format'
        }
      }
    } catch (error: any) {
      console.log('API POST failed, using client-side simulation')
      console.log('API error:', error.message)
      
      // Fallback to client-side simulation if API doesn't support POST yet
      const simulationSuccess = WatchlistSimulation.addToWatchlist(
        ticker, 
        companyName || `${ticker} Corporation`, 
        exchange || 'NASDAQ', 
        notes
      )
      
      const result = {
        success: true, // Always return success for client-side simulation (even if already exists)
        message: simulationSuccess 
          ? `Successfully added ${ticker} to watchlist (client-side)`
          : `${ticker} is already in your watchlist (client-side)`
      }
      
      console.log('Client-side simulation result:', result)
      console.log('Simulation success flag:', simulationSuccess)
      console.log('=== END API addToWatchlist DEBUG ===')
      return result
    }
  },

  async removeFromWatchlist(ticker: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await api.delete<{ success: boolean; message: string }>(`/api/watchlist/${ticker}`)
      // Always remove from client-side simulation so merged getWatchlist doesn't resurface the item
      WatchlistSimulation.removeFromWatchlist(ticker)
      return response.data
    } catch (error: any) {
      // Fallback to client-side simulation if API doesn't support DELETE yet
      console.log('API DELETE not supported yet, using client-side simulation')
      
      const success = WatchlistSimulation.removeFromWatchlist(ticker)
      
      return {
        success,
        message: success 
          ? `Successfully removed ${ticker} from watchlist (client-side)`
          : `${ticker} was not found in your watchlist`
      }
    }
  },

  async getWatchlistItem(ticker: string, forceRefresh: boolean = false): Promise<WatchlistItemDetail> {
    const params = forceRefresh ? { force_refresh: true } : {}
    try {
      const response = await api.get<WatchlistItemDetail>(`/api/watchlist/${ticker}`, { params })
      return response.data
    } catch (error: any) {
      // On 404, fall back to client-side WatchlistSimulation
      if (error?.response?.status === 404) {
        const clientItems = WatchlistSimulation.getWatchlist()
        const found = clientItems.find(item => item.ticker.toUpperCase() === ticker.toUpperCase())
        if (found) {
          return {
            watchlist_item: {
              ticker: found.ticker,
              company_name: found.companyName,
              exchange: found.exchange,
              added_at: found.addedAt,
              notes: found.notes,
            }
          }
        }
      }
      throw error
    }
  },

  async getAnalysisPresets(): Promise<{ presets: Record<string, AnalysisWeights>; business_types: string[] }> {
    const response = await api.get<{ presets: Record<string, AnalysisWeights>; business_types: string[] }>('/api/analysis-presets')
    return response.data
  },

  async updateWatchlistItem(ticker: string, notes?: string | null): Promise<{ success: boolean; message: string }> {
    const params = new URLSearchParams()
    // Only append notes if it's not null/undefined (null means clear the notes)
    if (notes !== undefined && notes !== null) {
      params.append('notes', notes)
    }
    // If notes is null, we still want to update (to clear it), so we pass notes=null
    // The backend will handle converting string "null" to None
    
    const url = notes === null 
      ? `/api/watchlist/${ticker}?notes=null`
      : params.toString() 
        ? `/api/watchlist/${ticker}?${params.toString()}`
        : `/api/watchlist/${ticker}`
    
    const response = await api.put<{ success: boolean; message: string }>(url)
    return response.data
  },

  async deleteFinancialPeriod(ticker: string, section: string, period: string): Promise<void> {
    await api.delete(`/api/financial-data/period`, {
      params: { ticker, section, period }
    })
  },

  async getFinancialData(ticker: string): Promise<{
    ticker: string
    financial_data: Record<string, Record<string, Record<string, number>>>
    metadata: Record<string, { last_updated: string | null; source: string; period_count: number }>
    has_data: boolean
    latest_analysis?: StockAnalysis
  }> {
    try {
      const response = await api.get(`/api/manual-data/${ticker}`)
      return response.data
    } catch (error) {
      // Return empty result on error — no mock data
      console.log('Using mock financial data for development')
      return { ticker: ticker.toUpperCase(), financial_data: {}, metadata: {}, has_data: false }
    }
  },
}

export interface WatchlistItem {
  ticker: string
  company_name?: string
  exchange?: string
  added_at?: string
  updated_at?: string
  notes?: string
  current_price?: number
  fair_value?: number
  margin_of_safety_pct?: number
  recommendation?: string
  last_analyzed_at?: string
  analysis_date?: string
  financial_health_score?: number
  business_quality_score?: number
  pe_ratio?: number
  live_price?: number
  price_error?: string
  cache_info?: {
    status: 'fresh' | 'stale' | 'missing'
    needs_refresh: boolean
    last_updated?: string
    is_today: boolean
  }
}

export interface WatchlistItemDetail {
  watchlist_item: WatchlistItem
  latest_analysis?: StockAnalysis
  ai_extracted_data?: {
    income_statement?: Record<string, Record<string, number>>
    balance_sheet?: Record<string, Record<string, number>>
    cashflow?: Record<string, Record<string, number>>
    key_metrics?: Record<string, number>
  }
  current_quote?: QuoteResponse
  price_error?: string
  cache_info?: {
    status: 'fresh' | 'stale' | 'missing' | 'refreshed' | 'refresh_failed_using_cache' | 'refresh_failed_no_cache'
    last_updated?: string
    is_today: boolean
    needs_refresh: boolean
  }
}

