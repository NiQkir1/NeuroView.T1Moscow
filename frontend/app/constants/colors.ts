/**
 * Константы цветов для использования в приложении
 * Централизованное управление цветовой схемой
 * Оптимизировано под стандарты Apple HIG
 */

export const COLORS = {
  // Основные цвета (более приглушенные, в стиле Apple)
  primary: '#AF52DE', // Системный фиолетовый Apple
  primaryDark: '#8E44AD',
  primaryLight: '#BF5AF2',
  primaryHover: '#9D4EDD',
  primaryBorder: '#AF52DE',
  primaryBorderOpacity: 'rgba(175, 82, 222, 0.3)',
  primaryShadow: 'rgba(175, 82, 222, 0.2)',
  
  // Системные цвета Apple
  systemBlue: '#007AFF',
  systemGreen: '#34C759',
  systemOrange: '#FF9500',
  systemRed: '#FF3B30',
  
  // Нейтральные тени (вместо цветных)
  shadow: 'rgba(0, 0, 0, 0.1)',
  shadowMedium: 'rgba(0, 0, 0, 0.15)',
  shadowLarge: 'rgba(0, 0, 0, 0.2)',
} as const

export type ColorKey = keyof typeof COLORS

