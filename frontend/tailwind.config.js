/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          900: '#0f1117',
          800: '#161822',
          700: '#1e2030',
          600: '#2a2d3e',
        },
      },
    },
  },
  plugins: [],
}