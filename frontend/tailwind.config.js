/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          50: '#1a1a1a',
          100: '#1f1f1f',
          200: '#2a2a2a',
          300: '#333333',
          400: '#3a3a3a',
          500: '#4a4a4a',
        },
        purple: {
          apple: '#AF52DE', // Системный фиолетовый Apple
          light: '#BF5AF2',
          dark: '#8E44AD',
        },
        neon: {
          green: '#00ff00',
          cyan: '#00ffff',
          pink: '#ff00ff',
          purple: '#AF52DE', // Обновлено на системный цвет
          blue: '#0080ff',
        },
        bg: {
          primary: 'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
          tertiary: 'var(--bg-tertiary)',
          quaternary: 'var(--bg-quaternary)',
          hover: 'var(--bg-hover)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          tertiary: 'var(--text-tertiary)',
          muted: 'var(--text-muted)',
        },
        border: {
          color: 'var(--border-color)',
          hover: 'var(--border-hover)',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'SF Pro Display', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      letterSpacing: {
        tighter: '-0.02em',
        tight: '-0.01em',
        normal: '0',
        wide: '0.01em',
        wider: '0.02em',
      },
    },
  },
  plugins: [],
}

