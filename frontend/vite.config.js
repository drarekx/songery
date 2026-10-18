// Construcció del frontend amb Vite: tot va a canconer/static/dist/, amb noms fixos perquè Flask
// i el codi que encara no és Vue (editor.js…) els importin directament.
//   canconer.js  motor de dibuix de pàgines i editor de lletres (Tiptap)
//   vue.js       components Vue i l'estat compartit (Pinia) que munten les pàgines
//   dialegs.js   diàlegs (confirmar, avisar, preguntar) de totes les pàgines
// Les dues entrades comparteixen els trossos comuns (una sola còpia de Vue i de Pinia).
import { fileURLToPath, URL } from "node:url";
import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [vue()],
  base: "./",
  define: { __VUE_OPTIONS_API__: "false", __VUE_PROD_DEVTOOLS__: "false", __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: "false" },
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  build: {
    outDir: "../canconer/static/dist",
    emptyOutDir: true,
    sourcemap: true,
    target: "es2022",
    rollupOptions: {
      input: { canconer: "src/index.js", vue: "src/vue.js", dialegs: "src/dialegs.js" },
      preserveEntrySignatures: "exports-only",
      output: { entryFileNames: "[name].js", chunkFileNames: "trossos/[name]-[hash].js", assetFileNames: "[name][extname]" },
    },
  },
  test: {
    environment: "happy-dom",
    include: ["tests/**/*.test.js"],
  },
});
