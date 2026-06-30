import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ash: {
          900: "#0f0f0d",
          800: "#1a1a16",
          700: "#242420",
        },
        rust: {
          500: "#c0522a",
          400: "#d4643a",
        },
        sand: {
          300: "#c9b99a",
          200: "#ddd0b8",
          100: "#f0e8d8",
        },
      },
      fontFamily: {
        mono: ["'Courier New'", "Courier", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
