/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      colors: {
        apple: {
          blue: '#0071e3',
          green: '#34c759',
          orange: '#ff9500',
          red: '#ff3b30',
          purple: '#af52de',
          gray: '#8e8e93'
        }
      },
      boxShadow: {
        glass: '0 8px 32px rgba(0,0,0,0.08), 0 1px 0 rgba(255,255,255,1) inset'
      }
    }
  },
  plugins: []
}
