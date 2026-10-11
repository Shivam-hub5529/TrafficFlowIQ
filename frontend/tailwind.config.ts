import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        concrete: "#E4E6E1", paint: "#FAFAF6", sign: "#0B5C45", signdark: "#08402F", amber: "#F2B21B",
        brake: "#C0392B", ink: "#26302C", lane: "#A9B0A8", mist: "#D5E3DB", led: "#FFB000", panel: "#1E2421",
      },
      fontFamily: {
        display: ["Overpass", "Arial Narrow", "Arial", "sans-serif"],
        body: ["Public Sans", "system-ui", "sans-serif"],
        led: ["Overpass Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
