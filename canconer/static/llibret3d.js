// Llibret en 3D: el PDF A5 muntat com un llibret de debò sobre la taula, amb fulls que es giren pel llom.
// Cada full porta dues pàgines (davant la senar, darrere la parell). Es passa pàgina clicant a la
// meitat dreta o esquerra, amb les fletxes o amb els botons. Només es dibuixen les pàgines de prop.
import * as pdfjs from "./vendor/pdfjs/pdf.min.mjs";

pdfjs.GlobalWorkerOptions.workerSrc = new URL("./vendor/pdfjs/pdf.worker.min.mjs", import.meta.url).href;

const SEPARACIO = 0.6; // px de gruix entre fulls apilats
const DURADA = 900; // ms que triga a girar un full

export class Llibret3D {
  /**
   * @param {HTMLElement} contenidor on es munta el llibret (ha de tenir alçada)
   * @param {object} opcions
   *   titols: funció (numPagina) => títol de la cançó que hi comença ("" si cap)
   */
  constructor(contenidor, opcions = {}) {
    this.contenidor = contenidor;
    this.titols = opcions.titols || (() => "");
    this.document = null;
    this.url = null;
    this.girats = 0; // fulls girats (0: tancat, mostra la portada)
    this.fulls = [];
    this.generacio = 0;
    this.redueix = window.matchMedia("(prefers-reduced-motion: reduce)");

    this.escena = el("div", "llibret3d-escena");
    this.llibre = el("div", "llibret3d-llibre");
    this.gruixEsquerra = el("div", "llibret3d-gruix esquerra");
    this.gruixDreta = el("div", "llibret3d-gruix dreta");
    this.ombraEsquerra = el("div", "llibret3d-ombra-taula esquerra");
    this.ombraDreta = el("div", "llibret3d-ombra-taula dreta");
    this.llibre.append(this.ombraEsquerra, this.ombraDreta, this.gruixEsquerra, this.gruixDreta);
    this.escena.append(this.llibre);

    const enrere = boto("Pàgina anterior", '<path d="m12 5-5 5 5 5"/>');
    const endavant = boto("Pàgina següent", '<path d="m8 5 5 5-5 5"/>');
    enrere.addEventListener("click", () => this.passa(-1));
    endavant.addEventListener("click", () => this.passa(1));
    this.llegenda = el("p", "llibret3d-llegenda");
    this.llegenda.setAttribute("aria-live", "polite");
    const barra = el("div", "llibret3d-barra");
    barra.append(enrere, this.llegenda, endavant);
    this.botons = { enrere, endavant };

    this.arrel = el("div", "llibret3d");
    this.arrel.tabIndex = 0;
    this.arrel.setAttribute("role", "region");
    this.arrel.setAttribute("aria-label", "Llibret en 3D. Fes servir les fletxes per passar pàgina.");
    this.arrel.append(this.escena, barra);
    contenidor.replaceChildren(this.arrel);

    // Clic a la meitat dreta del llibre: endavant; a l'esquerra: enrere.
    this.escena.addEventListener("click", (e) => {
      const r = this.llibre.getBoundingClientRect();
      this.passa(e.clientX >= r.left + r.width / 2 ? 1 : -1);
    });
    this.arrel.addEventListener("keydown", (e) => {
      const direccio = { ArrowRight: 1, ArrowLeft: -1, PageDown: 1, PageUp: -1 }[e.key];
      if (direccio) { e.preventDefault(); this.passa(direccio); }
      if (e.key === "Home") { e.preventDefault(); this.ves(0); }
      if (e.key === "End") { e.preventDefault(); this.ves(this.fulls.length); }
    });

    new ResizeObserver(() => {
      clearTimeout(this._redimensio);
      this._redimensio = setTimeout(() => this.mida(), 120);
    }).observe(contenidor);
  }

  /** Carrega el PDF A5 i munta els fulls (si l'URL no ha canviat, no fa res). */
  async carrega(url) {
    if (url === this.url && this.document) return this.arrel.focus({ preventScroll: true });
    const generacio = ++this.generacio;
    const document = await pdfjs.getDocument({ url, isEvalSupported: false }).promise;
    if (generacio !== this.generacio) return document.destroy();
    this.document?.destroy();
    this.document = document;
    this.url = url;
    const base = (await document.getPage(1)).getViewport({ scale: 1 });
    this.proporcio = base.height / base.width;
    this.munta();
    this.mida();
    this.arrel.focus({ preventScroll: true });
  }

  munta() {
    this.fulls.forEach((f) => f.node.remove());
    const n = this.document.numPages;
    this.fulls = [];
    for (let i = 0; i < Math.ceil(n / 2); i++) {
      const node = el("div", "llibret3d-full");
      const cares = [2 * i + 1, 2 * i + 2].map((p, j) => {
        const cara = el("div", `llibret3d-cara ${j ? "darrere" : "davant"}`);
        const llenc = document.createElement("canvas");
        cara.append(llenc, el("span", "llibret3d-ombra"));
        node.append(cara);
        return { n: p <= n ? p : null, llenc, dibuixada: false };
      });
      this.llibre.append(node);
      this.fulls.push({ node, cares });
    }
    this.girats = Math.min(this.girats, this.fulls.length);
    this.posa({ anima: false });
  }

  /** Mida de les pàgines segons l'espai disponible (el llibret obert ha de cabre sencer). */
  mida() {
    if (!this.document) return;
    const amplada = this.contenidor.clientWidth - 48;
    const alcada = this.contenidor.clientHeight - 120;
    const pagina = Math.max(80, Math.floor(Math.min(amplada / 2, alcada / this.proporcio / Math.cos(0.3))));
    this.ample = pagina;
    this.llibre.style.setProperty("--ample", `${pagina}px`);
    this.llibre.style.setProperty("--alt", `${Math.round(pagina * this.proporcio)}px`);
    for (const f of this.fulls) for (const c of f.cares) c.dibuixada = false;
    this.dibuixaProperes();
  }

  passa(direccio) {
    this.ves(this.girats + direccio);
  }

  ves(girats) {
    girats = Math.max(0, Math.min(this.fulls.length, girats));
    if (girats === this.girats) return;
    this.girats = girats;
    this.posa({ anima: !this.redueix.matches });
  }

  /** Col·loca cada full (girat o no) i el llibre (centrat si està tancat). */
  posa({ anima }) {
    const total = this.fulls.length;
    this.fulls.forEach((f, i) => {
      const girat = i < this.girats;
      // Els girats s'apilen a l'esquerra (l'últim, a sobre); els altres a la dreta (el primer, a sobre).
      const z = (girat ? i + 1 : total - i) * SEPARACIO;
      const estava = f.node.classList.contains("girat");
      f.node.classList.toggle("girat", girat);
      f.node.style.transition = anima ? "" : "none";
      f.node.style.transform = `translateZ(${z}px) rotateY(${girat ? -180 : 0}deg)`;
      if (anima && estava !== girat) {
        // Mentre gira, a sobre de tot, i amb una ombra que es mou.
        f.node.classList.add("girant");
        clearTimeout(f.temps);
        f.temps = setTimeout(() => f.node.classList.remove("girant"), DURADA);
      }
    });
    // Tancat (portada o contraportada), el llibre es desplaça perquè quedi centrat.
    const desplacament = this.girats === 0 ? -0.5 : this.girats === total ? 0.5 : 0;
    this.llibre.style.setProperty("--desplacament", desplacament);
    this.ombraEsquerra.classList.toggle("visible", this.girats > 0);
    this.ombraDreta.classList.toggle("visible", this.girats < total);
    this.llibre.classList.toggle("sense-animacio", !anima);
    this.gruixEsquerra.style.width = `${Math.min(14, this.girats * SEPARACIO * 1.5)}px`;
    this.gruixDreta.style.width = `${Math.min(14, (total - this.girats) * SEPARACIO * 1.5)}px`;
    this.botons.enrere.disabled = this.girats === 0;
    this.botons.endavant.disabled = this.girats === total;
    this.llegenda.innerHTML = this.textLlegenda();
    this.dibuixaProperes();
  }

  textLlegenda() {
    const n = this.document.numPages;
    if (this.girats === 0) return "Portada";
    if (this.girats === this.fulls.length) return "Contraportada";
    const esquerra = 2 * this.girats;
    const titol = this.titols(esquerra) || this.titols(esquerra + 1);
    return `Pàgines <strong>${esquerra}</strong> i <strong>${Math.min(n, esquerra + 1)}</strong>` +
      (titol ? ` · ${escapa(titol)}` : "");
  }

  /** Dibuixa les pàgines visibles i les de dos fulls endavant i endarrere. */
  async dibuixaProperes() {
    if (!this.document || !this.ample) return;
    const generacio = this.generacio;
    const ordre = [];
    for (let d = 0; d <= 2; d++) {
      for (const i of new Set([this.girats - 1 - d, this.girats + d])) {
        if (this.fulls[i]) ordre.push(...this.fulls[i].cares);
      }
    }
    for (const cara of ordre) {
      if (cara.dibuixada || !cara.n) continue;
      cara.dibuixada = true;
      const pagina = await this.document.getPage(cara.n);
      if (generacio !== this.generacio) return;
      const base = pagina.getViewport({ scale: 1 });
      const vista = pagina.getViewport({ scale: (this.ample / base.width) * Math.min(2, window.devicePixelRatio || 1) });
      cara.llenc.width = Math.floor(vista.width);
      cara.llenc.height = Math.floor(vista.height);
      await pagina.render({ canvasContext: cara.llenc.getContext("2d"), viewport: vista }).promise;
    }
  }
}

function el(etiqueta, classe) {
  const node = document.createElement(etiqueta);
  node.className = classe;
  return node;
}

function boto(titol, cami) {
  const b = el("button", "btn btn-icona h-9 w-9");
  b.type = "button";
  b.title = titol;
  b.setAttribute("aria-label", titol);
  b.innerHTML = `<svg class="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">${cami}</svg>`;
  return b;
}

function escapa(text) {
  return text.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
}
