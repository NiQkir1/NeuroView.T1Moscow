/**
 * Управление темой приложения
 */

export type Theme = 'dark' | 'light'

const THEME_KEY = 'neuroview_theme'

export const theme = {
  getTheme: (): Theme => {
    if (typeof window === 'undefined') return 'dark'
    const saved = localStorage.getItem(THEME_KEY) as Theme
    return saved || 'dark'
  },

  setTheme: (theme: Theme): void => {
    if (typeof window === 'undefined') return
    localStorage.setItem(THEME_KEY, theme)
    document.documentElement.setAttribute('data-theme', theme)
    applyTheme(theme)
  },

  initTheme: (): void => {
    if (typeof window === 'undefined') return
    const currentTheme = theme.getTheme()
    document.documentElement.setAttribute('data-theme', currentTheme)
    applyTheme(currentTheme)
  },
}

function applyTheme(theme: Theme) {
  if (typeof window === 'undefined') return
  
  const root = document.documentElement
  
  if (theme === 'light') {
    root.classList.add('light-theme')
    root.classList.remove('dark-theme')
  } else {
    root.classList.add('dark-theme')
    root.classList.remove('light-theme')
  }
}







