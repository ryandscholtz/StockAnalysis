// Enhanced search functionality with local ticker database
// This provides a better search experience while the API has limited tickers

export interface TickerInfo {
  ticker: string
  companyName: string
  exchange: string
  sector?: string
  aliases?: string[] // Common names and keywords for the company
}

// Comprehensive list of popular tickers
export const POPULAR_TICKERS: TickerInfo[] = [
  // Technology
  { ticker: 'AAPL', companyName: 'Apple Inc.', exchange: 'NASDAQ', sector: 'Technology', aliases: ['apple'] },
  { ticker: 'MSFT', companyName: 'Microsoft Corporation', exchange: 'NASDAQ', sector: 'Technology', aliases: ['microsoft'] },
  { ticker: 'GOOGL', companyName: 'Alphabet Inc. Class A', exchange: 'NASDAQ', sector: 'Technology', aliases: ['google', 'alphabet'] },
  { ticker: 'GOOG', companyName: 'Alphabet Inc. Class C', exchange: 'NASDAQ', sector: 'Technology', aliases: ['google', 'alphabet'] },
  { ticker: 'AMZN', companyName: 'Amazon.com Inc.', exchange: 'NASDAQ', sector: 'Technology', aliases: ['amazon'] },
  { ticker: 'TSLA', companyName: 'Tesla Inc.', exchange: 'NASDAQ', sector: 'Technology', aliases: ['tesla'] },
  { ticker: 'META', companyName: 'Meta Platforms Inc.', exchange: 'NASDAQ', sector: 'Technology', aliases: ['meta', 'facebook', 'fb'] },
  { ticker: 'NVDA', companyName: 'NVIDIA Corporation', exchange: 'NASDAQ', sector: 'Technology', aliases: ['nvidia'] },
  { ticker: 'NFLX', companyName: 'Netflix Inc.', exchange: 'NASDAQ', sector: 'Technology', aliases: ['netflix'] },
  { ticker: 'CRM', companyName: 'Salesforce Inc.', exchange: 'NYSE', sector: 'Technology', aliases: ['salesforce'] },
  { ticker: 'ORCL', companyName: 'Oracle Corporation', exchange: 'NYSE', sector: 'Technology', aliases: ['oracle'] },
  { ticker: 'ADBE', companyName: 'Adobe Inc.', exchange: 'NASDAQ', sector: 'Technology', aliases: ['adobe'] },
  { ticker: 'INTC', companyName: 'Intel Corporation', exchange: 'NASDAQ', sector: 'Technology', aliases: ['intel'] },
  { ticker: 'AMD', companyName: 'Advanced Micro Devices Inc.', exchange: 'NASDAQ', sector: 'Technology', aliases: ['amd'] },
  { ticker: 'PYPL', companyName: 'PayPal Holdings Inc.', exchange: 'NASDAQ', sector: 'Technology', aliases: ['paypal'] },
  { ticker: 'UBER', companyName: 'Uber Technologies Inc.', exchange: 'NYSE', sector: 'Technology', aliases: ['uber'] },
  { ticker: 'LYFT', companyName: 'Lyft Inc.', exchange: 'NASDAQ', sector: 'Technology', aliases: ['lyft'] },
  { ticker: 'SNAP', companyName: 'Snap Inc.', exchange: 'NYSE', sector: 'Technology', aliases: ['snap', 'snapchat'] },
  { ticker: 'TWTR', companyName: 'Twitter Inc.', exchange: 'NYSE', sector: 'Technology', aliases: ['twitter'] },
  { ticker: 'SPOT', companyName: 'Spotify Technology S.A.', exchange: 'NYSE', sector: 'Technology', aliases: ['spotify'] },

  // Financial
  { ticker: 'JPM', companyName: 'JPMorgan Chase & Co.', exchange: 'NYSE', sector: 'Financial' },
  { ticker: 'BAC', companyName: 'Bank of America Corporation', exchange: 'NYSE', sector: 'Financial' },
  { ticker: 'WFC', companyName: 'Wells Fargo & Company', exchange: 'NYSE', sector: 'Financial' },
  { ticker: 'GS', companyName: 'The Goldman Sachs Group Inc.', exchange: 'NYSE', sector: 'Financial' },
  { ticker: 'MS', companyName: 'Morgan Stanley', exchange: 'NYSE', sector: 'Financial' },
  { ticker: 'V', companyName: 'Visa Inc.', exchange: 'NYSE', sector: 'Financial' },
  { ticker: 'MA', companyName: 'Mastercard Incorporated', exchange: 'NYSE', sector: 'Financial' },
  { ticker: 'BRK.B', companyName: 'Berkshire Hathaway Inc. Class B', exchange: 'NYSE', sector: 'Financial' },
  { ticker: 'AXP', companyName: 'American Express Company', exchange: 'NYSE', sector: 'Financial' },
  { ticker: 'C', companyName: 'Citigroup Inc.', exchange: 'NYSE', sector: 'Financial' },

  // Healthcare
  { ticker: 'JNJ', companyName: 'Johnson & Johnson', exchange: 'NYSE', sector: 'Healthcare' },
  { ticker: 'PFE', companyName: 'Pfizer Inc.', exchange: 'NYSE', sector: 'Healthcare' },
  { ticker: 'UNH', companyName: 'UnitedHealth Group Incorporated', exchange: 'NYSE', sector: 'Healthcare' },
  { ticker: 'ABBV', companyName: 'AbbVie Inc.', exchange: 'NYSE', sector: 'Healthcare' },
  { ticker: 'MRK', companyName: 'Merck & Co. Inc.', exchange: 'NYSE', sector: 'Healthcare' },
  { ticker: 'TMO', companyName: 'Thermo Fisher Scientific Inc.', exchange: 'NYSE', sector: 'Healthcare' },
  { ticker: 'ABT', companyName: 'Abbott Laboratories', exchange: 'NYSE', sector: 'Healthcare' },
  { ticker: 'LLY', companyName: 'Eli Lilly and Company', exchange: 'NYSE', sector: 'Healthcare' },
  { ticker: 'BMY', companyName: 'Bristol-Myers Squibb Company', exchange: 'NYSE', sector: 'Healthcare' },
  { ticker: 'AMGN', companyName: 'Amgen Inc.', exchange: 'NASDAQ', sector: 'Healthcare' },

  // Consumer
  { ticker: 'KO', companyName: 'The Coca-Cola Company', exchange: 'NYSE', sector: 'Consumer', aliases: ['coke', 'coca cola', 'coca-cola'] },
  { ticker: 'PEP', companyName: 'PepsiCo Inc.', exchange: 'NASDAQ', sector: 'Consumer', aliases: ['pepsi'] },
  { ticker: 'WMT', companyName: 'Walmart Inc.', exchange: 'NYSE', sector: 'Consumer', aliases: ['walmart'] },
  { ticker: 'HD', companyName: 'The Home Depot Inc.', exchange: 'NYSE', sector: 'Consumer', aliases: ['home depot'] },
  { ticker: 'MCD', companyName: 'McDonald\'s Corporation', exchange: 'NYSE', sector: 'Consumer', aliases: ['mcdonalds', 'mcdonald'] },
  { ticker: 'NKE', companyName: 'NIKE Inc.', exchange: 'NYSE', sector: 'Consumer', aliases: ['nike'] },
  { ticker: 'SBUX', companyName: 'Starbucks Corporation', exchange: 'NASDAQ', sector: 'Consumer', aliases: ['starbucks'] },
  { ticker: 'TGT', companyName: 'Target Corporation', exchange: 'NYSE', sector: 'Consumer', aliases: ['target'] },
  { ticker: 'LOW', companyName: 'Lowe\'s Companies Inc.', exchange: 'NYSE', sector: 'Consumer', aliases: ['lowes', 'lowe'] },
  { ticker: 'COST', companyName: 'Costco Wholesale Corporation', exchange: 'NASDAQ', sector: 'Consumer', aliases: ['costco'] },

  // Industrial
  { ticker: 'BA', companyName: 'The Boeing Company', exchange: 'NYSE', sector: 'Industrial' },
  { ticker: 'CAT', companyName: 'Caterpillar Inc.', exchange: 'NYSE', sector: 'Industrial' },
  { ticker: 'GE', companyName: 'General Electric Company', exchange: 'NYSE', sector: 'Industrial' },
  { ticker: 'MMM', companyName: '3M Company', exchange: 'NYSE', sector: 'Industrial' },
  { ticker: 'HON', companyName: 'Honeywell International Inc.', exchange: 'NASDAQ', sector: 'Industrial' },
  { ticker: 'UPS', companyName: 'United Parcel Service Inc.', exchange: 'NYSE', sector: 'Industrial' },
  { ticker: 'FDX', companyName: 'FedEx Corporation', exchange: 'NYSE', sector: 'Industrial' },

  // Energy
  { ticker: 'XOM', companyName: 'Exxon Mobil Corporation', exchange: 'NYSE', sector: 'Energy' },
  { ticker: 'CVX', companyName: 'Chevron Corporation', exchange: 'NYSE', sector: 'Energy' },
  { ticker: 'COP', companyName: 'ConocoPhillips', exchange: 'NYSE', sector: 'Energy' },
  { ticker: 'EOG', companyName: 'EOG Resources Inc.', exchange: 'NYSE', sector: 'Energy' },

  // Telecom
  { ticker: 'VZ', companyName: 'Verizon Communications Inc.', exchange: 'NYSE', sector: 'Telecom' },
  { ticker: 'T', companyName: 'AT&T Inc.', exchange: 'NYSE', sector: 'Telecom' },
  { ticker: 'TMUS', companyName: 'T-Mobile US Inc.', exchange: 'NASDAQ', sector: 'Telecom' },

  // Real Estate & REITs
  { ticker: 'AMT', companyName: 'American Tower Corporation', exchange: 'NYSE', sector: 'Real Estate' },
  { ticker: 'PLD', companyName: 'Prologis Inc.', exchange: 'NYSE', sector: 'Real Estate' },
  { ticker: 'CCI', companyName: 'Crown Castle International Corp.', exchange: 'NYSE', sector: 'Real Estate' },

  // Utilities
  { ticker: 'NEE', companyName: 'NextEra Energy Inc.', exchange: 'NYSE', sector: 'Utilities' },
  { ticker: 'DUK', companyName: 'Duke Energy Corporation', exchange: 'NYSE', sector: 'Utilities' },
  { ticker: 'SO', companyName: 'The Southern Company', exchange: 'NYSE', sector: 'Utilities' },
]

export function testEnhancedSearch(): string {
  return `Enhanced search module loaded successfully. Available tickers: ${POPULAR_TICKERS.length}`
}

export function searchTickers(query: string, limit: number = 10): TickerInfo[] {
  if (!query || query.trim().length === 0) {
    return []
  }

  const queryUpper = query.toUpperCase().trim()
  const results: TickerInfo[] = []

  // First, find exact ticker matches
  const exactMatches = POPULAR_TICKERS.filter(ticker => 
    ticker.ticker.toUpperCase() === queryUpper
  )
  results.push(...exactMatches)

  // Then, find ticker starts with matches
  if (results.length < limit) {
    const startsWithMatches = POPULAR_TICKERS.filter(ticker => 
      ticker.ticker.toUpperCase().startsWith(queryUpper) && 
      !results.some(r => r.ticker === ticker.ticker)
    )
    results.push(...startsWithMatches.slice(0, limit - results.length))
  }

  // Then, find ticker contains matches
  if (results.length < limit) {
    const containsMatches = POPULAR_TICKERS.filter(ticker => 
      ticker.ticker.toUpperCase().includes(queryUpper) && 
      !results.some(r => r.ticker === ticker.ticker)
    )
    results.push(...containsMatches.slice(0, limit - results.length))
  }

  // Then, find company name matches
  if (results.length < limit) {
    const companyMatches = POPULAR_TICKERS.filter(ticker => 
      ticker.companyName.toUpperCase().includes(queryUpper) && 
      !results.some(r => r.ticker === ticker.ticker)
    )
    results.push(...companyMatches.slice(0, limit - results.length))
  }

  // Finally, find alias matches
  if (results.length < limit) {
    const aliasMatches = POPULAR_TICKERS.filter(ticker => 
      ticker.aliases && 
      ticker.aliases.some(alias => alias.toUpperCase().includes(queryUpper)) &&
      !results.some(r => r.ticker === ticker.ticker)
    )
    results.push(...aliasMatches.slice(0, limit - results.length))
  }

  return results.slice(0, limit)
}

export function getTickerInfo(ticker: string): TickerInfo | null {
  return POPULAR_TICKERS.find(t => t.ticker.toUpperCase() === ticker.toUpperCase()) || null
}