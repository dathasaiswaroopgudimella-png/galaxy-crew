/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bgPrimary: "#0a0c10",
        borderPrimary: "rgba(255, 255, 255, 0.08)",
        glowPrimary: "rgba(56, 189, 248, 0.3)",
        textPrimary: "#f3f4f6",
        textMuted: "#9ca3af"
      },
      fontFamily: {
        sans: ['Inter', 'IBM Plex Sans', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}
