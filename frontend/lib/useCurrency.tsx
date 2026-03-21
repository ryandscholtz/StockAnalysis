'use client'

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react'
import { stockApi } from './api'

const STORAGE_KEY = 'preferred_currency'
const DEFAULT_CURRENCY = 'USD'

// Sub-unit currencies — normalize to base before fetching FX
const SUB_UNIT_TO_BASE: Record<string, { base: string; factor: number }> = {
  ZAC: { base: 'ZAR', factor: 0.01 },
  GBX: { base: 'GBP', factor: 0.01 },
}

export const COMMON_CURRENCIES = [
  { code: 'USD', label: 'US Dollar' },
  { code: 'EUR', label: 'Euro' },
  { code: 'GBP', label: 'British Pound' },
  { code: 'JPY', label: 'Japanese Yen' },
  { code: 'CAD', label: 'Canadian Dollar' },
  { code: 'AUD', label: 'Australian Dollar' },
  { code: 'CHF', label: 'Swiss Franc' },
  { code: 'SGD', label: 'Singapore Dollar' },
  { code: 'HKD', label: 'Hong Kong Dollar' },
  { code: 'SEK', label: 'Swedish Krona' },
  { code: 'NZD', label: 'New Zealand Dollar' },
  { code: 'ZAR', label: 'South African Rand' },
  { code: 'INR', label: 'Indian Rupee' },
  { code: 'BRL', label: 'Brazilian Real' },
  { code: 'KRW', label: 'Korean Won' },
]

interface CurrencyContextValue {
  preferredCurrency: string
  setPreferredCurrency: (code: string) => void
  /**
   * Synchronous conversion — returns null if the FX rate has not been fetched yet.
   * Subscribe to context re-renders: once the rate is cached, the component will re-render.
   */
  convert: (amount: number | null | undefined, fromCurrency: string, toCurrency?: string) => number | null
  /**
   * Pre-fetch all rates needed to display a list of items. Call this after data loads.
   */
  prefetchRates: (fromCurrencies: string[], toCurrency?: string) => Promise<void>
}

const CurrencyContext = createContext<CurrencyContextValue>({
  preferredCurrency: DEFAULT_CURRENCY,
  setPreferredCurrency: () => {},
  convert: () => null,
  prefetchRates: async () => {},
})

export function CurrencyProvider({ children }: { children: React.ReactNode }) {
  const [preferredCurrency, setPreferredCurrencyState] = useState<string>(DEFAULT_CURRENCY)
  // rateCache: 'JPYUSD' -> 0.00665 (1 JPY = 0.00665 USD)
  const rateCache = useRef<Map<string, number>>(new Map())
  const inFlight = useRef<Set<string>>(new Set())
  // Bump to trigger re-renders when rates arrive
  const [rateVersion, setRateVersion] = useState(0)

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) setPreferredCurrencyState(stored)
    }
  }, [])

  const setPreferredCurrency = useCallback((code: string) => {
    setPreferredCurrencyState(code)
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, code)
    }
  }, [])

  /**
   * Resolve the base currency and scale factor for a given currency code.
   * Sub-units (ZAC, GBX) are normalised to their base currency.
   */
  const normalise = (code: string): { base: string; factor: number } => {
    const upper = (code || 'USD').toUpperCase()
    return SUB_UNIT_TO_BASE[upper] ?? { base: upper, factor: 1 }
  }

  const fetchRate = useCallback(async (fromBase: string, toBase: string): Promise<number> => {
    const key = `${fromBase}${toBase}`
    if (rateCache.current.has(key)) return rateCache.current.get(key)!
    if (inFlight.current.has(key)) {
      // poll until the in-flight request resolves
      await new Promise<void>(resolve => {
        const interval = setInterval(() => {
          if (!inFlight.current.has(key)) { clearInterval(interval); resolve() }
        }, 100)
      })
      return rateCache.current.get(key) ?? 1
    }
    inFlight.current.add(key)
    try {
      const quote = await stockApi.getQuote(`${fromBase}${toBase}=X`)
      const rate = (quote as any).currentPrice || (quote as any).price || 0
      if (rate && rate > 0) {
        rateCache.current.set(key, rate)
        setRateVersion(v => v + 1)
        return rate
      }
    } catch {
      // ignore — fallback to 1
    } finally {
      inFlight.current.delete(key)
    }
    rateCache.current.set(key, 1)
    setRateVersion(v => v + 1)
    return 1
  }, [])

  const convert = useCallback((
    amount: number | null | undefined,
    fromCurrency: string,
    toCurrency?: string,
  ): number | null => {
    if (amount == null || isNaN(amount) || !isFinite(amount)) return null
    const { base: fc, factor: ff } = normalise(fromCurrency)
    const { base: tc, factor: tf } = normalise(toCurrency ?? preferredCurrency)
    if (fc === tc) return amount * ff / tf
    const key = `${fc}${tc}`
    const baseRate = rateCache.current.get(key)
    if (baseRate === undefined) return null  // not cached yet
    return amount * baseRate * ff / tf
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preferredCurrency, rateVersion])  // rateVersion dependency triggers re-render after fetches

  const prefetchRates = useCallback(async (fromCurrencies: string[], toCurrency?: string): Promise<void> => {
    const tc = normalise(toCurrency ?? preferredCurrency).base
    const pairs = [...new Set(
      fromCurrencies
        .map(c => normalise(c).base)
        .filter(fc => fc && fc !== tc)
    )]
    await Promise.all(pairs.map(fc => fetchRate(fc, tc)))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preferredCurrency, fetchRate])

  return (
    <CurrencyContext.Provider value={{ preferredCurrency, setPreferredCurrency, convert, prefetchRates }}>
      {children}
    </CurrencyContext.Provider>
  )
}

export function useCurrency() {
  return useContext(CurrencyContext)
}
