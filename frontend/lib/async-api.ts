/**
 * Enhanced API client with background task support and optimized caching
 */

interface TaskStatus {
  id: string
  task_type: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  created_at: string
  started_at?: string
  completed_at?: string
  result?: any
  error?: string
  metadata?: any
}

interface BackgroundTaskResponse {
  task_id: string
  status: string
  message: string
  poll_url: string
}

interface CachedResponse<T> {
  cached: boolean
  timestamp: string
  data: T
}

class AsyncApiClient {
  private baseUrl: string
  private pollingIntervals: Map<string, NodeJS.Timeout> = new Map()

  constructor(baseUrl: string = 'http://127.0.0.1:8000/api') {
    this.baseUrl = baseUrl
  }

  /**
   * Start background task for live price fetching
   */
  async startLivePricesTask(): Promise<BackgroundTaskResponse> {
    const response = await fetch(`${this.baseUrl}/watchlist/live-prices-async`)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    return response.json()
  }

  /**
   * Start background task for stock analysis
   */
  async startAnalysisTask(
    ticker: string, 
    businessType?: string, 
    analysisWeights?: any
  ): Promise<BackgroundTaskResponse> {
    const params = new URLSearchParams()
    if (businessType) params.append('business_type', businessType)
    if (analysisWeights) params.append('analysis_weights', JSON.stringify(analysisWeights))
    
    const url = `${this.baseUrl}/analyze/${ticker}/async${params.toString() ? '?' + params.toString() : ''}`
    const response = await fetch(url)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    return response.json()
  }

  /**
   * Get task status and results
   */
  async getTaskStatus(taskId: string): Promise<TaskStatus> {
    const response = await fetch(`${this.baseUrl}/tasks/${taskId}`)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    return response.json()
  }

  /**
   * Cancel a running task
   */
  async cancelTask(taskId: string): Promise<{ message: string }> {
    const response = await fetch(`${this.baseUrl}/tasks/${taskId}`, {
      method: 'DELETE'
    })
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    return response.json()
  }

  /**
   * Poll task until completion with progress updates
   */
  async pollTaskWithProgress(
    taskId: string,
    onProgress?: (status: TaskStatus) => void,
    onComplete?: (result: any) => void,
    onError?: (error: string) => void,
    pollIntervalMs: number = 2000
  ): Promise<TaskStatus> {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const status = await this.getTaskStatus(taskId)
          
          // Call progress callback
          if (onProgress) {
            onProgress(status)
          }
          
          // Check if task is complete
          if (status.status === 'completed') {
            this.stopPolling(taskId)
            if (onComplete && status.result) {
              onComplete(status.result)
            }
            resolve(status)
          } else if (status.status === 'failed') {
            this.stopPolling(taskId)
            const error = status.error || 'Task failed with unknown error'
            if (onError) {
              onError(error)
            }
            reject(new Error(error))
          } else if (status.status === 'cancelled') {
            this.stopPolling(taskId)
            reject(new Error('Task was cancelled'))
          }
          // Continue polling for pending/running tasks
          
        } catch (error) {
          this.stopPolling(taskId)
          const errorMsg = error instanceof Error ? error.message : 'Unknown polling error'
          if (onError) {
            onError(errorMsg)
          }
          reject(error)
        }
      }
      
      // Start polling
      const interval = setInterval(poll, pollIntervalMs)
      this.pollingIntervals.set(taskId, interval)
      
      // Initial poll
      poll()
    })
  }

  /**
   * Stop polling for a specific task
   */
  stopPolling(taskId: string): void {
    const interval = this.pollingIntervals.get(taskId)
    if (interval) {
      clearInterval(interval)
      this.pollingIntervals.delete(taskId)
    }
  }

  /**
   * Stop all polling
   */
  stopAllPolling(): void {
    for (const [taskId, interval] of this.pollingIntervals) {
      clearInterval(interval)
    }
    this.pollingIntervals.clear()
  }

  /**
   * Get cached watchlist data (instant response)
   */
  async getCachedWatchlist(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/watchlist/cached`)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    return response.json()
  }

  /**
   * Get cached quote data (instant response)
   */
  async getCachedQuote(ticker: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/quote/${ticker}/cached`)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    return response.json()
  }

  /**
   * Get cache statistics
   */
  async getCacheStats(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/cache/stats`)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    return response.json()
  }

  /**
   * Clear cache
   */
  async clearCache(): Promise<{ message: string }> {
    const response = await fetch(`${this.baseUrl}/cache`, {
      method: 'DELETE'
    })
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    return response.json()
  }

  /**
   * Get detailed health status
   */
  async getDetailedHealth(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/health/detailed`)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    return response.json()
  }

  /**
   * High-level method: Get live prices with automatic fallback
   */
  async getLivePricesOptimized(
    onProgress?: (status: TaskStatus) => void
  ): Promise<any> {
    try {
      // Try to start background task
      const taskResponse = await this.startLivePricesTask()
      
      // If we got cached results immediately, return them
      if ('live_prices' in taskResponse) {
        return taskResponse
      }
      
      // Otherwise, poll for results
      const finalStatus = await this.pollTaskWithProgress(
        taskResponse.task_id,
        onProgress
      )
      
      return finalStatus.result
      
    } catch (error) {
      console.error('Error in optimized live prices fetch:', error)
      throw error
    }
  }

  /**
   * High-level method: Analyze stock with automatic fallback
   */
  async analyzeStockOptimized(
    ticker: string,
    businessType?: string,
    analysisWeights?: any,
    onProgress?: (status: TaskStatus) => void
  ): Promise<any> {
    try {
      // Try to start background task
      const taskResponse = await this.startAnalysisTask(ticker, businessType, analysisWeights)
      
      // If we got cached results immediately, return them
      if ('analysis' in taskResponse) {
        return taskResponse
      }
      
      // Otherwise, poll for results
      const finalStatus = await this.pollTaskWithProgress(
        taskResponse.task_id,
        onProgress
      )
      
      return finalStatus.result
      
    } catch (error) {
      console.error(`Error in optimized analysis for ${ticker}:`, error)
      throw error
    }
  }
}

// Export singleton instance
export const asyncApi = new AsyncApiClient()
export type { TaskStatus, BackgroundTaskResponse, CachedResponse }