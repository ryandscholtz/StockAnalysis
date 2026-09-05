/**
 * Fidelity International Trading symbology and Yahoo Finance suffixes.
 * Fidelity quotes foreign stocks as ROOT:CC (e.g. SAP:DE, NPN:ZA).
 * https://www.fidelity.com/stock-trading/faqs-international
 */

export const FIDELITY_COUNTRY_TO_YAHOO: Record<string, string> = {
  AU: '.AX',
  AT: '.VI',
  BE: '.BR',
  CA: '.TO',
  DK: '.CO',
  FI: '.HE',
  FR: '.PA',
  DE: '.DE',
  GR: '.AT',
  HK: '.HK',
  IE: '.IR',
  IT: '.MI',
  JP: '.T',
  MX: '.MX',
  NL: '.AS',
  NZ: '.NZ',
  NO: '.OL',
  PL: '.WA',
  PT: '.LS',
  SG: '.SI',
  ZA: '.JO',
  ES: '.MC',
  SE: '.ST',
  CH: '.SW',
  GB: '.L',
  US: '',
}

const YAHOO_SUFFIXES = [
  '.XJSE', '.JO', '.IR', '.AT', '.NZ', '.AX', '.HK', '.TO', '.MX',
  '.PA', '.DE', '.AS', '.BR', '.MI', '.MC', '.LS', '.SW', '.ST',
  '.CO', '.OL', '.HE', '.WA', '.VI', '.SI', '.L', '.V', '.T',
]

/**
 * Convert a user-entered symbol (Yahoo, Fidelity ROOT:CC, or hyphen suffix)
 * into Yahoo Finance form used by the rest of the app.
 */
export function normalizeTicker(ticker?: string): string {
  if (!ticker) return ''
  const raw = ticker.trim().toUpperCase()
  if (!raw) return ''

  if (raw.includes(':')) {
    const [root, cc] = raw.split(':').map((s) => s.trim())
    if (root && cc && cc in FIDELITY_COUNTRY_TO_YAHOO) {
      return root + FIDELITY_COUNTRY_TO_YAHOO[cc]
    }
    return raw
  }

  for (const suffix of YAHOO_SUFFIXES) {
    const token = suffix.replace(/^\./, '')
    if (raw.endsWith(`-${token}`) && raw.length > token.length + 1) {
      return raw.slice(0, -(token.length + 1)) + '.' + token
    }
  }

  if (raw.endsWith('.XJSE')) {
    return raw.slice(0, -5) + '.JO'
  }
  return raw
}
