/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Editorial Study Desk Palette
        canvas: '#FAF8F5',       // warm cream
        paper: {
          DEFAULT: '#FFFFFF',    // clean card white
          canvas: '#FAF8F5',     // warm paper canvas
          surface: '#F5F2EB',    // slightly tinted paper surface
          hairline: '#EAE6DF',   // thin paper borders
          'hairline-strong': '#D6D0C5',
          card: '#FFFFFF',
          deep: '#F3EFE8',
          muted: '#EFECE6',
        },
        surface: {
          DEFAULT: '#FAF8F5',
          card: '#FFFFFF',
          hairline: '#EAE6DF',   // thin paper borders
          deep: '#F3EFE8',       // deeper warm section surface
          muted: '#EFECE6',
        },
        ink: {
          DEFAULT: '#16130F',    // primary crisp ink text
          50: '#F9F8F6',
          100: '#F3F0EC',
          200: '#E6E1D9',
          300: '#D5CDC0',
          400: '#9E9689',
          500: '#7B766C',        // tertiary/timestamp/helper text
          600: '#5E5A52',        // high contrast secondary (4.5:1 on cream)
          700: '#423E37',
          800: '#2A2621',
          900: '#16130F',        // primary crisp ink text & dark pill bg
          950: '#0C0A08',
          secondary: '#5E5A52',
          muted: '#7B766C',
        },
        royal: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
          800: '#1E40AF',
          900: '#1E3A8A',
        },
        // Accents
        primary: {
          DEFAULT: '#1D4ED8',    // deep royal blue
          hover: '#1E40AF',
          light: '#DBEAFE',
          tint: '#EFF6FF',
        },
        highlighter: {
          DEFAULT: '#FFE45C',    // marker yellow
          base: '#FFE45C',
          hover: '#FCD34D',
          tint: '#FEF9C3',
        },
        // Status Colors (with 8-12% tinted backgrounds)
        status: {
          verified: '#059669',       // Emerald
          verifiedBg: '#ECFDF5',
          verifiedBorder: '#A7F3D0',
          ambiguous: '#D97706',      // Amber
          ambiguousBg: '#FFFBEB',
          ambiguousBorder: '#FDE68A',
          refused: '#DC2626',        // Coral
          refusedBg: '#FEF2F2',
          refusedBorder: '#FECACA',
          info: '#4F46E5',           // Indigo
          infoBg: '#EEF2FF',
          infoBorder: '#C7D2FE',
        },
        // Backward compatibility mappings
        cream: {
          50: '#FDFCF9',
          100: '#FAF8F5',
          200: '#F3EFE8',
          300: '#EAE6DF',
          400: '#DFD8CC',
          500: '#C5BCAE',
        },
      },
      fontFamily: {
        display: ['Fraunces', 'Instrument Serif', 'Georgia', 'serif'],
        serif: ['Instrument Serif', 'Fraunces', 'Georgia', 'serif'],
        sans: ['Inter', 'Instrument Sans', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        'paper-sm': '0 1px 2px 0 rgba(22, 19, 15, 0.04)',
        'paper': '0 1px 3px 0 rgba(22, 19, 15, 0.05), 0 1px 2px -1px rgba(22, 19, 15, 0.03)',
        'paper-md': '0 4px 12px -2px rgba(22, 19, 15, 0.06), 0 2px 6px -2px rgba(22, 19, 15, 0.04)',
        'paper-lg': '0 10px 24px -4px rgba(22, 19, 15, 0.08), 0 4px 8px -2px rgba(22, 19, 15, 0.03)',
        'paper-lift': '0 12px 28px -6px rgba(22, 19, 15, 0.09), 0 4px 10px -2px rgba(22, 19, 15, 0.04)',
        'highlighter': '0 0 0 3px rgba(255, 228, 92, 0.45)',
      },
      borderRadius: {
        'paper': '0.875rem',
      },
    },
  },
  plugins: [],
}
