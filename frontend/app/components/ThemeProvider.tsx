'use client'

import { useEffect } from 'react'
import { theme } from '@/lib/theme'

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    theme.initTheme()
  }, [])

  return <>{children}</>
}







