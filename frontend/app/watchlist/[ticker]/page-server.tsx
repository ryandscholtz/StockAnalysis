// Server component wrapper for static export
import WatchlistDetailClient from './page-client'

export async function generateStaticParams() {
  // Return empty array to allow client-side routing for all tickers
  return []
}

export default function WatchlistDetailPage() {
  return <WatchlistDetailClient />
}