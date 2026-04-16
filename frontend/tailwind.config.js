/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          base: '#0d0f1a',
          surface: '#131625',
          'surface-2': '#1c1f35',
          'surface-3': '#252841',
        },
        border: {
          DEFAULT: '#2d3158',
          strong: '#404580',
        },
        text: {
          primary: '#f0f2ff',
          secondary: '#8b8faf',
          muted: '#4a4f72',
        },
        accent: {
          DEFAULT: '#6366f1',
          hover: '#818cf8',
          subtle: '#6366f115',
        },
        success: {
          DEFAULT: '#10b981',
          subtle: '#10b98115',
          text: '#34d399',
        },
        warning: {
          DEFAULT: '#f59e0b',
          subtle: '#f59e0b15',
          text: '#fbbf24',
        },
        danger: {
          DEFAULT: '#ef4444',
          subtle: '#ef444415',
          text: '#f87171',
        },
        info: {
          DEFAULT: '#3b82f6',
          subtle: '#3b82f615',
          text: '#60a5fa',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        'pdv-xl': ['2rem', { lineHeight: '2.5rem', fontWeight: '700' }],
        'pdv-lg': ['1.5rem', { lineHeight: '2rem', fontWeight: '600' }],
      },
      animation: {
        'flash-success': 'flashSuccess 0.4s ease-out',
        'flash-error': 'flashError 0.4s ease-out',
        'slide-in': 'slideIn 0.2s ease-out',
        'fade-in': 'fadeIn 0.15s ease-out',
      },
      keyframes: {
        flashSuccess: {
          '0%': { backgroundColor: '#10b98130' },
          '100%': { backgroundColor: 'transparent' },
        },
        flashError: {
          '0%, 50%': { backgroundColor: '#ef444425' },
          '100%': { backgroundColor: 'transparent' },
        },
        slideIn: {
          '0%': { transform: 'translateY(-8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
