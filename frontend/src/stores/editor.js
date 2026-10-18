// Estat de l'editor compartit entre els components Vue i el codi de l'editor que encara no ho és
// (canconer/static/editor.js). editor.js hi escriu l'estat (sincronitza) i hi connecta les accions
// que encara fa ell (connecta); els components el llegeixen i criden les accions.
import { defineStore } from "pinia";
import { markRaw } from "vue";

/** Tipus de dades d'arrossegar un acord del panell d'acords a la pàgina. */
export const TIPUS_ACORD = "application/x-canconer-acord";

export const useEditorStore = defineStore("editor", {
  state: () => ({
    /** Es pot editar el que hi ha obert (una versió fixada, per exemple, no). */
    editable: true,
    /** Cançó oberta ({id, titol}) o null si el que hi ha obert no és una cançó. */
    canco: null,
    /** Acords de la cançó, ja transportats i sense el baix (D/F# → D), en ordre d'aparició. */
    acords: [],
    /** SVG del diagrama de cada acord. */
    diagrames: {},
    /** Vídeos de YouTube de la cançó: [{id, video, inici, titol, canal, inclou_qr}]. */
    videos: [],
    urls: {},
    /** Accions que encara fa editor.js: {afegeixDiagrama(nom), canviaVideos(llista)…}. */
    ponts: markRaw({}),
  }),
  actions: {
    sincronitza(canvis) {
      this.$patch(canvis);
    },
    connecta(ponts) {
      this.ponts = markRaw({ ...this.ponts, ...ponts });
    },
    afegeixDiagrama(nom) {
      this.ponts.afegeixDiagrama?.(nom);
    },
    canviaVideos(llista) {
      this.videos = llista;
      this.ponts.canviaVideos?.(llista);
    },
  },
});
