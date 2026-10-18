/** Configuració de Tailwind CSS v3 per a la interfície web (el PDF té el seu propi CSS). */
module.exports = {
  content: [
    "./canconer/templates/**/*.html",
    "./canconer/static/*.js",
    "./frontend/src/**/*.{js,vue}",
  ],
  // Classes que el JavaScript compon dinàmicament (Tailwind no les pot trobar al codi).
  safelist: ["nansa-nw", "nansa-n", "nansa-ne", "nansa-e", "nansa-se", "nansa-s", "nansa-sw", "nansa-w"],
  theme: {
    extend: {
      colors: {
        // Blanc, negre i grisos neutres.
        paper: { 50: "#fafafa", 100: "#f5f5f5", 200: "#e9e9e9", 300: "#d9d9d9", DEFAULT: "#f5f5f5" },
        ink: { 300: "#a6a6a6", 400: "#8c8c8c", 500: "#6b6b6b", 700: "#3b3b3b", 900: "#141414", DEFAULT: "#141414" },
        // Accent de la interfície: el negre (botons principals, selecció, focus).
        accent: { 50: "#f2f2f2", 100: "#e6e6e6", 200: "#d4d4d4", 500: "#141414", 600: "#2e2e2e", 700: "#000000" },
        // Vermell: només per esborrar i per als errors.
        perill: { 50: "#fdf3f2", 100: "#fbe2df", 200: "#f4c0b9", 500: "#b42318", 600: "#b42318", 700: "#8f1c13" },
        taula: "#ebebeb", // taula de llum on es veuen les pàgines
      },
      fontFamily: {
        display: ['"Newsreader"', "Georgia", "serif"],
        sans: ['"Hanken Grotesk"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        full: "0 1px 2px rgb(20 20 20 / 0.10), 0 6px 18px -6px rgb(20 20 20 / 0.18)",
        suau: "0 1px 2px rgb(20 20 20 / 0.06), 0 1px 1px rgb(20 20 20 / 0.04)",
      },
    },
  },
  plugins: [],
};
