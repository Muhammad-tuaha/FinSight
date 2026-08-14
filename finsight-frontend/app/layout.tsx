import type { Metadata } from 'next'
import './globals.css'
import { StoreProvider } from '@/lib/store'
import { AuthProvider } from '@/lib/auth-context'
import Sidebar from '@/components/ui/Sidebar'
import Footer from '@/components/ui/Footer'

export const metadata: Metadata = {
  title: 'FinSight — PSX Financial Intelligence',
  description: 'AI-powered financial analysis for the Pakistan Stock Exchange',
  icons: {
    icon: '/favicon.png',
    shortcut: '/favicon.png',
    apple: '/favicon.png',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.png" type="image/png" sizes="any" />
      </head>
      <body>
        <AuthProvider>
          <StoreProvider>
            <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg)' }}>
              <Sidebar />
              {/* Main content column — sits beside the sidebar, not full screen */}
              <main className="main-content" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto', minWidth: 0 }}>
                {/* Page content fills at least the full viewport height, pushing footer below the fold */}
                <div className="page-wrapper">
                  {children}
                </div>
                <Footer />
              </main>
            </div>
          </StoreProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
