'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function Home() {
  const router = useRouter()

  useEffect(() => {
    // Redirect to watchlist page
    router.push('/watchlist')
  }, [router])

  return (
    <div className="container">
      <div style={{ textAlign: 'center', padding: '60px 20px' }}>
        <p>Redirecting...</p>
      </div>
    </div>
  )
}

