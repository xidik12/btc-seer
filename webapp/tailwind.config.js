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
          blue: '#7a6535',
          green: '#00d68f',
          red: '#ff4d6a',
          yellow: '#ffb800',
          orange: '#ff8c42',
          purple: '#a78bfa',
        },
        text: {
          primary: '#ffffff',
          secondary: '#c0c0d0',
          muted: '#9090a8',
        },
      },
      boxShadow: {
        card: '0 4px 24px rgba(0, 0, 0, 0.4), 0 1px 8px rgba(0, 0, 0, 0.3), 0 0 1px rgba(0, 0, 0, 0.2)',
      },
    },
  },
  plugins: [],
}
