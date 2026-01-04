import './globals.css'
import type { Metadata } from 'next'
import Navigation from '@/components/Navigation'
import DeveloperFeedback from '@/components/DeveloperFeedback'
import VersionFooter from '@/components/VersionFooter'

export const metadata: Metadata = {
  title: 'Stock Analysis Tool',
  description: 'Analyze stocks using value investing principles',
  icons: {
    icon: '/favicon.svg',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Navigation />
        <main style={{ flex: 1 }}>
          {children}
        </main>
        <VersionFooter />
        <DeveloperFeedback enabled={true} />
      </body>
    </html>
  )
}

