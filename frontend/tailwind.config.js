/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        /* ── Primary: Deep Saffron ─────────────────── */
        saffron: {
          50:  '#FFF8EC',
          100: '#FDF0D5',
          200: '#FBDFA3',
          300: '#F8C966',
          400: '#F5B030',
          500: '#E6820A',   /* brand primary */
          600: '#C96D06',
          700: '#A55605',
          800: '#7A3F04',
          900: '#522A03',
        },
        /* ── Secondary: Cardamom Green ─────────────── */
        cardamom: {
          50:  '#EAF5ED',
          100: '#D3EBD9',
          200: '#A7D6B3',
          300: '#73BC8A',
          400: '#4E9F68',
          500: '#3A6B4A',   /* brand secondary */
          600: '#2E5439',
          700: '#233F2B',
          800: '#172A1D',
          900: '#0C160F',
        },
        /* ── Accent: Cinnamon Brown ─────────────────── */
        cinnamon: {
          50:  '#F9F0EB',
          100: '#F2DDD2',
          200: '#E5BBA5',
          300: '#D4966E',
          400: '#BF7045',
          500: '#6B3A20',   /* brand accent */
          600: '#55301A',
          700: '#402514',
          800: '#2A180D',
          900: '#150C07',
        },
        /* ── Neutrals: Warm Beige ────────────────────── */
        beige: {
          50:  '#FAFAF7',
          100: '#F5F1E8',
          200: '#EDE6D6',
          300: '#E0D5C0',
          400: '#CEC0A6',
          500: '#B8A485',
        },
      },
      fontFamily: {
        heading: ['Poppins', 'sans-serif'],
        body:    ['Inter', 'sans-serif'],
        data:    ['"Roboto Mono"', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 4px rgba(0,0,0,0.07), 0 4px 16px rgba(0,0,0,0.05)',
        'card-hover': '0 4px 12px rgba(0,0,0,0.10), 0 8px 24px rgba(0,0,0,0.08)',
      },
      borderRadius: {
        xl2: '1rem',
        xl3: '1.5rem',
      },
    },
  },
  plugins: [],
}
