import type { Metadata } from 'next'
import './globals.css'
import { ThemeProvider } from './components/ThemeProvider'
import { SidebarProvider } from './components/SidebarContext'
import { ErrorBoundaryWrapper } from './components/ErrorBoundaryWrapper'
import { NotificationProvider } from './hooks/useNotifications'
import NotificationContainer from './components/NotificationContainer'

export const metadata: Metadata = {
  title: 'NeuroView - AI Interview Platform',
  description: 'Платформа для проведения технических собеседований с AI-интервьюером',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ru">
      <body>
        <ErrorBoundaryWrapper>
          <ThemeProvider>
            <SidebarProvider>
              <NotificationProvider>
                <NotificationContainer />
                {children}
              </NotificationProvider>
            </SidebarProvider>
          </ThemeProvider>
        </ErrorBoundaryWrapper>
      </body>
    </html>
  )
}

