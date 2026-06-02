import type { Metadata } from 'next'
import './globals.css'
import { StoreProvider } from '@/lib/store'
import Sidebar from '@/components/ui/Sidebar'

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
            <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              {children}
            </main>
          </div>
        </StoreProvider>
      </body>
    </html>
  )
}
