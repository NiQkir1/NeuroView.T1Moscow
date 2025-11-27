/**
 * Константы для spacing согласно стандартам Apple HIG (8px grid system)
 */
export const SPACING = {
  xs: '0.5rem',   // 8px
  sm: '0.75rem',  // 12px
  md: '1rem',     // 16px
  lg: '1.5rem',   // 24px
  xl: '2rem',     // 32px
  '2xl': '3rem',  // 48px
  '3xl': '4rem',  // 64px
} as const

// Tailwind классы для spacing (кратные 8px)
export const SPACING_CLASSES = {
  xs: 'p-2',      // 8px
  sm: 'p-3',      // 12px
  md: 'p-4',      // 16px
  lg: 'p-6',      // 24px
  xl: 'p-8',      // 32px
  '2xl': 'p-12',  // 48px
  '3xl': 'p-16',  // 64px
} as const

export type SpacingKey = keyof typeof SPACING






