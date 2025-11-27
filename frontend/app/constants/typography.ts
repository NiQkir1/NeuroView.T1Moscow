/**
 * Константы для типографики согласно стандартам Apple HIG
 */
export const TYPOGRAPHY = {
  h1: 'text-3xl font-semibold tracking-tight',
  h2: 'text-2xl font-semibold tracking-tight',
  h3: 'text-xl font-semibold tracking-tight',
  h4: 'text-lg font-semibold tracking-tight',
  body: 'text-base leading-relaxed',
  bodySmall: 'text-sm leading-relaxed',
  caption: 'text-xs text-text-tertiary',
  label: 'text-sm font-medium text-text-tertiary tracking-tight',
} as const

export type TypographyKey = keyof typeof TYPOGRAPHY






