'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { LoadingSpinner } from '@/components/LoadingSpinner'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    // Redirect to watchlist page
    router.push('/watchlist')
  }, [router])

  return (
    <div className="flex items-center justify-center min-h-96">
      <LoadingSpinner text="Redirecting to watchlist..." />
    </div>
  )
}

