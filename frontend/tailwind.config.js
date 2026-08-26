/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        gov: {
          navy: "#0f2a4a",
          blue: "#1a4a8a",
          accent: "#c8a24b",
          paper: "#f5f7fa",
        },
      },
    },
  },
  plugins: [],
};