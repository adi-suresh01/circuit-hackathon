/** @type {import('tailwindcss').Config} */
// Optional: Tailwind is used for CopilotKit-style UI (cards, badges, spacing).
// If you remove Tailwind, replace classes in App.jsx with plain CSS.
module.exports = {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
