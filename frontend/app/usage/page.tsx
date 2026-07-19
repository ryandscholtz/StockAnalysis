'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/AuthProvider'
import { stockApi, BedrockUsageResponse, BedrockUsageCounter } from '@/lib/api'

function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value || 0)
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value || 0)
}

function formatDate(value?: string | null): string {
  if (!value) return '—'
  const date = new Date(value)
  if (isNaN(date.getTime())) return '—'
  return date.toLocaleString()
}

function CounterCard({ title, subtitle, counter }: { title: string; subtitle: string; counter: BedrockUsageCounter }) {
  return (
    <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: '12px', padding: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.08)' }}>
      <div style={{ fontSize: '12px', fontWeight: '700', letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '6px' }}>{title}</div>
      <div style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '18px' }}>{subtitle}</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '12px' }}>
        <div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Requests</div>
          <div style={{ fontSize: '26px', fontWeight: '700', color: 'var(--text-primary)' }}>{formatNumber(counter.request_count)}</div>
        </div>
        <div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Input Tokens</div>
          <div style={{ fontSize: '26px', fontWeight: '700', color: 'var(--text-primary)' }}>{formatNumber(counter.input_tokens)}</div>
        </div>
        <div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Output Tokens</div>
          <div style={{ fontSize: '26px', fontWeight: '700', color: 'var(--text-primary)' }}>{formatNumber(counter.output_tokens)}</div>
        </div>
        <div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Total Tokens</div>
          <div style={{ fontSize: '26px', fontWeight: '700', color: 'var(--text-primary)' }}>{formatNumber(counter.total_tokens)}</div>
        </div>
        <div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Estimated Cost</div>
          <div style={{ fontSize: '26px', fontWeight: '700', color: '#0f766e' }}>{formatUsd(counter.estimated_cost_usd)}</div>
        </div>
      </div>
      <div style={{ marginTop: '18px', paddingTop: '14px', borderTop: '1px solid var(--border-default)', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px', fontSize: '13px' }}>
        <div><strong>Last Model:</strong> {counter.last_model_id || '—'}</div>
        <div><strong>Last Operation:</strong> {counter.last_operation || '—'}</div>
        <div><strong>Usage Source:</strong> {counter.last_usage_source || '—'}</div>
        <div><strong>Created:</strong> {formatDate(counter.created_at)}</div>
        <div><strong>Updated:</strong> {formatDate(counter.updated_at)}</div>
        <div><strong>Reset At:</strong> {formatDate(counter.reset_at)}</div>
      </div>
    </div>
  )
}

export default function UsagePage() {
  const router = useRouter()
  const { isAuthenticated, loading: authLoading } = useAuth()
  const [usage, setUsage] = useState<BedrockUsageResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [resetting, setResetting] = useState(false)

  const loadUsage = async () => {
    try {
      setLoading(true)
      setError('')
      const response = await stockApi.getBedrockUsage()
      setUsage(response)
    } catch (err: any) {
      setError(err?.message || 'Failed to load usage.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.replace('/')
    }
  }, [authLoading, isAuthenticated, router])

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      loadUsage()
    }
  }, [authLoading, isAuthenticated])

  if (authLoading || (!isAuthenticated && !authLoading)) {
    return <div className="container" style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>Loading…</div>
  }

  return (
    <div className="container" style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ fontSize: '32px', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '6px' }}>Bedrock Usage</h1>
          <p style={{ fontSize: '15px', color: 'var(--text-muted)' }}>
            Near-real-time Bedrock token usage and estimated cost tracking for your account.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            onClick={loadUsage}
            disabled={loading}
            style={{ padding: '8px 16px', backgroundColor: 'var(--color-primary)', color: '#fff', border: 'none', borderRadius: '6px', cursor: loading ? 'not-allowed' : 'pointer', fontWeight: '600' }}
          >
            Refresh
          </button>
          <button
            onClick={async () => {
              setResetting(true)
              setError('')
              try {
                await stockApi.resetBedrockUsageInstance()
                await loadUsage()
              } catch (err: any) {
                setError(err?.message || 'Failed to reset instance usage.')
              } finally {
                setResetting(false)
              }
            }}
            disabled={resetting}
            style={{ padding: '8px 16px', backgroundColor: resetting ? '#9ca3af' : '#f59e0b', color: '#fff', border: 'none', borderRadius: '6px', cursor: resetting ? 'not-allowed' : 'pointer', fontWeight: '600' }}
          >
            {resetting ? 'Resetting…' : 'Reset Instance Counter'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', backgroundColor: 'var(--status-error-bg)', border: '1px solid #ef4444', borderRadius: '6px', color: 'var(--status-error-text)', marginBottom: '20px' }}>
          ⚠️ {error}
        </div>
      )}

      {loading && !usage ? (
        <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px 0' }}>Loading usage…</div>
      ) : usage ? (
        <div style={{ display: 'grid', gap: '16px' }}>
          <CounterCard title="Lifetime Total" subtitle="Never resets automatically. Tracks all Bedrock usage attributed to your account." counter={usage.total} />
          <CounterCard title="Instance Counter" subtitle="Accumulates until you manually reset it from this page." counter={usage.instance} />
        </div>
      ) : null}
    </div>
  )
}