import './globals.css'
import type { Metadata } from 'next'
import Navigation from '@/components/Navigation'
import VersionFooter from '@/components/VersionFooter'
import { Providers } from '@/components/Providers'
import { AuthProvider } from '@/components/AuthProvider'

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
      <body className="flex flex-col min-h-screen bg-gray-50 text-gray-900">
        <AuthProvider>
          <Providers>
            <Navigation />
            <main className="flex-1 container mx-auto px-0 sm:px-4 py-4 sm:py-6 bg-white sm:bg-transparent">
              {children}
            </main>
            <VersionFooter />
          </Providers>
        </AuthProvider>
      </body>
    </html>
  )
}

