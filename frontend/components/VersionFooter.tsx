'use client'

import { useEffect, useState } from 'react'

interface VersionInfo {
  backend: string | null
  frontend: string | null
}

export default function VersionFooter() {
  const [versionInfo, setVersionInfo] = useState<VersionInfo>({
    backend: null,
    frontend: null
  })
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    // Generate frontend version only on client side to avoid hydration mismatch
    const generateFrontendVersion = () => {
      // Create date in GMT+2 timezone
      const now = new Date()
      const gmtPlus2Offset = 2 * 60 // GMT+2 in minutes
      const localOffset = now.getTimezoneOffset() // Local timezone offset in minutes
      const gmtPlus2Time = new Date(now.getTime() + (gmtPlus2Offset + localOffset) * 60000)
      
      const year = gmtPlus2Time.getFullYear().toString().slice(-2)
      const month = String(gmtPlus2Time.getMonth() + 1).padStart(2, '0')
      const day = String(gmtPlus2Time.getDate()).padStart(2, '0')
      const hours = String(gmtPlus2Time.getHours()).padStart(2, '0')
      const minutes = String(gmtPlus2Time.getMinutes()).padStart(2, '0')
      return `${year}${month}${day}-${hours}:${minutes}`
    }

    setMounted(true)
    setVersionInfo(prev => ({ ...prev, frontend: generateFrontendVersion() }))

    // Fetch backend version
    const fetchBackendVersion = async () => {
      try {
        // Use the production API URL
        const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://dx0w31lbc1.execute-api.eu-west-1.amazonaws.com/production'
        console.log('Fetching backend version from:', apiBaseUrl)
        const response = await fetch(`${apiBaseUrl}/api/version`)
        if (response.ok) {
          const data = await response.json()
          console.log('Backend version data:', data)
          setVersionInfo(prev => ({ ...prev, backend: data.version || data.build_time }))
        } else {
          console.log('Backend version fetch failed:', response.status, response.statusText)
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

  // Don't render anything until mounted to avoid hydration mismatch
  if (!mounted) {
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
          <span>Loading versions...</span>
        </div>
      </footer>
    )
  }

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
        {versionInfo.frontend && (
          <span>
            Frontend: <span style={{ fontFamily: 'monospace', fontWeight: '500' }}>{versionInfo.frontend}</span>
          </span>
        )}
      </div>
    </footer>
  )
}