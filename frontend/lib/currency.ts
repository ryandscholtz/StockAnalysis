/**
 * Currency formatting utilities
 */

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: '$',
  EUR: '€',
  GBP: '£',
  JPY: '¥',
  CAD: 'C$',
  AUD: 'A$',
  CHF: 'CHF',
  CNY: '¥',
  HKD: 'HK$',
  SEK: 'kr',
  NZD: 'NZ$',
  SGD: 'S$',
  ZAR: 'R',
  INR: '₹',
  BRL: 'R$',
  MXN: '$',
  KRW: '₩',
}

/**
 * Get currency symbol for a currency code
 */
export function getCurrencySymbol(currencyCode?: string): string {
  if (!currencyCode) return '$'
  return CURRENCY_SYMBOLS[currencyCode.toUpperCase()] || currencyCode
}

/**
 * Format a price with currency symbol
 * Returns "-" if amount is null, undefined, NaN, or not a valid number
 */
export function formatPrice(amount: number | null | undefined, currencyCode?: string): string {
  if (amount === null || amount === undefined || isNaN(amount) || !isFinite(amount)) {
    return '-'
  }
  const symbol = getCurrencySymbol(currencyCode)
  return `${symbol}${amount.toFixed(2)}`
}

/**
 * Format a large number (like market cap) with currency
 * Returns "-" if amount is null, undefined, NaN, or not a valid number
 */
export function formatLargeNumber(amount: number | null | undefined, currencyCode?: string): string {
  if (amount === null || amount === undefined || isNaN(amount) || !isFinite(amount)) {
    return '-'
  }
  const symbol = getCurrencySymbol(currencyCode)
  
  if (amount >= 1_000_000_000_000) {
    return `${symbol}${(amount / 1_000_000_000_000).toFixed(2)}T`
  } else if (amount >= 1_000_000_000) {
    return `${symbol}${(amount / 1_000_000_000).toFixed(2)}B`
  } else if (amount >= 1_000_000) {
    return `${symbol}${(amount / 1_000_000).toFixed(2)}M`
  } else if (amount >= 1_000) {
    return `${symbol}${(amount / 1_000).toFixed(2)}K`
  }
  return formatPrice(amount, currencyCode)
}

/**
 * Format a number with specified decimal places
 * Returns "-" if value is null, undefined, NaN, or not a valid number
 */
export function formatNumber(value: number | null | undefined, decimals: number = 2): string {
  if (value === null || value === undefined || isNaN(value) || !isFinite(value)) {
    return '-'
  }
  return value.toFixed(decimals)
}

/**
 * Format a percentage value
 * Returns "-" if value is null, undefined, NaN, or not a valid number
 */
export function formatPercent(value: number | null | undefined, decimals: number = 1): string {
  if (value === null || value === undefined || isNaN(value) || !isFinite(value)) {
    return '-'
  }
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(decimals)}%`
}

/**
 * Format a ratio (like P/E, P/B)
 * Returns "-" if value is null, undefined, NaN, or not a valid number
 */
export function formatRatio(value: number | null | undefined, decimals: number = 2): string {
  if (value === null || value === undefined || isNaN(value) || !isFinite(value)) {
    return '-'
  }
  return value.toFixed(decimals)
}

