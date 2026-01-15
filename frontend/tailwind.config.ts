/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#0f0f0f',
        foreground: '#fafafa',
        card: '#1a1a1a',
        border: '#2a2a2a',
        primary: '#3b82f6',
        'primary-hover': '#2563eb',
        muted: '#6b7280',
        success: '#22c55e',
        error: '#ef4444',
      },
    },
  },
  plugins: [],
}
