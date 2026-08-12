/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#FAF9F6",
        foreground: "#1A1A1A",
        ink: "#0A192F",
        hairline: "#E5E5E0",
        outcome: {
          admitted: "#3B5284",
          ongoing: "#D97706",
          approved: "#15803D",
          liquidation: "#B91C1C",
          dissolved: "#737373",
          withdrawn: "#8B5CF6",
          unclassified: "#9CA3AF"
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        sans: ['Inter', 'sans-serif']
      }
    },
  },
  plugins: [],
}
