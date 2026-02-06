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
          card: '#22222e',
          hover: '#2a2a38',
        },
        accent: {
          blue: '#4a9eff',
          green: '#00d68f',
          red: '#ff4d6a',
          yellow: '#ffb800',
          orange: '#ff8c42',
        },
        text: {
          primary: '#ffffff',
          secondary: '#8b8b9e',
          muted: '#5a5a70',
        },
      },
    },
  },
  plugins: [],
}
