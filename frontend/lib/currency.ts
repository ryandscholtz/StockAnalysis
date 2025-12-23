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
 */
export function formatPrice(amount: number, currencyCode?: string): string {
  const symbol = getCurrencySymbol(currencyCode)
  return `${symbol}${amount.toFixed(2)}`
}

/**
 * Format a large number (like market cap) with currency
 */
export function formatLargeNumber(amount: number, currencyCode?: string): string {
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

