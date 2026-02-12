/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx}"
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["Space Grotesk", "sans-serif"],
        mono: ["Share Tech Mono", "monospace"]
      },
      colors: {
        night: "#09090d",
        obsidian: "#0f1218",
        plasma: "#00f5d4",
        circuit: "#0bd3ff",
        ember: "#ff7a18"
      },
      boxShadow: {
        neon: "0 0 24px rgba(11, 211, 255, 0.35)",
        glow: "0 0 60px rgba(0, 245, 212, 0.2)"
      }
    }
  },
  plugins: []
};
