import type { Metadata } from 'next'
import './globals.css'
import { StoreProvider } from '@/lib/store'
import Sidebar from '@/components/ui/Sidebar'
import Footer from '@/components/ui/Footer'

export const metadata: Metadata = {
  title: 'FinSight — PSX Financial Intelligence',
  description: 'AI-powered financial analysis for the Pakistan Stock Exchange',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <StoreProvider>
          <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg)' }}>
            <Sidebar />
            {/* Main content column — sits beside the sidebar, not full screen */}
            <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto', minWidth: 0 }}>
              {/* Page content fills at least the full viewport height, pushing footer below the fold */}
              <div style={{ flex: 1 }}>
                {children}
              </div>
              <Footer />
            </main>
          </div>
        </StoreProvider>
      </body>
    </html>
  )
}
