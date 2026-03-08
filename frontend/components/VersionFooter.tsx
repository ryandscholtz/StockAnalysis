'use client'

import { useEffect, useState } from 'react'

export default function VersionFooter() {
  const [version, setVersion] = useState<string | null>(null)

  useEffect(() => {
    const now = new Date()
    const gmtPlus2Offset = 2 * 60
    const localOffset = now.getTimezoneOffset()
    const gmtPlus2Time = new Date(now.getTime() + (gmtPlus2Offset + localOffset) * 60000)

    const year = gmtPlus2Time.getFullYear().toString().slice(-2)
    const month = String(gmtPlus2Time.getMonth() + 1).padStart(2, '0')
    const day = String(gmtPlus2Time.getDate()).padStart(2, '0')
    const hours = String(gmtPlus2Time.getHours()).padStart(2, '0')
    const minutes = String(gmtPlus2Time.getMinutes()).padStart(2, '0')
    setVersion(`${year}${month}${day}-${hours}:${minutes}`)
  }, [])

  if (!version) return null

  return (
    <footer style={{
      marginTop: 'auto',
      padding: '12px 20px',
      backgroundColor: 'var(--bg-surface-subtle)',
      borderTop: '1px solid var(--border-default)',
      fontSize: '12px',
      color: 'var(--text-muted)',
      textAlign: 'center'
    }}>
      <span>
        Frontend: <span style={{ fontFamily: 'monospace', fontWeight: '500' }}>{version}</span>
      </span>
    </footer>
  )
}
