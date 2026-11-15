import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f3ecdf",
        ink: "#1b2421",
        card: "#fffaf3",
        line: "#e4d7c6",
        ember: "#c84b1a",
        pine: "#1f6a4a",
        moss: "#e7f2ec",
      },
      fontFamily: {
        serif: ["Iowan Old Style", "Palatino Linotype", "Palatino", "Georgia", "serif"],
        sans: ["Avenir Next", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
