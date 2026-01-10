'use client'

import SignInForm from '@/components/SignInForm'

export default function SignInPage() {
  return (
    <div className="container" style={{ paddingTop: '60px', paddingBottom: '60px' }}>
      <div style={{ textAlign: 'center', marginBottom: '40px' }}>
        <h1 style={{ fontSize: '32px', marginBottom: '12px' }}>
          Welcome Back
        </h1>
        <p style={{ fontSize: '16px', color: '#6b7280' }}>
          Sign in to access your personalized stock analysis dashboard
        </p>
      </div>
      
      <SignInForm />
      
      <div style={{ 
        textAlign: 'center', 
        marginTop: '40px', 
        padding: '20px',
        backgroundColor: '#f9fafb',
        borderRadius: '8px',
        border: '1px solid #e5e7eb'
      }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '18px', color: '#374151' }}>
          Why Create an Account?
        </h3>
        <ul style={{ 
          textAlign: 'left', 
          maxWidth: '400px', 
          margin: '0 auto',
          padding: 0,
          listStyle: 'none',
          fontSize: '14px',
          color: '#6b7280'
        }}>
          <li style={{ marginBottom: '8px', display: 'flex', alignItems: 'center' }}>
            <span style={{ color: '#10b981', marginRight: '8px' }}>✓</span>
            Save your personal watchlists
          </li>
          <li style={{ marginBottom: '8px', display: 'flex', alignItems: 'center' }}>
            <span style={{ color: '#10b981', marginRight: '8px' }}>✓</span>
            Add custom financial data for analysis
          </li>
          <li style={{ marginBottom: '8px', display: 'flex', alignItems: 'center' }}>
            <span style={{ color: '#10b981', marginRight: '8px' }}>✓</span>
            Track your analysis history
          </li>
          <li style={{ display: 'flex', alignItems: 'center' }}>
            <span style={{ color: '#10b981', marginRight: '8px' }}>✓</span>
            Access advanced features
          </li>
        </ul>
      </div>
    </div>
  )
}