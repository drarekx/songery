/** Configuració de Tailwind CSS v3 per a la interfície web (el PDF té el seu propi CSS). */
module.exports = {
  content: [
    "./canconer/templates/**/*.html",
    "./canconer/static/*.js",
    "./frontend/src/**/*.js",
  ],
  // Classes que el JavaScript compon dinàmicament (Tailwind no les pot trobar al codi).
  safelist: ["nansa-nw", "nansa-n", "nansa-ne", "nansa-e", "nansa-se", "nansa-s", "nansa-sw", "nansa-w"],
  theme: {
    extend: {
      colors: {
        // Paper i tinta: la paleta d'una impremta.
        paper: { 50: "#fcfbf8", 100: "#f6f4ef", 200: "#ede9e0", 300: "#dfd9cc", DEFAULT: "#f6f4ef" },
        ink: { 300: "#a7a196", 400: "#8a8478", 500: "#6b665c", 700: "#3a3832", 900: "#1b1a17", DEFAULT: "#1b1a17" },
        // Vermelló: el color dels acords, únic accent.
        vermello: { 50: "#fdf4f2", 100: "#fbe4df", 200: "#f5c3b8", 500: "#c4321f", 600: "#a8281a", 700: "#8a2015" },
        taula: "#e6e2d8", // taula de llum on es veuen les pàgines
      },
      fontFamily: {
        display: ['"Newsreader"', "Georgia", "serif"],
        sans: ['"Hanken Grotesk"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        full: "0 1px 2px rgb(27 26 23 / 0.10), 0 6px 18px -6px rgb(27 26 23 / 0.18)",
        suau: "0 1px 2px rgb(27 26 23 / 0.06), 0 1px 1px rgb(27 26 23 / 0.04)",
      },
    },
  },
  plugins: [],
};
