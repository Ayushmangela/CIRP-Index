/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#FAF9F6",
        foreground: "#1A1A1A",
        ink: "#0A192F",
        hairline: "#E5E5E0",
        cream: {
          DEFAULT: "#FAF9F6",
          50: "#FFFEFC",
          100: "#F3F0E8",
          200: "#EAE5D8",
        },
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
        mono: ['var(--font-mono)', '"JetBrains Mono"', 'monospace'],
        sans: ['var(--font-sans)', 'Inter', 'sans-serif'],
        serif: ['var(--font-serif)', '"Source Serif 4"', 'Georgia', 'serif']
      }
    },
  },
  plugins: [],
}
