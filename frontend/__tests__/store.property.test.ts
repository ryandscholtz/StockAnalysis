/**
 * Property-based tests for state management consistency
 * Feature: tech-stack-modernization, Property 6: State Management Consistency
 */

import { renderHook, act, cleanup } from '@testing-library/react'
import * as fc from 'fast-check'
import { useAppStore } from '@/lib/store'
import { StockAnalysis } from '@/types/analysis'

// Generators for property-based testing
const tickerArbitrary = fc.string({ minLength: 1, maxLength: 10 })
  .filter(s => /^[A-Z0-9]+$/.test(s.toUpperCase()))
  .map(s => s.toUpperCase())

const priceArbitrary = fc.float({ min: Math.fround(0.01), max: Math.fround(10000), noNaN: true })

const recommendationArbitrary = fc.constantFrom('Strong Buy', 'Buy', 'Hold', 'Avoid')

const stockAnalysisArbitrary = fc.record({
  ticker: tickerArbitrary,
  companyName: fc.string({ minLength: 1, maxLength: 100 }),
  currentPrice: priceArbitrary,
  fairValue: priceArbitrary,
  marginOfSafety: fc.float({ min: Math.fround(-100), max: Math.fround(100) }),
  upsidePotential: fc.float({ min: Math.fround(-100), max: Math.fround(500) }),
  priceToIntrinsicValue: fc.float({ min: Math.fround(0.1), max: Math.fround(10) }),
  recommendation: recommendationArbitrary,
  recommendationReasoning: fc.string({ minLength: 10, maxLength: 200 }),
  valuation: fc.record({
    dcf: priceArbitrary,
    earningsPower: priceArbitrary,
    assetBased: priceArbitrary,
    weightedAverage: priceArbitrary,
  }),
  financialHealth: fc.record({
    score: fc.float({ min: Math.fround(0), max: Math.fround(10) }),
    metrics: fc.record({
      debtToEquity: fc.float({ min: Math.fround(0), max: Math.fround(10) }),
      currentRatio: fc.float({ min: Math.fround(0), max: Math.fround(10) }),
      quickRatio: fc.float({ min: Math.fround(0), max: Math.fround(10) }),
      interestCoverage: fc.float({ min: Math.fround(0), max: Math.fround(100) }),
      roe: fc.float({ min: Math.fround(-50), max: Math.fround(100) }),
      roic: fc.float({ min: Math.fround(-50), max: Math.fround(100) }),
      roa: fc.float({ min: Math.fround(-50), max: Math.fround(100) }),
      fcfMargin: fc.float({ min: Math.fround(-50), max: Math.fround(100) }),
    }),
  }),
  businessQuality: fc.record({
    score: fc.float({ min: Math.fround(0), max: Math.fround(10) }),
    moatIndicators: fc.array(fc.string(), { minLength: 0, maxLength: 5 }),
    competitivePosition: fc.string({ minLength: 10, maxLength: 100 }),
  }),
  timestamp: fc.date().map(d => d.toISOString()),
}) as fc.Arbitrary<StockAnalysis>

// Helper function to reset store state
function resetStoreState() {
  act(() => {
    useAppStore.setState({
      analyses: [],
      currentAnalysis: null,
      loading: false,
      error: null,
      sidebarOpen: false,
      theme: 'light'
    })
  })
}

describe('State Management Consistency Properties', () => {
  beforeEach(() => {
    // Reset store state before each test
    resetStoreState()
    cleanup()
  })

  afterEach(() => {
    // Clean up after each test
    resetStoreState()
    cleanup()
  })

  it('Property 6: State Management Consistency - Adding analysis should be reflected in all store consumers', () => {
    fc.assert(fc.property(
      stockAnalysisArbitrary,
      (analysis) => {
        // Reset store before this property test iteration
        resetStoreState()
        
        const { result: result1 } = renderHook(() => useAppStore())
        const { result: result2 } = renderHook(() => useAppStore())
        
        // Both hooks should start with empty analyses
        expect(result1.current.analyses).toEqual([])
        expect(result2.current.analyses).toEqual([])
        
        // Add analysis through first hook
        act(() => {
          result1.current.addAnalysis(analysis)
        })
        
        // Both hooks should see the same updated state
        expect(result1.current.analyses).toHaveLength(1)
        expect(result2.current.analyses).toHaveLength(1)
        expect(result1.current.analyses[0]).toEqual(analysis)
        expect(result2.current.analyses[0]).toEqual(analysis)
        
        // State should be identical across all consumers
        expect(result1.current.analyses).toEqual(result2.current.analyses)
        
        // Clean up after this iteration
        resetStoreState()
      }
    ), { numRuns: 50 })
  })

  it('Property 6: State Management Consistency - Updating analysis should maintain consistency', () => {
    fc.assert(fc.property(
      stockAnalysisArbitrary,
      stockAnalysisArbitrary,
      (initialAnalysis, updatedAnalysis) => {
        // Reset store before this property test iteration
        resetStoreState()
        
        // Ensure both analyses have the same ticker for update test
        const sameTickerUpdated = { ...updatedAnalysis, ticker: initialAnalysis.ticker }
        
        const { result: result1 } = renderHook(() => useAppStore())
        const { result: result2 } = renderHook(() => useAppStore())
        
        // Add initial analysis
        act(() => {
          result1.current.addAnalysis(initialAnalysis)
        })
        
        // Update analysis through second hook
        act(() => {
          result2.current.updateAnalysis(initialAnalysis.ticker, sameTickerUpdated)
        })
        
        // Both hooks should see the updated analysis
        expect(result1.current.analyses).toHaveLength(1)
        expect(result2.current.analyses).toHaveLength(1)
        expect(result1.current.analyses[0]).toEqual(sameTickerUpdated)
        expect(result2.current.analyses[0]).toEqual(sameTickerUpdated)
        
        // State should be consistent across consumers
        expect(result1.current.analyses).toEqual(result2.current.analyses)
        
        // Clean up after this iteration
        resetStoreState()
      }
    ), { numRuns: 50 })
  })

  it('Property 6: State Management Consistency - Error state should be synchronized', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 1, maxLength: 100 }),
      (errorMessage) => {
        // Reset store before this property test iteration
        resetStoreState()
        
        const { result: result1 } = renderHook(() => useAppStore())
        const { result: result2 } = renderHook(() => useAppStore())
        
        // Set error through first hook
        act(() => {
          result1.current.setError(errorMessage)
        })
        
        // Both hooks should see the same error state
        expect(result1.current.error).toBe(errorMessage)
        expect(result2.current.error).toBe(errorMessage)
        
        // Clear error through second hook
        act(() => {
          result2.current.clearError()
        })
        
        // Both hooks should see error cleared
        expect(result1.current.error).toBeNull()
        expect(result2.current.error).toBeNull()
        
        // Clean up after this iteration
        resetStoreState()
      }
    ), { numRuns: 50 })
  })

  it('Property 6: State Management Consistency - Loading state should be synchronized', () => {
    fc.assert(fc.property(
      fc.boolean(),
      (loadingState) => {
        // Reset store before this property test iteration
        resetStoreState()
        
        const { result: result1 } = renderHook(() => useAppStore())
        const { result: result2 } = renderHook(() => useAppStore())
        
        // Set loading state through first hook
        act(() => {
          result1.current.setLoading(loadingState)
        })
        
        // Both hooks should see the same loading state
        expect(result1.current.loading).toBe(loadingState)
        expect(result2.current.loading).toBe(loadingState)
        
        // Clean up after this iteration
        resetStoreState()
      }
    ), { numRuns: 50 })
  })

  it('Property 6: State Management Consistency - UI state should be synchronized', () => {
    fc.assert(fc.property(
      fc.boolean(),
      fc.constantFrom('light', 'dark'),
      (sidebarOpen, theme) => {
        // Reset store before this property test iteration
        resetStoreState()
        
        const { result: result1 } = renderHook(() => useAppStore())
        const { result: result2 } = renderHook(() => useAppStore())
        
        // Update UI state through first hook
        act(() => {
          result1.current.setSidebarOpen(sidebarOpen)
          result1.current.setTheme(theme)
        })
        
        // Both hooks should see the same UI state
        expect(result1.current.sidebarOpen).toBe(sidebarOpen)
        expect(result2.current.sidebarOpen).toBe(sidebarOpen)
        expect(result1.current.theme).toBe(theme)
        expect(result2.current.theme).toBe(theme)
        
        // Clean up after this iteration
        resetStoreState()
      }
    ), { numRuns: 50 })
  })

  it('Property 6: State Management Consistency - Multiple operations should maintain consistency', () => {
    fc.assert(fc.property(
      fc.array(stockAnalysisArbitrary, { minLength: 1, maxLength: 3 }).map(analyses => {
        // Ensure unique tickers to avoid deduplication issues
        return analyses.map((analysis, index) => ({
          ...analysis,
          ticker: `TICKER${index}`
        }))
      }),
      (analyses) => {
        // Reset store before this property test iteration
        resetStoreState()
        
        const { result: result1 } = renderHook(() => useAppStore())
        const { result: result2 } = renderHook(() => useAppStore())
        
        // Add multiple analyses through different hooks
        analyses.forEach((analysis, index) => {
          act(() => {
            if (index % 2 === 0) {
              result1.current.addAnalysis(analysis)
            } else {
              result2.current.addAnalysis(analysis)
            }
          })
        })
        
        // Both hooks should have the same final state
        expect(result1.current.analyses).toHaveLength(analyses.length)
        expect(result2.current.analyses).toHaveLength(analyses.length)
        
        // All analyses should be present (order might differ due to deduplication)
        const result1Tickers = result1.current.analyses.map(a => a.ticker).sort()
        const result2Tickers = result2.current.analyses.map(a => a.ticker).sort()
        const expectedTickers = analyses.map(a => a.ticker).sort()
        
        expect(result1Tickers).toEqual(expectedTickers)
        expect(result2Tickers).toEqual(expectedTickers)
        expect(result1.current.analyses).toEqual(result2.current.analyses)
        
        // Clean up after this iteration
        resetStoreState()
      }
    ), { numRuns: 30 })
  })
})