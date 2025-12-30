import axios from 'axios'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface StockAnalysis {
  ticker: string
  companyName: string
  currentPrice: number
  fairValue: number
  marginOfSafety: number
  upsidePotential: number
  priceToIntrinsicValue: number
  recommendation: 'Strong Buy' | 'Buy' | 'Hold' | 'Avoid'
  recommendationReasoning: string
  valuation: {
    dcf: number
    earningsPower: number
    assetBased: number
    weightedAverage: number
  }
  financialHealth: {
    score: number
    metrics: {
      debtToEquity: number
      currentRatio: number
      quickRatio: number
      interestCoverage: number
      roe: number
      roic: number
      roa: number
      fcfMargin: number
    }
  }
  businessQuality: {
    score: number
    moatIndicators: string[]
    competitivePosition: string
  }
  managementQuality?: {
    score: number
    strengths: string[]
    weaknesses: string[]
  }
  growthMetrics?: {
    revenueGrowth1Y?: number | null
    revenueGrowth3Y?: number | null
    revenueGrowth5Y?: number | null
    earningsGrowth1Y?: number | null
    earningsGrowth3Y?: number | null
    earningsGrowth5Y?: number | null
    fcfGrowth1Y?: number | null
    fcfGrowth3Y?: number | null
    fcfGrowth5Y?: number | null
  }
  priceRatios?: {
    priceToEarnings?: number | null
    priceToBook?: number | null
    priceToSales?: number | null
    priceToFCF?: number | null
    enterpriseValueToEBITDA?: number | null
  }
  currency?: string
  financialCurrency?: string
  timestamp: string
  dataQualityWarnings?: Array<{
    category: string
    field: string
    message: string
    severity: string
    assumed_value?: number | null
    actual_value?: number | null
  }>
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
  async analyzeStock(
    ticker: string,
    onProgress?: (update: ProgressUpdate) => void
  ): Promise<StockAnalysis> {
    if (onProgress) {
      // Use streaming endpoint with progress updates using fetch
      return new Promise(async (resolve, reject) => {
        try {
          console.log(`Fetching analysis for ${ticker} with streaming...`)
          console.log(`URL: ${API_BASE_URL}/api/analyze/${ticker}?stream=true`)
          
          // Add timeout to detect if fetch hangs
          const controller = new AbortController()
          const timeoutId = setTimeout(() => {
            console.error('Fetch timeout after 30 seconds')
            controller.abort()
          }, 30000)
          
          try {
            const response = await fetch(`${API_BASE_URL}/api/analyze/${ticker}?stream=true`, {
              headers: {
                'Accept': 'text/event-stream',
              },
              signal: controller.signal
            })
            clearTimeout(timeoutId)

            console.log('Response status:', response.status, response.statusText)
            console.log('Response headers:', Object.fromEntries(response.headers.entries()))
            if (!response.ok) {
              const errorText = await response.text()
              console.error('Error response:', errorText)
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
              try {
                const { done, value } = await reader.read()
                chunkCount++
                
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
                        
                        if (update.type === 'complete' && update.data) {
                          console.log('Analysis complete!')
                          resolve(update.data)
                          return
                        } else if (update.type === 'error') {
                          console.error('Error from server:', update.message)
                          reject(new Error(update.message || 'Analysis failed'))
                          return
                        } else if (update.type === 'progress') {
                          onProgress(update)
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
              } catch (error) {
                console.error('Error reading stream:', error)
                reject(error)
                return
              }
            }
          } catch (error: any) {
            clearTimeout(timeoutId)
            if (error.name === 'AbortError') {
              console.error('Request was aborted (timeout or cancelled)')
              reject(new Error('Request timeout - backend may not be responding'))
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
      const response = await api.get<StockAnalysis>(`/api/analyze/${ticker}`)
      return response.data
    }
  },

  async getQuote(ticker: string): Promise<QuoteResponse> {
    const response = await api.get<QuoteResponse>(`/api/quote/${ticker}`)
    return response.data
  },

  async searchTickers(query: string): Promise<SearchResult[]> {
    if (!query || query.trim().length === 0) {
      return []
    }
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

  async uploadPDF(ticker: string, file: File): Promise<{ success: boolean; message: string; updated_periods?: number; extracted_data?: any; extraction_details?: any }> {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await api.post<{ success: boolean; message: string; updated_periods?: number; extracted_data?: any }>(`/api/upload-pdf?ticker=${ticker}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
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
}

