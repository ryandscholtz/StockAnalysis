'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/AuthProvider'
import { LoadingSpinner } from '@/components/LoadingSpinner'

export default function Home() {
  const router = useRouter()
  const { isAuthenticated, loading } = useAuth()

  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.replace('/watchlist')
    }
  }, [isAuthenticated, loading, router])

  if (loading || isAuthenticated) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '400px' }}>
        <LoadingSpinner text="Loading..." />
      </div>
    )
  }

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '0 20px' }}>

      {/* Hero */}
      <div style={{ textAlign: 'center', padding: '72px 20px 56px' }}>
        <div style={{
          display: 'inline-block',
          padding: '5px 16px',
          backgroundColor: 'var(--color-primary-bg)',
          color: 'var(--color-primary)',
          borderRadius: '20px',
          fontSize: '13px',
          fontWeight: '600',
          marginBottom: '28px',
          border: '1px solid var(--color-primary)',
          letterSpacing: '0.02em',
        }}>
          Value Investing Made Simple
        </div>

        <h1 style={{
          fontSize: '52px',
          fontWeight: '800',
          color: 'var(--text-primary)',
          lineHeight: '1.1',
          marginBottom: '24px',
          letterSpacing: '-0.02em',
        }}>
          Analyse stocks with<br />
          <span style={{ color: 'var(--color-primary)' }}>confidence</span>
        </h1>

        <p style={{
          fontSize: '19px',
          color: 'var(--text-muted)',
          maxWidth: '540px',
          margin: '0 auto 40px',
          lineHeight: '1.65',
        }}>
          Build your personal watchlist, calculate fair values, and identify
          undervalued stocks using time-tested value investing principles.
        </p>

        <div style={{ display: 'flex', gap: '14px', justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link
            href="/auth/signup"
            style={{
              padding: '14px 32px',
              backgroundColor: 'var(--color-primary)',
              color: 'white',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: '600',
              textDecoration: 'none',
              display: 'inline-block',
            }}
          >
            Get Started Free
          </Link>
          <Link
            href="/auth/signin"
            style={{
              padding: '14px 32px',
              backgroundColor: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: '600',
              textDecoration: 'none',
              display: 'inline-block',
              border: '1px solid var(--border-input)',
            }}
          >
            Sign In
          </Link>
        </div>
      </div>

      {/* Feature cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '20px',
        padding: '8px 0 60px',
      }}>
        {[
          {
            icon: '📊',
            title: 'Personal Watchlist',
            description:
              'Track your favourite stocks in one place. Add, remove, and monitor any stock at a glance.',
          },
          {
            icon: '⚖️',
            title: 'Fair Value Analysis',
            description:
              'Calculate intrinsic value using proven valuation models and know exactly when a stock is undervalued.',
          },
          {
            icon: '💡',
            title: 'Smart Recommendations',
            description:
              'Get clear Strong Buy, Buy, Hold, or Avoid signals grounded in margin of safety and financial health.',
          },
          {
            icon: '📈',
            title: 'Bulk Analysis',
            description:
              'Analyse your entire watchlist in one click and instantly surface the best opportunities.',
          },
          {
            icon: '🏦',
            title: 'Financial Health Scores',
            description:
              'Assess business quality, earnings stability, and balance sheet strength all in one score.',
          },
          {
            icon: '🌍',
            title: 'Multi-Exchange Support',
            description:
              'Analyse stocks across major global exchanges with automatic currency handling.',
          },
        ].map((feature) => (
          <div
            key={feature.title}
            style={{
              padding: '28px',
              backgroundColor: 'var(--bg-surface)',
              borderRadius: '12px',
              border: '1px solid var(--border-default)',
              boxShadow: '0 2px 4px rgba(0,0,0,0.06)',
            }}
          >
            <div style={{ fontSize: '30px', marginBottom: '14px' }}>{feature.icon}</div>
            <h3 style={{
              fontSize: '17px',
              fontWeight: '700',
              color: 'var(--text-primary)',
              marginBottom: '10px',
            }}>
              {feature.title}
            </h3>
            <p style={{ fontSize: '14px', color: 'var(--text-muted)', lineHeight: '1.65' }}>
              {feature.description}
            </p>
          </div>
        ))}
      </div>

      {/* Bottom CTA */}
      <div style={{
        textAlign: 'center',
        padding: '56px 20px',
        backgroundColor: 'var(--color-primary-bg)',
        borderRadius: '16px',
        marginBottom: '60px',
        border: '1px solid var(--border-default)',
      }}>
        <h2 style={{
          fontSize: '30px',
          fontWeight: '700',
          color: 'var(--text-primary)',
          marginBottom: '12px',
        }}>
          Ready to invest smarter?
        </h2>
        <p style={{ fontSize: '16px', color: 'var(--text-muted)', marginBottom: '32px' }}>
          Create a free account and start building your watchlist today.
        </p>
        <Link
          href="/auth/signup"
          style={{
            padding: '14px 40px',
            backgroundColor: 'var(--color-primary)',
            color: 'white',
            borderRadius: '8px',
            fontSize: '16px',
            fontWeight: '600',
            textDecoration: 'none',
            display: 'inline-block',
          }}
        >
          Create Free Account
        </Link>
      </div>

    </div>
  )
}
