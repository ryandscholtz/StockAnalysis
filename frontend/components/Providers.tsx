'use client'

import React from 'react'
import { ErrorBoundary } from './ErrorBoundary'

interface ProvidersProps {
  children: React.ReactNode
}

export function Providers({ children }: ProvidersProps) {
  return (
    <ErrorBoundary>
      {children}
    </ErrorBoundary>
  )
}