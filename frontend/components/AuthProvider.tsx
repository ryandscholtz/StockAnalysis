'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { authService, AuthState, UserInfo } from '@/lib/auth-mock' // Use mock auth for development

interface AuthContextType extends AuthState {
  signIn: (username: string, password: string) => Promise<UserInfo>
  signUp: (username: string, email: string, password: string, givenName?: string, familyName?: string) => Promise<void>
  signOut: () => void
  confirmSignUp: (username: string, code: string) => Promise<void>
  resendConfirmationCode: (username: string) => Promise<void>
  forgotPassword: (username: string) => Promise<void>
  confirmPassword: (username: string, code: string, newPassword: string) => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    token: null,
    loading: true
  })

  useEffect(() => {
    // Subscribe to auth state changes
    const unsubscribe = authService.onAuthStateChange((newState) => {
      setAuthState(newState)
    })

    // Get initial auth state (this will trigger loadStoredUser on client side)
    setAuthState(authService.getAuthState())

    return unsubscribe
  }, [])

  const contextValue: AuthContextType = {
    ...authState,
    signIn: authService.signIn.bind(authService),
    signUp: authService.signUp.bind(authService),
    signOut: authService.signOut.bind(authService),
    confirmSignUp: authService.confirmSignUp.bind(authService),
    resendConfirmationCode: authService.resendConfirmationCode.bind(authService),
    forgotPassword: authService.forgotPassword.bind(authService),
    confirmPassword: authService.confirmPassword.bind(authService)
  }

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export function RequireAuth({ children, fallback }: { children: React.ReactNode, fallback?: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth()

  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '200px',
        fontSize: '16px',
        color: '#6b7280'
      }}>
        Loading...
      </div>
    )
  }

  if (!isAuthenticated) {
    return fallback || (
      <div style={{
        padding: '24px',
        textAlign: 'center',
        background: '#fef3c7',
        border: '1px solid #f59e0b',
        borderRadius: '8px',
        margin: '24px 0'
      }}>
        <h3 style={{ margin: '0 0 12px 0', color: '#92400e' }}>Authentication Required</h3>
        <p style={{ margin: '0 0 16px 0', color: '#92400e' }}>
          Please sign in to access this feature.
        </p>
        <a 
          href="/auth/signin" 
          style={{
            display: 'inline-block',
            padding: '8px 16px',
            backgroundColor: '#2563eb',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '6px',
            fontSize: '14px',
            fontWeight: '500'
          }}
        >
          Sign In
        </a>
      </div>
    )
  }

  return <>{children}</>
}