'use client'

import { useState, useEffect } from 'react'
import { theme, Theme } from '@/lib/theme'

export function useTheme() {
  const [currentTheme, setCurrentTheme] = useState<Theme>('dark')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    theme.initTheme()
    setCurrentTheme(theme.getTheme())
  }, [])

  const toggleTheme = (newTheme: Theme) => {
    theme.setTheme(newTheme)
    setCurrentTheme(newTheme)
  }

  const toggle = () => {
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark'
    toggleTheme(newTheme)
  }

  return { theme: currentTheme, toggleTheme, toggle, mounted }
}



