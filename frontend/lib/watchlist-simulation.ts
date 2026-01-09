// Temporary watchlist simulation for client-side functionality
// This provides watchlist functionality while the API is being updated

export interface WatchlistItem {
  ticker: string
  companyName: string
  exchange: string
  addedAt: string
  notes?: string
}

const WATCHLIST_STORAGE_KEY = 'stock-analysis-watchlist'

export class WatchlistSimulation {
  static getWatchlist(): WatchlistItem[] {
    try {
      const stored = localStorage.getItem(WATCHLIST_STORAGE_KEY)
      return stored ? JSON.parse(stored) : []
    } catch (error) {
      console.error('Error reading watchlist from localStorage:', error)
      return []
    }
  }

  static addToWatchlist(ticker: string, companyName: string, exchange: string, notes?: string): boolean {
    try {
      const watchlist = this.getWatchlist()
      
      // Check if already exists
      if (watchlist.some(item => item.ticker.toUpperCase() === ticker.toUpperCase())) {
        return false // Already exists
      }

      const newItem: WatchlistItem = {
        ticker: ticker.toUpperCase(),
        companyName,
        exchange,
        addedAt: new Date().toISOString(),
        notes
      }

      watchlist.push(newItem)
      localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(watchlist))
      return true
    } catch (error) {
      console.error('Error adding to watchlist:', error)
      return false
    }
  }

  static removeFromWatchlist(ticker: string): boolean {
    try {
      const watchlist = this.getWatchlist()
      const filtered = watchlist.filter(item => item.ticker.toUpperCase() !== ticker.toUpperCase())
      
      if (filtered.length === watchlist.length) {
        return false // Item not found
      }

      localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(filtered))
      return true
    } catch (error) {
      console.error('Error removing from watchlist:', error)
      return false
    }
  }

  static isInWatchlist(ticker: string): boolean {
    const watchlist = this.getWatchlist()
    return watchlist.some(item => item.ticker.toUpperCase() === ticker.toUpperCase())
  }

  static updateWatchlistItem(ticker: string, updates: Partial<WatchlistItem>): boolean {
    try {
      const watchlist = this.getWatchlist()
      const index = watchlist.findIndex(item => item.ticker.toUpperCase() === ticker.toUpperCase())
      
      if (index === -1) {
        return false // Item not found
      }

      watchlist[index] = { ...watchlist[index], ...updates }
      localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(watchlist))
      return true
    } catch (error) {
      console.error('Error updating watchlist item:', error)
      return false
    }
  }

  static clearWatchlist(): void {
    localStorage.removeItem(WATCHLIST_STORAGE_KEY)
  }
}