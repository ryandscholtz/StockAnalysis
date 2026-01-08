/**
 * React hook for managing background tasks with progress tracking
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import { asyncApi, TaskStatus } from '@/lib/async-api'

interface UseBackgroundTaskOptions {
  pollInterval?: number
  autoStart?: boolean
  onProgress?: (status: TaskStatus) => void
  onComplete?: (result: any) => void
  onError?: (error: string) => void
}

interface UseBackgroundTaskReturn {
  // State
  isLoading: boolean
  progress: number
  status: TaskStatus['status'] | null
  result: any
  error: string | null
  taskId: string | null
  
  // Actions
  startTask: (taskPromise: Promise<any>) => Promise<void>
  cancelTask: () => Promise<void>
  reset: () => void
  
  // Task-specific helpers
  startLivePrices: () => Promise<void>
  startAnalysis: (ticker: string, businessType?: string, analysisWeights?: any) => Promise<void>
}

export function useBackgroundTask(options: UseBackgroundTaskOptions = {}): UseBackgroundTaskReturn {
  const {
    pollInterval = 2000,
    autoStart = false,
    onProgress,
    onComplete,
    onError
  } = options

  // State
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState<TaskStatus['status'] | null>(null)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [taskId, setTaskId] = useState<string | null>(null)

  // Refs to track current task
  const currentTaskIdRef = useRef<string | null>(null)
  const isActiveRef = useRef(true)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isActiveRef.current = false
      if (currentTaskIdRef.current) {
        asyncApi.stopPolling(currentTaskIdRef.current)
      }
    }
  }, [])

  // Reset state
  const reset = useCallback(() => {
    if (currentTaskIdRef.current) {
      asyncApi.stopPolling(currentTaskIdRef.current)
    }
    
    setIsLoading(false)
    setProgress(0)
    setStatus(null)
    setResult(null)
    setError(null)
    setTaskId(null)
    currentTaskIdRef.current = null
  }, [])

  // Cancel current task
  const cancelTask = useCallback(async () => {
    if (currentTaskIdRef.current) {
      try {
        await asyncApi.cancelTask(currentTaskIdRef.current)
        asyncApi.stopPolling(currentTaskIdRef.current)
        
        if (isActiveRef.current) {
          setStatus('cancelled')
          setIsLoading(false)
        }
      } catch (err) {
        console.error('Error cancelling task:', err)
      }
    }
  }, [])

  // Start a background task
  const startTask = useCallback(async (taskPromise: Promise<any>) => {
    // Reset previous state
    reset()
    
    if (!isActiveRef.current) return

    setIsLoading(true)
    setError(null)
    setStatus('pending')

    try {
      // Start the task
      const taskResponse = await taskPromise
      
      // Check if we got immediate results (cached)
      if ('live_prices' in taskResponse || 'analysis' in taskResponse) {
        if (isActiveRef.current) {
          setResult(taskResponse)
          setStatus('completed')
          setProgress(100)
          setIsLoading(false)
          
          if (onComplete) {
            onComplete(taskResponse)
          }
        }
        return
      }

      // We got a task ID, start polling
      const newTaskId = taskResponse.task_id
      setTaskId(newTaskId)
      currentTaskIdRef.current = newTaskId

      // Poll for progress and results
      await asyncApi.pollTaskWithProgress(
        newTaskId,
        (taskStatus) => {
          if (!isActiveRef.current || currentTaskIdRef.current !== newTaskId) return

          setStatus(taskStatus.status)
          setProgress(taskStatus.progress)
          
          if (onProgress) {
            onProgress(taskStatus)
          }
        },
        (taskResult) => {
          if (!isActiveRef.current || currentTaskIdRef.current !== newTaskId) return

          setResult(taskResult)
          setIsLoading(false)
          
          if (onComplete) {
            onComplete(taskResult)
          }
        },
        (taskError) => {
          if (!isActiveRef.current || currentTaskIdRef.current !== newTaskId) return

          setError(taskError)
          setIsLoading(false)
          
          if (onError) {
            onError(taskError)
          }
        },
        pollInterval
      )

    } catch (err) {
      if (!isActiveRef.current) return

      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      setError(errorMessage)
      setIsLoading(false)
      setStatus('failed')
      
      if (onError) {
        onError(errorMessage)
      }
    }
  }, [pollInterval, onProgress, onComplete, onError, reset])

  // Helper: Start live prices task
  const startLivePrices = useCallback(async () => {
    await startTask(asyncApi.startLivePricesTask())
  }, [startTask])

  // Helper: Start analysis task
  const startAnalysis = useCallback(async (
    ticker: string, 
    businessType?: string, 
    analysisWeights?: any
  ) => {
    await startTask(asyncApi.startAnalysisTask(ticker, businessType, analysisWeights))
  }, [startTask])

  return {
    // State
    isLoading,
    progress,
    status,
    result,
    error,
    taskId,
    
    // Actions
    startTask,
    cancelTask,
    reset,
    
    // Helpers
    startLivePrices,
    startAnalysis
  }
}

// Hook for live prices specifically
export function useLivePrices(options: UseBackgroundTaskOptions = {}) {
  const task = useBackgroundTask(options)
  
  const refreshPrices = useCallback(async () => {
    await task.startLivePrices()
  }, [task])

  return {
    ...task,
    refreshPrices,
    livePrices: task.result?.live_prices || {}
  }
}

// Hook for stock analysis specifically
export function useStockAnalysis(options: UseBackgroundTaskOptions = {}) {
  const task = useBackgroundTask(options)
  
  const analyzeStock = useCallback(async (
    ticker: string, 
    businessType?: string, 
    analysisWeights?: any
  ) => {
    await task.startAnalysis(ticker, businessType, analysisWeights)
  }, [task])

  return {
    ...task,
    analyzeStock,
    analysis: task.result
  }
}