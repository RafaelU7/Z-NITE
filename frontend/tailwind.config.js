/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // ── PDV dark-theme palette — teal-petróleo ──
        pdv: {
          bg:            '#0A1E26',   // teal-petróleo — fundo principal
          surface:       '#0D2530',   // painéis / cards
          'surface-2':   '#112B38',   // superfícies elevadas
          border:        '#193548',   // borda padrão
          'border-2':    '#1D4260',   // borda mais visível
          text:          '#F3F7FA',   // texto principal
          muted:         '#8FA3B2',   // texto secundário/muted
          fiscal:        '#32C85B',   // verde lime premium — modo FISCAL
          'fiscal-dk':   '#28A44C',   // hover verde fiscal
          teal:          '#19C7B5',   // teal accent
          gerencial:     '#D4A62A',   // âmbar premium — modo GERENCIAL
          'gerencial-dk': '#A97A14',  // hover âmbar gerencial
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
