import axios from 'axios'
import { logApiEvent } from '@/components/DeveloperFeedback'
import { WatchlistSimulation } from './watchlist-simulation'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor for logging
api.interceptors.request.use(
  (config) => {
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
                  // Stream ended - check if we have any remaining data
                  if (buffer.trim()) {
                    const lines = buffer.split('\n')
                    for (const line of lines) {
                      const trimmed = line.trim()
                      if (trimmed.startsWith('data: ')) {
                        try {
                          const data = trimmed.slice(6).trim()
                          if (data) {
                            const update: ProgressUpdate = JSON.parse(data)
                            console.log('Final update from buffer:', update)
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
                  console.error('Stream ended without completion message. Buffer:', buffer)
                  reject(new Error('Stream ended without completion'))
                  return
                }

                const chunk = decoder.decode(value, { stream: true })
                buffer += chunk
                
                // Process complete lines
                const lines = buffer.split('\n')
                buffer = lines.pop() || ''

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
      const params: any = {}
      if (forceRefresh) params.force_refresh = true
      if (businessType) params.business_type = businessType
      if (weights) params.weights = JSON.stringify(weights)
      const response = await api.get<StockAnalysis>(`/api/analyze/${ticker}`, { params })
      return response.data
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
    const response = await api.get<SearchResponse>(`/api/search`, {
      params: { q: query }
    })
    return response.data.results
  },

  async addManualData(ticker: string, dataType: string, period: string, data: Record<string, number>): Promise<{ success: boolean; message: string }> {
    const response = await api.post('/api/manual-data', {
      ticker,
      data_type: dataType,
      period,
      data
    })
    return response.data
  },

  async uploadPDF(ticker: string, file: File): Promise<{ success: boolean; message: string; updated_periods: number; extracted_data?: any; extraction_details?: any }> {
    const formData = new FormData()
    formData.append('file', file)
    
    try {
      console.log(`Uploading PDF for ticker: ${ticker}`)
      const response = await api.post<{ success: boolean; message: string; updated_periods: number; extracted_data?: any; extraction_details?: any }>(`/api/upload-pdf?ticker=${ticker}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 600000, // 10 minute timeout for large PDFs
      })
      console.log('Upload response:', response.data)
      return response.data
    } catch (error: any) {
      console.error('Upload PDF error:', error)
      console.error('Error response:', error.response?.data)
      throw error
    }
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
    console.log('=== getWatchlist DEBUG ===')
    try {
      const response = await api.get<{ items: WatchlistItem[]; total: number }>('/api/watchlist')
      console.log('API watchlist response:', response.data)
      
      // Merge with client-side watchlist
      const clientWatchlist = WatchlistSimulation.getWatchlist()
      console.log('Client-side watchlist:', clientWatchlist)
      
      const apiItems = response.data.items || []
      console.log('API items:', apiItems)
      
      // Convert client-side items to API format
      const clientItems: WatchlistItem[] = clientWatchlist.map(item => ({
        ticker: item.ticker,
        company_name: item.companyName,
        exchange: item.exchange,
        added_at: item.addedAt,
        notes: item.notes,
        // Add some mock data for display
        current_price: 150.00,
        fair_value: 180.00,
        margin_of_safety_pct: 16.67,
        recommendation: 'BUY'
      }))
      console.log('Converted client items:', clientItems)
      
      // Merge and deduplicate
      const allItems = [...apiItems, ...clientItems]
      console.log('All items before deduplication:', allItems)
      
      const uniqueItems = allItems.filter((item, index, self) => 
        index === self.findIndex(i => i.ticker === item.ticker)
      )
      console.log('Unique items after deduplication:', uniqueItems)
      
      const result = {
        items: uniqueItems,
        total: uniqueItems.length
      }
      console.log('Final getWatchlist result:', result)
      console.log('=== END getWatchlist DEBUG ===')
      return result
    } catch (error) {
      // Fallback to client-side only
      console.log('API watchlist not available, using client-side only')
      const clientWatchlist = WatchlistSimulation.getWatchlist()
      console.log('Client-side watchlist (fallback):', clientWatchlist)
      
      const items: WatchlistItem[] = clientWatchlist.map(item => ({
        ticker: item.ticker,
        company_name: item.companyName,
        exchange: item.exchange,
        added_at: item.addedAt,
        notes: item.notes,
        // Add some mock data for display
        current_price: 150.00,
        fair_value: 180.00,
        margin_of_safety_pct: 16.67,
        recommendation: 'BUY'
      }))
      
      const result = {
        items,
        total: items.length
      }
      console.log('Fallback result:', result)
      console.log('=== END getWatchlist DEBUG ===')
      return result
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
        return response.data
      } else if (response.data.watchlist_item) {
        // Old format: { watchlist_item: {...}, latest_analysis: {...} }
        // This means the API processed the request but returned the wrong format
        // Since the API is mock and doesn't actually save, also save to client-side
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
    const response = await api.get<WatchlistItemDetail>(`/api/watchlist/${ticker}`, { params })
    return response.data
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

