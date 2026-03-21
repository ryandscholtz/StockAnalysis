/**
 * Currency formatting utilities
 */

/**
 * Infer the likely trading currency from a ticker symbol suffix or exchange name.
 * Returns undefined when the currency cannot be inferred (assume USD).
 */
export function inferCurrencyFromTicker(ticker?: string, exchange?: string): string | undefined {
  // Exchange-level inference (takes priority when present)
  if (exchange) {
    const ex = exchange.toUpperCase()
    if (ex.includes('LSE') || ex.includes('LONDON') || ex === 'LON' || ex === 'L' || ex === 'XLON') return 'GBP'
    if (ex.includes('PARIS') || ex === 'EPA' || ex === 'PAR' || ex === 'XPAR') return 'EUR'
    if (ex.includes('FRANKFURT') || ex.includes('XETRA') || ex === 'ETR' || ex === 'XETR') return 'EUR'
    if (ex.includes('AMSTERDAM') || ex === 'AMS' || ex === 'XAMS') return 'EUR'
    if (ex.includes('BRUSSELS') || ex === 'BRU' || ex === 'XBRU') return 'EUR'
    if (ex.includes('MILAN') || ex === 'MIL' || ex === 'XMIL' || ex === 'BIT') return 'EUR'
    if (ex.includes('MADRID') || ex === 'MAD' || ex === 'XMAD' || ex === 'BME') return 'EUR'
    if (ex.includes('SWISS') || ex === 'SWX' || ex === 'XSWX' || ex === 'VTX') return 'CHF'
    if (ex.includes('AUSTRALIA') || ex.includes('ASX') || ex === 'XASX') return 'AUD'
    if (ex.includes('TORONTO') || ex.includes('TSX') || ex === 'XTSE') return 'CAD'
    if (ex.includes('TOKYO') || ex.includes('TSE') || ex === 'XTKS') return 'JPY'
    if (ex.includes('HONG KONG') || ex.includes('HKEX') || ex === 'XHKG') return 'HKD'
    if (ex.includes('SINGAPORE') || ex === 'SGX' || ex === 'XSES') return 'SGD'
    if (ex.includes('JOHANNESBURG') || ex.includes('JSE') || ex === 'XJSE') return 'ZAR'
    if (ex.includes('KOREA') || ex === 'KRX' || ex === 'XKRX') return 'KRW'
    if (ex.includes('INDIA') || ex.includes('BSE') || ex.includes('NSE') || ex === 'XBOM' || ex === 'XNSE') return 'INR'
  }
  // Ticker suffix inference
  if (!ticker) return undefined
  const t = ticker.toUpperCase()
  if (t.endsWith('.L') || t.endsWith('.LN')) return 'GBP'
  if (t.endsWith('.PA')) return 'EUR'
  if (t.endsWith('.DE') || t.endsWith('.F') || t.endsWith('.MU') || t.endsWith('.BE')) return 'EUR'
  if (t.endsWith('.AS')) return 'EUR'
  if (t.endsWith('.BR')) return 'EUR'
  if (t.endsWith('.MI')) return 'EUR'
  if (t.endsWith('.MC')) return 'EUR'
  if (t.endsWith('.LS')) return 'EUR'
  if (t.endsWith('.SW')) return 'CHF'
  if (t.endsWith('.AX')) return 'AUD'
  if (t.endsWith('.TO') || t.endsWith('.V') || t.endsWith('.CN')) return 'CAD'
  if (t.endsWith('.T')) return 'JPY'
  if (t.endsWith('.HK')) return 'HKD'
  if (t.endsWith('.SI')) return 'SGD'
  if (t.endsWith('.KS') || t.endsWith('.KQ')) return 'KRW'
  if (t.endsWith('.BO') || t.endsWith('.NS')) return 'INR'
  if (t.endsWith('.JK')) return 'IDR'
  if (t.includes('.XJSE') || t.includes('.JSE') || t.includes('.JNB')) return 'ZAR'
  return undefined
}

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
  ZAC: 'R¢',
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

