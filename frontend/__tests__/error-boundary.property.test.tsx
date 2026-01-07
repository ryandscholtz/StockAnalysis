/**
 * Property-based tests for error boundary handling
 * Feature: tech-stack-modernization, Property 6: Error Boundary Handling
 */

import React from 'react'
import { render, screen, cleanup } from '@testing-library/react'
import * as fc from 'fast-check'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { LoadingState } from '@/components/LoadingSpinner'

// Component that throws an error for testing
interface ErrorThrowingComponentProps {
  shouldThrow: boolean
  errorMessage: string
}

function ErrorThrowingComponent({ shouldThrow, errorMessage }: ErrorThrowingComponentProps) {
  if (shouldThrow) {
    throw new Error(errorMessage)
  }
  return <div data-testid="success-content">Success content</div>
}

// Component that simulates loading states
interface LoadingTestComponentProps {
  loading: boolean
  error: string | null
  content: string
}

function LoadingTestComponent({ loading, error, content }: LoadingTestComponentProps) {
  return (
    <LoadingState loading={loading} error={error}>
      <div data-testid="loaded-content">{content}</div>
    </LoadingState>
  )
}

describe('Error Boundary Handling Properties', () => {
  beforeEach(() => {
    cleanup()
  })

  afterEach(() => {
    cleanup()
  })

  it('Property: Error boundaries should catch errors and show error UI', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 1, maxLength: 100 }),
      (errorMessage) => {
        // Clean up before each iteration
        cleanup()
        
        // Test that error boundary catches errors
        const { container } = render(
          <ErrorBoundary>
            <ErrorThrowingComponent shouldThrow={true} errorMessage={errorMessage} />
          </ErrorBoundary>
        )
        
        // Should show error UI instead of crashing
        expect(screen.getAllByText('Something went wrong')[0]).toBeInTheDocument()
        expect(screen.getAllByText(/An unexpected error occurred/)[0]).toBeInTheDocument()
        expect(screen.getAllByRole('button', { name: /refresh page/i })[0]).toBeInTheDocument()
        expect(screen.getAllByRole('button', { name: /try again/i })[0]).toBeInTheDocument()
        
        // Should not show the original content
        expect(screen.queryByTestId('success-content')).not.toBeInTheDocument()
        
        // Clean up after iteration
        cleanup()
      }
    ), { numRuns: 20 })
  })

  it('Property: Error boundaries should not interfere with successful renders', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 1, maxLength: 100 }).filter(s => s.trim().length > 0),
      (content) => {
        // Clean up before each iteration
        cleanup()
        
        // Test that error boundary doesn't interfere when no error occurs
        render(
          <ErrorBoundary>
            <div data-testid="success-content">{content}</div>
          </ErrorBoundary>
        )
        
        // Should show the original content
        expect(screen.getAllByTestId('success-content')[0]).toBeInTheDocument()
        expect(screen.getAllByText(content)[0]).toBeInTheDocument()
        
        // Should not show error UI
        expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument()
        
        // Clean up after iteration
        cleanup()
      }
    ), { numRuns: 20 })
  })

  it('Property: Loading states should be properly displayed', () => {
    fc.assert(fc.property(
      fc.boolean(),
      fc.oneof(fc.constant(null), fc.string({ minLength: 1, maxLength: 100 })),
      fc.string({ minLength: 1, maxLength: 100 }).filter(s => s.trim().length > 0),
      (loading, error, content) => {
        // Clean up before each iteration
        cleanup()
        
        render(
          <LoadingTestComponent 
            loading={loading} 
            error={error} 
            content={content} 
          />
        )
        
        if (loading) {
          // Should show loading spinner
          expect(screen.getAllByRole('status')[0]).toBeInTheDocument()
          expect(screen.getAllByText('Loading...')[0]).toBeInTheDocument()
          
          // Should not show content or error
          expect(screen.queryByTestId('loaded-content')).not.toBeInTheDocument()
          expect(screen.queryByText('Error')).not.toBeInTheDocument()
        } else if (error) {
          // Should show error state
          expect(screen.getAllByText('Error')[0]).toBeInTheDocument()
          expect(screen.getAllByText(error)[0]).toBeInTheDocument()
          
          // Should not show loading or content
          expect(screen.queryByRole('status')).not.toBeInTheDocument()
          expect(screen.queryByTestId('loaded-content')).not.toBeInTheDocument()
        } else {
          // Should show content
          expect(screen.getAllByTestId('loaded-content')[0]).toBeInTheDocument()
          expect(screen.getAllByText(content)[0]).toBeInTheDocument()
          
          // Should not show loading or error
          expect(screen.queryByRole('status')).not.toBeInTheDocument()
          expect(screen.queryByText('Error')).not.toBeInTheDocument()
        }
        
        // Clean up after iteration
        cleanup()
      }
    ), { numRuns: 30 })
  })

  it('Property: Error boundary with custom fallback should use provided fallback', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 1, maxLength: 100 }),
      fc.string({ minLength: 1, maxLength: 100 }).filter(s => s.trim().length > 0),
      (errorMessage, fallbackText) => {
        // Clean up before each iteration
        cleanup()
        
        const customFallback = <div data-testid="custom-fallback">{fallbackText}</div>
        
        render(
          <ErrorBoundary fallback={customFallback}>
            <ErrorThrowingComponent shouldThrow={true} errorMessage={errorMessage} />
          </ErrorBoundary>
        )
        
        // Should show custom fallback
        expect(screen.getAllByTestId('custom-fallback')[0]).toBeInTheDocument()
        expect(screen.getAllByText(fallbackText)[0]).toBeInTheDocument()
        
        // Should not show default error UI
        expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument()
        expect(screen.queryByTestId('success-content')).not.toBeInTheDocument()
        
        // Clean up after iteration
        cleanup()
      }
    ), { numRuns: 20 })
  })

  it('Property: Error boundary should call onError callback when provided', () => {
    fc.assert(fc.property(
      fc.string({ minLength: 1, maxLength: 100 }),
      (errorMessage) => {
        // Clean up before each iteration
        cleanup()
        
        const onErrorMock = jest.fn()
        
        render(
          <ErrorBoundary onError={onErrorMock}>
            <ErrorThrowingComponent shouldThrow={true} errorMessage={errorMessage} />
          </ErrorBoundary>
        )
        
        // Should call onError callback
        expect(onErrorMock).toHaveBeenCalledTimes(1)
        expect(onErrorMock).toHaveBeenCalledWith(
          expect.any(Error),
          expect.objectContaining({
            componentStack: expect.any(String)
          })
        )
        
        // The error passed should have the correct message
        const [error] = onErrorMock.mock.calls[0]
        expect(error.message).toBe(errorMessage)
        
        // Clean up after iteration
        cleanup()
      }
    ), { numRuns: 20 })
  })

  it('Property: Loading state transitions should be consistent', () => {
    fc.assert(fc.property(
      fc.array(
        fc.record({
          loading: fc.boolean(),
          error: fc.oneof(fc.constant(null), fc.string({ minLength: 1, maxLength: 50 })),
          content: fc.string({ minLength: 1, maxLength: 50 }).filter(s => s.trim().length > 0)
        }),
        { minLength: 1, maxLength: 3 }
      ),
      (states) => {
        // Clean up before each iteration
        cleanup()
        
        const { rerender } = render(
          <LoadingTestComponent {...states[0]} />
        )
        
        // Test each state transition
        states.forEach((state, index) => {
          rerender(<LoadingTestComponent {...state} />)
          
          // Verify the current state is displayed correctly
          if (state.loading) {
            expect(screen.getAllByRole('status')[0]).toBeInTheDocument()
          } else if (state.error) {
            expect(screen.getAllByText('Error')[0]).toBeInTheDocument()
            expect(screen.getAllByText(state.error)[0]).toBeInTheDocument()
          } else {
            expect(screen.getAllByTestId('loaded-content')[0]).toBeInTheDocument()
            expect(screen.getAllByText(state.content)[0]).toBeInTheDocument()
          }
        })
        
        // Clean up after iteration
        cleanup()
      }
    ), { numRuns: 15 })
  })
})