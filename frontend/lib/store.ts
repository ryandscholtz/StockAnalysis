import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import { StockAnalysis } from '@/types/analysis'

interface AppState {
  // Analysis state
  analyses: StockAnalysis[]
  currentAnalysis: StockAnalysis | null
  loading: boolean
  error: string | null
  
  // UI state
  sidebarOpen: boolean
  theme: 'light' | 'dark'
  
  // Actions
  setAnalyses: (analyses: StockAnalysis[]) => void
  addAnalysis: (analysis: StockAnalysis) => void
  updateAnalysis: (ticker: string, analysis: StockAnalysis) => void
  removeAnalysis: (ticker: string) => void
  setCurrentAnalysis: (analysis: StockAnalysis | null) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearError: () => void
  
  // UI actions
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  setTheme: (theme: 'light' | 'dark') => void
  
  // Async actions
  fetchAnalysis: (ticker: string) => Promise<void>
  refreshAnalysis: (ticker: string) => Promise<void>
}

export const useAppStore = create<AppState>()(
  devtools(
    (set, get) => ({
      // Initial state
      analyses: [],
      currentAnalysis: null,
      loading: false,
      error: null,
      sidebarOpen: false,
      theme: 'light',
      
      // Sync actions
      setAnalyses: (analyses) => set({ analyses }),
      
      addAnalysis: (analysis) => set((state) => ({
        analyses: [...state.analyses.filter(a => a.ticker !== analysis.ticker), analysis]
      })),
      
      updateAnalysis: (ticker, analysis) => set((state) => ({
        analyses: state.analyses.map(a => a.ticker === ticker ? analysis : a),
        currentAnalysis: state.currentAnalysis?.ticker === ticker ? analysis : state.currentAnalysis
      })),
      
      removeAnalysis: (ticker) => set((state) => ({
        analyses: state.analyses.filter(a => a.ticker !== ticker),
        currentAnalysis: state.currentAnalysis?.ticker === ticker ? null : state.currentAnalysis
      })),
      
      setCurrentAnalysis: (analysis) => set({ currentAnalysis: analysis }),
      
      setLoading: (loading) => set({ loading }),
      
      setError: (error) => set({ error }),
      
      clearError: () => set({ error: null }),
      
      // UI actions
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      
      setTheme: (theme) => set({ theme }),
      
      // Async actions
      fetchAnalysis: async (ticker: string) => {
        const { setLoading, setError, addAnalysis } = get()
        
        setLoading(true)
        setError(null)
        
        try {
          const response = await fetch(`/api/analyze/${ticker}`)
          if (!response.ok) {
            throw new Error(`Failed to fetch analysis: ${response.statusText}`)
          }
          
          const analysis: StockAnalysis = await response.json()
          addAnalysis(analysis)
        } catch (error) {
          setError(error instanceof Error ? error.message : 'Unknown error occurred')
        } finally {
          setLoading(false)
        }
      },
      
      refreshAnalysis: async (ticker: string) => {
        const { setLoading, setError, updateAnalysis } = get()
        
        setLoading(true)
        setError(null)
        
        try {
          const response = await fetch(`/api/analyze/${ticker}?refresh=true`)
          if (!response.ok) {
            throw new Error(`Failed to refresh analysis: ${response.statusText}`)
          }
          
          const analysis: StockAnalysis = await response.json()
          updateAnalysis(ticker, analysis)
        } catch (error) {
          setError(error instanceof Error ? error.message : 'Unknown error occurred')
        } finally {
          setLoading(false)
        }
      }
    }),
    {
      name: 'app-store',
    }
  )
)