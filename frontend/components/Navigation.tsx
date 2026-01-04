'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

export default function Navigation() {
  const pathname = usePathname()

  const navItems = [
    { href: '/watchlist', label: 'Watchlist' },
    { href: '/processing-data', label: 'Upload PDF Statement' },
    { href: '/docs', label: 'Docs' },
  ]

  return (
    <nav style={{
      backgroundColor: 'white',
      borderBottom: '1px solid #e5e7eb',
      padding: '16px 0',
      marginBottom: '20px'
    }}>
      <div className="container" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <Link href="/" style={{
          fontSize: '20px',
          fontWeight: '700',
          color: '#111827',
          textDecoration: 'none'
        }}>
          Stock Analysis Tool
        </Link>
        <div style={{
          display: 'flex',
          gap: '8px'
        }}>
          {navItems.map((item) => {
            const isActive = pathname === item.href || (item.href === '/watchlist' && pathname === '/')
            return (
              <Link
                key={item.href}
                href={item.href}
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  textDecoration: 'none',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: isActive ? '#2563eb' : '#6b7280',
                  backgroundColor: isActive ? '#eff6ff' : 'transparent',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = '#f3f4f6'
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'transparent'
                  }
                }}
              >
                {item.label}
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}

