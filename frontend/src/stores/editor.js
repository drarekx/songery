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
    /** Cançó oberta ({id, titol, autor}) o null si el que hi ha obert no és una cançó. */
    canco: null,
    /** Com és la cançó oberta en aquest cançoner: {transport, inclosa, inici, versio_id, versio_numero,
     *  versio_ultima, usos}; null si no n'hi ha cap d'oberta. */
    entrada: null,
    /** Acords de la cançó, ja transportats i sense el baix (D/F# → D), en ordre d'aparició. */
    acords: [],
    /** SVG del diagrama de cada acord. */
    diagrames: {},
    /** Vídeos de YouTube de la cançó: [{id, video, inici, titol, canal, inclou_qr}]. */
    videos: [],
    /** Estils de text del cançoner ({clau: {nom, font, mida, pes, …}}). */
    estils: {},
    /** Tipografies disponibles: [{clau, nom, categoria, css}]. */
    tipografies: [],
    /** Capes de les pàgines obertes: [{etiqueta, elements: [{id, tipus, nom, font, bloquejat, grup,
     *  seleccionat, index}], mestra: n}] (cada element, del de davant al del fons). */
    capes: null,
    /** Pàgines mestres del cançoner: [{id, nom}]. */
    mestres: [],
    /** Columna de l'esquerra. obert: el que hi ha obert ("llibre", "canco:id", "especial:portada",
     *  "mestra:id"); cancons: [{id, titol, tipus, inclosa, inici, versio_numero (si està fixada),
     *  desfasada, usos, pagines: [números]}]; total: pàgines del llibret. */
    llista: { obert: null, cancons: [], total: null },
    /** Panell de propietats. mode: "pagina" (no hi ha res seleccionat), "element" o "multi".
     *  pagina: {tipus (el que hi ha obert: canco, especial, mestra o llibre), mestra, costat, fons,
     *           nomMestra, mestraEsborrable}
     *  element: còpia de l'element seleccionat, amb grup (si forma part d'un grup), infoMarc
     *           ({text, alerta}, per als marcs de lletra)
     *  multi: {n, grup (la selecció és un grup sencer), algunGrup}
     *  moure: {visible, anterior, seguent} (botons per passar-ho a la pàgina del costat) */
    propietats: { mode: "pagina", pagina: null, element: null, multi: null, moure: { visible: false, anterior: false, seguent: false } },
    urls: {},
    /** Accions que encara fa editor.js. */
    ponts: markRaw({}),
  }),
  getters: {
    /** Transport en semitons de la cançó oberta en aquest cançoner. */
    transport: (estat) => Number(estat.entrada?.transport || 0),
  },
  actions: {
    sincronitza(canvis) {
      this.$patch((estat) => Object.assign(estat, canvis));
    },
    connecta(ponts) {
      this.ponts = markRaw({ ...this.ponts, ...ponts });
    },
    crida(nom, ...args) {
      return this.ponts[nom]?.(...args);
    },
    afegeixDiagrama(nom) {
      this.crida("afegeixDiagrama", nom);
    },
    canviaVideos(llista) {
      this.videos = llista;
      this.crida("canviaVideos", llista);
    },
    /** Títol o autor de la cançó oberta. */
    canviaDadesCanco(prop, valor) {
      if (!this.canco || !this.editable) return;
      this.canco[prop] = valor;
      if (prop === "titol") {
        const fila = this.llista.cancons.find((c) => c.id === this.canco.id);
        if (fila) fila.titol = valor;
      }
      this.crida("canviaDadesCanco", prop, valor);
    },
    /** Transport, «surt al PDF» o on comença, en aquest cançoner. */
    canviaEntrada(canvis) {
      if (!this.entrada) return;
      Object.assign(this.entrada, canvis);
      this.crida("canviaEntrada", canvis);
    },
    mouTransport(semitons) {
      let n = this.transport + semitons;
      if (n > 11) n -= 12;
      if (n < -11) n += 12;
      this.canviaEntrada({ transport: n });
    },
    /** Propietats de l'element seleccionat (es tornen a dibuixar). */
    canviaPropietats(propietats) {
      const e = this.propietats.element;
      if (!e || !this.editable) return;
      Object.assign(e, propietats);
      this.crida("canviaPropietats", propietats);
    },
    /** Posició, mida, rotació i opacitat: es mouen sense tornar a dibuixar l'element. */
    canviaPosicio(prop, valor) {
      const e = this.propietats.element;
      if (!e || !this.editable || !Number.isFinite(valor)) return;
      e[prop] = valor;
      this.crida("canviaPosicio", prop, valor);
    },
    /** Format propi de l'element (sobre el de l'estil); valor buit: torna al de l'estil. */
    canviaFormat(prop, valor) {
      const e = this.propietats.element;
      if (!e || !this.editable) return;
      const format = { ...(e.format || {}) };
      if (valor === "" || valor === null || valor === undefined) delete format[prop];
      else format[prop] = valor;
      this.canviaPropietats({ format });
    },
    canviaEstil(clau, prop, valor) {
      if (!this.estils[clau]) return;
      this.estils[clau][prop] = valor;
      this.crida("canviaEstil", clau, prop, valor);
    },
  },
});
