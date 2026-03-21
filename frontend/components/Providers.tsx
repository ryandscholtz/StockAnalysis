'use client'

import React from 'react'
import { ErrorBoundary } from './ErrorBoundary'
import { CurrencyProvider } from '@/lib/useCurrency'

interface ProvidersProps {
  children: React.ReactNode
}

export function Providers({ children }: ProvidersProps) {
  return (
    <ErrorBoundary>
      <CurrencyProvider>
        {children}
      </CurrencyProvider>
    </ErrorBoundary>
  )
}