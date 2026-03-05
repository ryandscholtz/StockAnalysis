'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAuth } from './AuthProvider'
import { useState, useEffect } from 'react'

const MOBILE_BREAKPOINT = 640

export default function Navigation() {
  const pathname = usePathname()
  const { isAuthenticated, user, signOut } = useAuth()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(typeof window !== 'undefined' && window.innerWidth < MOBILE_BREAKPOINT)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  useEffect(() => {
    setMenuOpen(false)
  }, [pathname])

  const navItems = [
    { href: '/explore', label: 'Explore', requireAuth: false },
    { href: '/watchlist', label: 'Watchlist', requireAuth: true },
    { href: '/docs', label: 'Docs', requireAuth: false },
  ]

  const handleSignOut = () => {
    signOut()
    setShowUserMenu(false)
  }

  return (
    <nav style={{
      position: 'relative',
      backgroundColor: 'var(--bg-surface)',
      borderBottom: '1px solid var(--border-default)',
      padding: '16px 0',
      marginBottom: '20px'
    }}>
      <div className="container" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <Link
          href="/"
          style={{
            fontSize: '20px',
            fontWeight: '700',
            color: 'var(--text-primary)',
            textDecoration: 'none'
          }}
          onClick={() => setMenuOpen(false)}
        >
          Stock Analysis Tool
        </Link>

        {/* Hamburger button - mobile only */}
        {isMobile && (
          <button
            type="button"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            onClick={() => setMenuOpen((o) => !o)}
            style={{
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              gap: '5px',
              width: '40px',
              height: '40px',
              padding: '8px',
              background: 'var(--bg-surface-subtle)',
              border: '1px solid var(--border-default)',
              borderRadius: '8px',
              cursor: 'pointer'
            }}
          >
            <span style={{
              display: 'block',
              width: '20px',
              height: '2px',
              borderRadius: '1px',
              background: 'var(--text-secondary)',
              transform: menuOpen ? 'rotate(45deg) translate(5px, 5px)' : 'none',
              transition: 'all 0.2s'
            }} />
            <span style={{
              display: 'block',
              width: '20px',
              height: '2px',
              borderRadius: '1px',
              background: 'var(--text-secondary)',
              opacity: menuOpen ? 0 : 1,
              transition: 'opacity 0.2s'
            }} />
            <span style={{
              display: 'block',
              width: '20px',
              height: '2px',
              borderRadius: '1px',
              background: 'var(--text-secondary)',
              transform: menuOpen ? 'rotate(-45deg) translate(5px, -5px)' : 'none',
              transition: 'all 0.2s'
            }} />
          </button>
        )}

        {/* Desktop nav */}
        {!isMobile && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          {/* Navigation Items */}
          {navItems.map((item) => {
            // Hide auth-required items if not authenticated
            if (item.requireAuth && !isAuthenticated) {
              return null
            }
            
            const isActive = pathname === item.href
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
                  color: isActive ? 'var(--color-primary)' : 'var(--text-muted)',
                  backgroundColor: isActive ? 'var(--color-primary-bg)' : 'transparent',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'var(--bg-hover)'
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

          {/* Authentication Section */}
          {isAuthenticated ? (
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 12px',
                  backgroundColor: 'var(--bg-hover)',
                  border: '1px solid var(--border-input)',
                  borderRadius: '6px',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer'
                }}
              >
                <div style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontSize: '12px',
                  fontWeight: '600'
                }}>
                  {user?.username?.charAt(0).toUpperCase() || 'U'}
                </div>
                <span>{user?.username || 'User'}</span>
                <span style={{ fontSize: '12px' }}>▼</span>
              </button>

              {showUserMenu && (
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  right: 0,
                  marginTop: '4px',
                  backgroundColor: 'var(--bg-surface)',
                  border: '1px solid var(--border-input)',
                  borderRadius: '6px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
                  minWidth: '200px',
                  zIndex: 50
                }}>
                  <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-default)' }}>
                    <div style={{ fontSize: '14px', fontWeight: '500', color: 'var(--text-primary)' }}>
                      {user?.givenName && user?.familyName 
                        ? `${user.givenName} ${user.familyName}`
                        : user?.username
                      }
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      {user?.email}
                    </div>
                    <div style={{ 
                      fontSize: '10px', 
                      color: '#10b981',
                      backgroundColor: '#f0fdf4',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      display: 'inline-block',
                      marginTop: '4px',
                      textTransform: 'uppercase',
                      fontWeight: '600'
                    }}>
                      {user?.subscriptionTier || 'Free'}
                    </div>
                  </div>
                  
                  <div style={{ padding: '8px 0' }}>
                    <Link
                      href="/profile"
                      style={{
                        display: 'block',
                        padding: '8px 16px',
                        fontSize: '14px',
                        color: 'var(--text-secondary)',
                        textDecoration: 'none'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'var(--bg-hover)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent'
                      }}
                      onClick={() => setShowUserMenu(false)}
                    >
                      Profile Settings
                    </Link>
                    
                    <button
                      onClick={handleSignOut}
                      style={{
                        display: 'block',
                        width: '100%',
                        padding: '8px 16px',
                        fontSize: '14px',
                        color: '#dc2626',
                        backgroundColor: 'transparent',
                        border: 'none',
                        textAlign: 'left',
                        cursor: 'pointer'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'var(--status-error-bg)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent'
                      }}
                    >
                      Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', gap: '8px' }}>
              <Link
                href="/auth/signin"
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  textDecoration: 'none',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: 'var(--text-muted)',
                  backgroundColor: 'transparent',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--bg-hover)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent'
                }}
              >
                Sign In
              </Link>
              <Link
                href="/auth/signup"
                style={{
                  padding: '8px 16px',
                  borderRadius: '6px',
                  textDecoration: 'none',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: 'white',
                  backgroundColor: 'var(--color-primary)',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--color-primary-hover)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--color-primary)'
                }}
              >
                Sign Up
              </Link>
            </div>
          )}
        </div>
        )}
      </div>

      {/* Mobile menu panel - full width below nav */}
      {isMobile && menuOpen && (
        <div
          className="nav-mobile-menu"
          role="dialog"
          aria-label="Mobile menu"
          onClick={(e) => { if (e.target === e.currentTarget) setMenuOpen(false) }}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 60,
            paddingTop: '60px',
            backgroundColor: 'rgba(0,0,0,0.4)',
            overflowY: 'auto'
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              backgroundColor: 'var(--bg-surface)',
              borderBottom: '1px solid var(--border-default)',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
              padding: '12px 0',
              minHeight: '120px'
            }}
          >
          {navItems.map((item) => {
            if (item.requireAuth && !isAuthenticated) return null
            const isActive = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setMenuOpen(false)}
                style={{
                  display: 'block',
                  padding: '12px 16px',
                  fontSize: '15px',
                  fontWeight: '500',
                  color: isActive ? 'var(--color-primary)' : 'var(--text-secondary)',
                  backgroundColor: isActive ? 'var(--color-primary-bg)' : 'transparent',
                  textDecoration: 'none',
                  borderLeft: '3px solid transparent'
                }}
              >
                {item.label}
              </Link>
            )
          })}
          {isAuthenticated ? (
            <>
              <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border-default)', marginTop: '8px' }}>
                <div style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                  {user?.email}
                </div>
                <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-primary)' }}>
                  {user?.givenName && user?.familyName ? `${user.givenName} ${user.familyName}` : user?.username}
                </div>
              </div>
              <Link
                href="/profile"
                onClick={() => setMenuOpen(false)}
                style={{
                  display: 'block',
                  padding: '12px 16px',
                  fontSize: '15px',
                  color: 'var(--text-secondary)',
                  textDecoration: 'none'
                }}
              >
                Profile Settings
              </Link>
              <button
                type="button"
                onClick={() => { handleSignOut(); setMenuOpen(false) }}
                style={{
                  display: 'block',
                  width: '100%',
                  padding: '12px 16px',
                  fontSize: '15px',
                  color: '#dc2626',
                  background: 'none',
                  border: 'none',
                  textAlign: 'left',
                  cursor: 'pointer'
                }}
              >
                Sign Out
              </button>
            </>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '12px 16px', borderTop: '1px solid var(--border-default)', marginTop: '8px' }}>
              <Link
                href="/auth/signin"
                onClick={() => setMenuOpen(false)}
                style={{
                  padding: '12px 16px',
                  borderRadius: '6px',
                  textAlign: 'center' as const,
                  fontSize: '15px',
                  fontWeight: '500',
                  color: 'var(--text-secondary)',
                  backgroundColor: 'var(--bg-hover)',
                  textDecoration: 'none'
                }}
              >
                Sign In
              </Link>
              <Link
                href="/auth/signup"
                onClick={() => setMenuOpen(false)}
                style={{
                  padding: '12px 16px',
                  borderRadius: '6px',
                  textAlign: 'center' as const,
                  fontSize: '15px',
                  fontWeight: '500',
                  color: 'white',
                  backgroundColor: 'var(--color-primary)',
                  textDecoration: 'none'
                }}
              >
                Sign Up
              </Link>
            </div>
          )}
          </div>
        </div>
      )}

      {/* Click outside to close user menu / mobile menu */}
      {(showUserMenu || (isMobile && menuOpen)) && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 40
          }}
          onClick={() => {
            setShowUserMenu(false)
            setMenuOpen(false)
          }}
        />
      )}
    </nav>
  )
}
