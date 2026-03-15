/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: {
          primary: '#0f0f14',
          secondary: '#1a1a24',
          card: 'rgba(34, 34, 46, 0.65)',
          hover: '#2a2a38',
        },
        accent: {
          blue: '#3b82f6',       // Fixed: was #7a6535 (gold). Now actual blue for primary actions
          green: '#00d68f',
          red: '#ff4d6a',
          yellow: '#ffb800',
          orange: '#ff8c42',
          purple: '#a78bfa',
          gold: '#7a6535',       // Preserved old "blue" value as gold for backward compat
        },
        text: {
          primary: '#ffffff',
          secondary: '#c0c0d0',
          muted: '#9090a8',
        },
      },
      fontSize: {
        // Enforce minimum readable sizes — replaces text-[8px] to text-[11px] abuse
        'xxs': ['0.625rem', { lineHeight: '0.875rem' }],  // 10px — absolute minimum
        'xs': ['0.75rem', { lineHeight: '1rem' }],         // 12px — standard small
      },
      borderRadius: {
        'card': '1rem',       // 16px — standard card radius
        'card-sm': '0.75rem', // 12px — inner card / sub-card radius
      },
      boxShadow: {
        card: '0 4px 24px rgba(0, 0, 0, 0.4), 0 1px 8px rgba(0, 0, 0, 0.3), 0 0 1px rgba(0, 0, 0, 0.2)',
        'card-hover': '0 8px 32px rgba(0, 0, 0, 0.5), 0 2px 12px rgba(0, 0, 0, 0.35)',
      },
    },
  },
  plugins: [],
}
