'use client'

import { useState } from 'react'
import { useAuth } from './AuthProvider'
import { useRouter } from 'next/navigation'

const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  border: '1px solid var(--border-input)',
  borderRadius: '6px',
  fontSize: '14px',
  boxSizing: 'border-box' as const,
  backgroundColor: 'var(--bg-surface)',
  color: 'var(--text-primary)'
}

const labelStyle = {
  display: 'block',
  marginBottom: '6px',
  fontSize: '14px',
  fontWeight: '500' as const,
  color: 'var(--text-secondary)'
}

export default function SignUpForm() {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    givenName: '',
    familyName: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  
  const { signUp } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      setLoading(false)
      return
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long')
      setLoading(false)
      return
    }

    try {
      await signUp(
        formData.username,
        formData.email,
        formData.password,
        formData.givenName || undefined,
        formData.familyName || undefined
      )
      
      setSuccess(true)
      setTimeout(() => {
        router.push(`/auth/confirm?username=${encodeURIComponent(formData.username)}`)
      }, 2000)
      
    } catch (err: any) {
      setError(err.message || 'Sign up failed')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
  }

  if (success) {
    return (
      <div className="card" style={{ maxWidth: '400px', margin: '0 auto', textAlign: 'center' }}>
        <div style={{
          padding: '24px',
          backgroundColor: 'var(--status-success-bg)',
          border: '1px solid #86efac',
          borderRadius: '8px',
          marginBottom: '16px'
        }}>
          <h2 style={{ color: 'var(--status-success-text)', marginBottom: '12px' }}>Account Created!</h2>
          <p style={{ color: 'var(--status-success-text)', margin: 0 }}>
            Please check your email for a verification code to complete your registration.
          </p>
        </div>
        <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
          Redirecting to confirmation page...
        </p>
      </div>
    )
  }

  return (
    <div className="card" style={{ maxWidth: '400px', margin: '0 auto' }}>
      <h2 style={{ textAlign: 'center', marginBottom: '24px' }}>Create Account</h2>
      
      {error && (
        <div style={{
          padding: '12px',
          backgroundColor: 'var(--status-error-bg)',
          border: '1px solid #fecaca',
          borderRadius: '6px',
          marginBottom: '16px',
          color: 'var(--status-error-text)',
          fontSize: '14px'
        }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
          <div>
            <label style={labelStyle}>First Name</label>
            <input
              type="text"
              name="givenName"
              value={formData.givenName}
              onChange={handleChange}
              style={inputStyle}
              placeholder="First name"
            />
          </div>
          
          <div>
            <label style={labelStyle}>Last Name</label>
            <input
              type="text"
              name="familyName"
              value={formData.familyName}
              onChange={handleChange}
              style={inputStyle}
              placeholder="Last name"
            />
          </div>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>Username *</label>
          <input
            type="text"
            name="username"
            value={formData.username}
            onChange={handleChange}
            required
            style={inputStyle}
            placeholder="Choose a username"
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>Email Address *</label>
          <input
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
            style={inputStyle}
            placeholder="Enter your email"
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>Password *</label>
          <input
            type="password"
            name="password"
            value={formData.password}
            onChange={handleChange}
            required
            style={inputStyle}
            placeholder="Create a password (min 8 characters)"
          />
        </div>

        <div style={{ marginBottom: '24px' }}>
          <label style={labelStyle}>Confirm Password *</label>
          <input
            type="password"
            name="confirmPassword"
            value={formData.confirmPassword}
            onChange={handleChange}
            required
            style={inputStyle}
            placeholder="Confirm your password"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          style={{
            width: '100%',
            padding: '12px',
            backgroundColor: loading ? '#9ca3af' : 'var(--color-primary)',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            fontSize: '16px',
            fontWeight: '500',
            cursor: loading ? 'not-allowed' : 'pointer',
            marginBottom: '16px'
          }}
        >
          {loading ? 'Creating Account...' : 'Create Account'}
        </button>
      </form>

      <div style={{ textAlign: 'center', fontSize: '14px', color: 'var(--text-muted)' }}>
        <p>
          Already have an account?{' '}
          <a 
            href="/auth/signin" 
            style={{ color: 'var(--color-primary)', textDecoration: 'none' }}
          >
            Sign in
          </a>
        </p>
      </div>
    </div>
  )
}
