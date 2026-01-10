'use client'

import SignUpForm from '@/components/SignUpForm'

export default function SignUpPage() {
  return (
    <div className="container" style={{ paddingTop: '60px', paddingBottom: '60px' }}>
      <div style={{ textAlign: 'center', marginBottom: '40px' }}>
        <h1 style={{ fontSize: '32px', marginBottom: '12px' }}>
          Join Stock Analysis
        </h1>
        <p style={{ fontSize: '16px', color: '#6b7280' }}>
          Create your free account to start building personalized watchlists and analysis
        </p>
      </div>
      
      <SignUpForm />
      
      <div style={{ 
        textAlign: 'center', 
        marginTop: '40px', 
        padding: '20px',
        backgroundColor: '#f0fdf4',
        borderRadius: '8px',
        border: '1px solid #86efac'
      }}>
        <h3 style={{ margin: '0 0 12px 0', fontSize: '18px', color: '#166534' }}>
          🎉 Free Account Includes
        </h3>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: '16px',
          marginTop: '16px'
        }}>
          <div>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '16px', color: '#166534' }}>
              📊 Personal Watchlists
            </h4>
            <p style={{ margin: 0, fontSize: '14px', color: '#15803d' }}>
              Track up to 50 stocks with personalized notes and alerts
            </p>
          </div>
          <div>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '16px', color: '#166534' }}>
              📈 Manual Data Entry
            </h4>
            <p style={{ margin: 0, fontSize: '14px', color: '#15803d' }}>
              Add custom financial data for accurate valuations
            </p>
          </div>
          <div>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '16px', color: '#166534' }}>
              🔍 100 Analyses/Month
            </h4>
            <p style={{ margin: 0, fontSize: '14px', color: '#15803d' }}>
              Comprehensive stock analysis with fair value calculations
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}