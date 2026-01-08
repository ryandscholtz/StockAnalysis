'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  const router = useRouter()

  useEffect(() => {
    // Log error for debugging
    console.error('Application error:', error)
  }, [error])

  return (
    <div className="container">
      <div style={{
        textAlign: 'center',
        padding: '60px 20px',
        maxWidth: '600px',
        margin: '0 auto'
      }}>
        <h2 style={{ fontSize: '24px', marginBottom: '16px', color: '#dc2626' }}>
          Something went wrong!
        </h2>
        <p style={{ fontSize: '16px', color: '#6b7280', marginBottom: '24px' }}>
          {error.message || 'An unexpected error occurred'}
        </p>
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
          <button
            onClick={reset}
            style={{
              background: '#2563eb',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              padding: '10px 20px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500'
            }}
          >
            Try again
          </button>
          <button
            onClick={() => router.push('/')}
            style={{
              background: '#6b7280',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              padding: '10px 20px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500'
            }}
          >
            Go home
          </button>
        </div>
        {error.digest && (
          <p style={{
            marginTop: '24px',
            fontSize: '12px',
            color: '#9ca3af',
            fontFamily: 'monospace'
          }}>
            Error ID: {error.digest}
          </p>
        )}
      </div>
    </div>
  )
}

