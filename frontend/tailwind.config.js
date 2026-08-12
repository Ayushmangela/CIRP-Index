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
          admitted: "#4A6FA5",
          cirp_ongoing: "#B8860B",
          resolution_approved: "#2D5F3F",
          liquidation: "#A0432B",
          dissolved: "#7A7873",
          withdrawn: "#6B5B7B",
          unclassified: "#9A9892"
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
