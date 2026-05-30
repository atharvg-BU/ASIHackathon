import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        panel: "#101923",
        panel2: "#142231",
        cyanline: "#43d9ff",
        runway: "#8cf7b1",
        amber: "#ffbc58",
        danger: "#ff5b6e"
      }
    }
  },
  plugins: []
};

export default config;
