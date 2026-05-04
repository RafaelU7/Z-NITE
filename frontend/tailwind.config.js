/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // ── PDV dark-theme palette ──
        pdv: {
          bg:          '#0D1B2A',   // fundo principal do PDV
          surface:     '#112030',   // painéis / cards
          'surface-2': '#162840',   // superfícies elevadas
          border:      '#1E3352',   // borda padrão
          'border-2':  '#243E62',   // borda mais visível
          text:        '#E2E8F0',   // texto principal
          muted:       '#64748B',   // texto secundário/muted
          fiscal:      '#10B981',   // cor dominante modo FISCAL (emerald-500)
          'fiscal-dk': '#059669',   // hover do fiscal (emerald-600)
          gerencial:   '#F59E0B',   // cor dominante modo GERENCIAL (amber-500)
          'gerencial-dk': '#D97706', // hover do gerencial
        },
        // ── Backgrounds (light theme — gerencial/admin) ──
        bg: {
          base: '#F3F6FA',       // página principal — cinza-azulado suave
          surface: '#FFFFFF',    // cards / painéis / modais
          'surface-2': '#F0F4F9', // inputs / seções secundárias
          'surface-3': '#E4EBF4', // hover sutil / kbd chips
        },
        border: {
          DEFAULT: '#D1DBE8',    // borda padrão — mais visível que antes
          strong: '#A8B8CC',     // separadores fortes
        },
        text: {
          primary: '#0F172A',
          secondary: '#475569',
          muted: '#64748B',      // upgrade: era #94A3B8 (baixo contraste)
        },
        // ── Marca ──
        accent: {
          DEFAULT: '#6366F1',
          hover: '#4F46E5',
          subtle: '#EEF2FF',
        },
        // ── Semânticas (ajustadas para legibilidade em fundo claro) ──
        success: {
          DEFAULT: '#22C55E',
          subtle: '#F0FDF4',
          text: '#16A34A',
        },
        warning: {
          DEFAULT: '#F59E0B',
          subtle: '#FFFBEB',
          text: '#D97706',
        },
        danger: {
          DEFAULT: '#EF4444',
          subtle: '#FEF2F2',
          text: '#DC2626',
        },
        // info = azul fiscal
        info: {
          DEFAULT: '#2563EB',
          subtle: '#EFF6FF',
          text: '#1D4ED8',
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
        'pulse-once': 'pulseOnce 1.5s ease-in-out',
      },
      keyframes: {
        flashSuccess: {
          '0%': { backgroundColor: '#22C55E30' },
          '100%': { backgroundColor: 'transparent' },
        },
        flashError: {
          '0%, 50%': { backgroundColor: '#EF444425' },
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
        pulseOnce: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.65' },
        },
      },
    },
  },
  plugins: [],
}
