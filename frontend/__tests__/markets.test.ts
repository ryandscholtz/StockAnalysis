import { normalizeTicker, FIDELITY_COUNTRY_TO_YAHOO } from '@/lib/markets'
import { inferCurrencyFromTicker } from '@/lib/currency'
import { searchTickers } from '@/lib/enhanced-search'

describe('Fidelity ticker normalisation', () => {
  it('converts Fidelity ROOT:CC symbols to Yahoo suffixes', () => {
    expect(normalizeTicker('SAP:DE')).toBe('SAP.DE')
    expect(normalizeTicker('npn:za')).toBe('NPN.JO')
    expect(normalizeTicker('7203:JP')).toBe('7203.T')
    expect(normalizeTicker('FPH:NZ')).toBe('FPH.NZ')
    expect(normalizeTicker('ETE:GR')).toBe('ETE.AT')
    expect(normalizeTicker('A5G:IE')).toBe('A5G.IR')
    expect(normalizeTicker('AAPL:US')).toBe('AAPL')
    expect(normalizeTicker('AAPL')).toBe('AAPL')
  })

  it('leaves unknown colon symbols unchanged', () => {
    expect(normalizeTicker('BRK:B')).toBe('BRK:B')
  })

  it('converts hyphen and MarketStack suffixes', () => {
    expect(normalizeTicker('MRF-JO')).toBe('MRF.JO')
    expect(normalizeTicker('BEL.XJSE')).toBe('BEL.JO')
  })

  it('covers every Fidelity country code', () => {
    expect(Object.keys(FIDELITY_COUNTRY_TO_YAHOO).sort()).toEqual([
      'AT', 'AU', 'BE', 'CA', 'CH', 'DE', 'DK', 'ES', 'FI', 'FR',
      'GB', 'GR', 'HK', 'IE', 'IT', 'JP', 'MX', 'NL', 'NO', 'NZ',
      'PL', 'PT', 'SE', 'SG', 'US', 'ZA',
    ])
  })
})

describe('Fidelity currency inference', () => {
  it('infers local currencies from Yahoo suffixes', () => {
    expect(inferCurrencyFromTicker('SAP.DE')).toBe('EUR')
    expect(inferCurrencyFromTicker('ETE.AT')).toBe('EUR')
    expect(inferCurrencyFromTicker('A5G.IR')).toBe('EUR')
    expect(inferCurrencyFromTicker('FPH.NZ')).toBe('NZD')
    expect(inferCurrencyFromTicker('HIVE.V')).toBe('CAD')
    expect(inferCurrencyFromTicker('AMXL.MX')).toBe('MXN')
    expect(inferCurrencyFromTicker('NOVO-B.CO')).toBe('DKK')
    expect(inferCurrencyFromTicker('EQNR.OL')).toBe('NOK')
    expect(inferCurrencyFromTicker('PKO.WA')).toBe('PLN')
    expect(inferCurrencyFromTicker('NPN.JO')).toBe('ZAR')
    expect(inferCurrencyFromTicker('7203.T')).toBe('JPY')
    expect(inferCurrencyFromTicker('SHEL.L')).toBe('GBP')
    expect(inferCurrencyFromTicker('AAPL')).toBeUndefined()
  })

  it('accepts Fidelity colon symbols', () => {
    expect(inferCurrencyFromTicker('SAP:DE')).toBe('EUR')
    expect(inferCurrencyFromTicker('NPN:ZA')).toBe('ZAR')
    expect(inferCurrencyFromTicker('FPH:NZ')).toBe('NZD')
  })
})

describe('Local search covers Fidelity markets', () => {
  it('finds representative international listings', () => {
    expect(searchTickers('SAP.DE')[0]?.ticker).toBe('SAP.DE')
    expect(searchTickers('SAP:DE')[0]?.ticker).toBe('SAP.DE')
    expect(searchTickers('Naspers')[0]?.ticker).toBe('NPN.JO')
    expect(searchTickers('FPH.NZ')[0]?.exchange).toBe('NZX')
    expect(searchTickers('Kerry')[0]?.ticker).toBe('KRZ.IR')
  })
})
