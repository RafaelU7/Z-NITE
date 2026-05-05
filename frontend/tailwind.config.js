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
        // ── Backgrounds (dark theme — sistema inteiro) ──
        bg: {
          base:        '#07151d',   // fundo mais profundo das páginas
          surface:     '#0D2530',   // cards / painéis / modais
          'surface-2': '#112B38',   // inputs / seções secundárias / linhas de tabela
          'surface-3': '#193548',   // hover sutil / kbd chips / borda mais elevada
        },
        border: {
          DEFAULT: '#193548',   // borda padrão teal-petróleo
          strong:  '#1D4260',   // separadores mais marcados
        },
        text: {
          primary:   '#F3F7FA',   // off-white — texto principal
          secondary: '#A8C0CC',   // cinza-teal claro — texto secundário
          muted:     '#6B8899',   // cinza-teal escuro — labels/hints
        },
        // ── Marca — TEAL (substitui indigo) ──
        accent: {
          DEFAULT: '#19C7B5',   // teal — ação principal
          hover:   '#14A89A',   // hover teal
          subtle:  '#0a1f26',   // fundo teal muito escuro
        },
        // ── Semânticas dark-native ──
        success: {
          DEFAULT: '#32C85B',   // verde fiscal premium
          subtle:  '#071a10',   // fundo verde muito escuro
          text:    '#4DD470',   // verde legível em fundo escuro
        },
        warning: {
          DEFAULT: '#D4A62A',   // âmbar gerencial premium
          subtle:  '#1a1305',   // fundo âmbar muito escuro
          text:    '#F0C842',   // âmbar legível em fundo escuro
        },
        danger: {
          DEFAULT: '#EF5350',   // vermelho para erros/risco
          subtle:  '#1c0606',   // fundo vermelho muito escuro
          text:    '#F87171',   // vermelho legível em fundo escuro
        },
        // info = azul operacional
        info: {
          DEFAULT: '#2C7BE5',   // azul médio
          subtle:  '#061528',   // fundo azul muito escuro
          text:    '#60A5FA',   // azul legível em fundo escuro
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
