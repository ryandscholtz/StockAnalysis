'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function NotFound() {
  const router = useRouter()

  useEffect(() => {
    // Handle client-side routing for dynamic routes
    const path = window.location.pathname
    
    // If it's a watchlist ticker route, redirect to the ticker page
    if (path.startsWith('/watchlist/') && path.split('/').length === 3) {
      const ticker = path.split('/')[2]
      if (ticker && ticker.length > 0) {
        // This will be handled by the client-side routing
        return
      }
    }
  }, [router])

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center', 
      minHeight: '60vh',
      textAlign: 'center',
      padding: '40px 20px'
    }}>
      <h1 style={{ fontSize: '96px', fontWeight: '800', color: '#e5e7eb', marginBottom: '20px' }}>
        404
      </h1>
      <h2 style={{ fontSize: '24px', color: '#6b7280', marginBottom: '12px' }}>
        Page Not Found
      </h2>
      <p style={{ color: '#9ca3af', marginBottom: '30px' }}>
        The page you're looking for doesn't exist.
      </p>
      <a 
        href="/" 
        style={{
          display: 'inline-block',
          padding: '12px 24px',
          background: '#2563eb',
          color: 'white',
          textDecoration: 'none',
          borderRadius: '6px',
          fontWeight: '600'
        }}
      >
        🏠 Go Home
      </a>
    </div>
  )
}