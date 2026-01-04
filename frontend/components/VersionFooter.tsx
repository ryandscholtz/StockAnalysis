'use client'

import { useEffect, useState } from 'react'

interface VersionInfo {
  backend: string | null
  frontend: string
}

export default function VersionFooter() {
  const [versionInfo, setVersionInfo] = useState<VersionInfo>({
    backend: null,
    frontend: new Date().toLocaleString('en-US', {
      year: '2-digit',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    }).replace(/\//g, '').replace(', ', '-').replace(' ', '-')
  })

  useEffect(() => {
    // Format frontend version in yymmdd-hh:mm format
    const now = new Date()
    const year = now.getFullYear().toString().slice(-2)
    const month = String(now.getMonth() + 1).padStart(2, '0')
    const day = String(now.getDate()).padStart(2, '0')
    const hours = String(now.getHours()).padStart(2, '0')
    const minutes = String(now.getMinutes()).padStart(2, '0')
    const frontendVersion = `${year}${month}${day}-${hours}:${minutes}`
    
    setVersionInfo(prev => ({ ...prev, frontend: frontendVersion }))

    // Fetch backend version
    const fetchBackendVersion = async () => {
      try {
        // Use the same API base URL as the rest of the app
        const apiBaseUrl = typeof window !== 'undefined' 
          ? (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
          : 'http://localhost:8000'
        const response = await fetch(`${apiBaseUrl}/api/version`)
        if (response.ok) {
          const data = await response.json()
          setVersionInfo(prev => ({ ...prev, backend: data.version || data.build_time }))
        }
      } catch (error) {
        console.debug('Could not fetch backend version:', error)
        // Silently fail - backend version is optional
        // But log to console for debugging
        if (process.env.NODE_ENV === 'development') {
          console.log('Backend version fetch failed:', error)
        }
      }
    }

    fetchBackendVersion()
  }, [])

  return (
    <footer style={{
      marginTop: 'auto',
      padding: '12px 20px',
      backgroundColor: '#f9fafb',
      borderTop: '1px solid #e5e7eb',
      fontSize: '12px',
      color: '#6b7280',
      textAlign: 'center'
    }}>
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '16px',
        flexWrap: 'wrap'
      }}>
        {versionInfo.backend && (
          <span>
            Backend: <span style={{ fontFamily: 'monospace', fontWeight: '500' }}>{versionInfo.backend}</span>
          </span>
        )}
        <span>
          Frontend: <span style={{ fontFamily: 'monospace', fontWeight: '500' }}>{versionInfo.frontend}</span>
        </span>
      </div>
    </footer>
  )
}

