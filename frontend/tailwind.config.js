/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        /* ── Primary: Forest Green ──────────────────── */
        forest: {
          50:  '#E8F5E9',
          100: '#C8E6C9',
          200: '#A5D6A7',
          300: '#81C784',
          400: '#66BB6A',
          500: '#4CAF50',   /* brand secondary */
          600: '#388E3C',
          700: '#2E7D32',   /* brand primary */
          800: '#1B5E20',   /* deep green */
          900: '#0D3B0F',
        },
        /* ── Primary container / Surface greens ─────── */
        agri: {
          50:  '#F4F8F3',   /* background */
          100: '#E6F0E2',
          200: '#DCE8D8',   /* borders */
          300: '#B8D0B2',
          400: '#8FB887',
          500: '#6BA15F',
        },
        /* ── Neutrals ────────────────────────────────── */
        surface: '#FFFFFF',
        'text-primary':  '#1E293B',
        'text-secondary':'#64748B',
      },
      fontFamily: {
        heading: ['Poppins', 'sans-serif'],
        body:    ['Inter', 'sans-serif'],
        data:    ['"Roboto Mono"', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.04)',
        'card-hover': '0 4px 12px rgba(0,0,0,0.08), 0 8px 24px rgba(0,0,0,0.06)',
        'green-glow': '0 0 0 3px rgba(46,125,50,0.2)',
      },
      borderRadius: {
        xl2: '1rem',
        xl3: '1.5rem',
      },
    },
  },
  plugins: [],
}
