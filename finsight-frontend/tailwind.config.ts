/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ['IBM Plex Mono', 'monospace'],
        display: ['Syne', 'sans-serif'],
        sans: ['DM Sans', 'sans-serif'],
      },
      colors: {
        bg: '#0a0d12',
        surface: '#10141c',
        surface2: '#161b26',
        surface3: '#1d2535',
        accent: '#00e5a0',
        accent2: '#00b87a',
        amber: '#f5a623',
        danger: '#ff4d4d',
        blue: '#4d9fff',
        border: 'rgba(255,255,255,0.07)',
        border2: 'rgba(255,255,255,0.12)',
        text1: '#e8eaf2',
        text2: '#8b92a8',
        text3: '#555e72',
      },
    },
  },
  plugins: [],
}
