import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="container">
      <div style={{
        textAlign: 'center',
        padding: '60px 20px',
        maxWidth: '600px',
        margin: '0 auto'
      }}>
        <h2 style={{ fontSize: '32px', marginBottom: '16px', color: '#111827' }}>
          404 - Page Not Found
        </h2>
        <p style={{ fontSize: '16px', color: '#6b7280', marginBottom: '24px' }}>
          The page you're looking for doesn't exist.
        </p>
        <Link
          href="/"
          style={{
            display: 'inline-block',
            background: '#2563eb',
            color: 'white',
            textDecoration: 'none',
            borderRadius: '6px',
            padding: '10px 20px',
            fontSize: '14px',
            fontWeight: '500'
          }}
        >
          Go to Home
        </Link>
      </div>
    </div>
  )
}

