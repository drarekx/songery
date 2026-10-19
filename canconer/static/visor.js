// Visor de PDF amb PDF.js: mostra el llibret A5 per dobles pàgines (com quan està plegat i obert)
// o els fulls A4 imposats amb el número de cada cara. Té zoom i només dibuixa les pàgines visibles.
import * as pdfjs from "./vendor/pdfjs/pdf.min.mjs";

pdfjs.GlobalWorkerOptions.workerSrc = new URL("./vendor/pdfjs/pdf.worker.min.mjs", import.meta.url).href;

/** Nivells de zoom relatius a "ajustat a l'amplada" (1). */
export const NIVELLS_ZOOM = [0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4];

/** Cares dels fulls A4 per a un llibret de n pàgines (la mateixa fórmula que imposicio.py). */
export function caresImposicio(n) {
  const cares = [];
  for (let i = 0; i < n / 4; i++) {
    cares.push({ full: i + 1, costat: "davant", esquerra: n - 2 * i, dreta: 1 + 2 * i });
    cares.push({ full: i + 1, costat: "darrere", esquerra: 2 + 2 * i, dreta: n - 1 - 2 * i });
  }
  return cares;
}

/** Cares per a fulls solts (anelles): talla i apila, com ordre_talla_i_apila d'imposicio.py (0: en blanc). */
export function caresTallaIApila(n) {
  const fulls = Math.ceil(n / 4);
  const pagina = (p) => (p <= n ? p : 0);
  const cares = [];
  for (let i = 0; i < fulls; i++) {
    cares.push({ full: i + 1, costat: "davant", esquerra: pagina(1 + 2 * i), dreta: pagina(1 + 2 * (fulls + i)) });
    cares.push({ full: i + 1, costat: "darrere", esquerra: pagina(2 + 2 * (fulls + i)), dreta: pagina(2 + 2 * i) });
  }
  return cares;
}

export class Visor {
  /**
   * @param {HTMLElement} contenidor element on es dibuixen les pàgines
   * @param {object} opcions
   *   mode: "dobles" (llibret A5 obert) o "fulls" (A4 imposat)
   *   desplacament: element que fa scroll (per defecte, el mateix contenidor)
   *   titols: funció (numPagina) => text per a la llegenda d'una doble pàgina
   *   clicPagina: funció (numPagina) cridada en clicar una pàgina A5
   *   canviZoom: funció (zoom) cridada quan canvia el zoom
   *   fullsSolts: nombre de pàgines A5 si els fulls A4 van per tallar i apilar (anelles); si no, null
   *   marges: marges d'enquadernació en mm ({interior, exterior, superior, inferior}) per dibuixar-ne
   *           les guies (només a la pantalla; es mostren amb la classe .amb-marges)
   */
  constructor(contenidor, opcions = {}) {
    this.contenidor = contenidor;
    this.mode = opcions.mode || "dobles";
    this.desplacament = opcions.desplacament || contenidor;
    this.titols = opcions.titols || (() => "");
    this.clicPagina = opcions.clicPagina || null;
    this.canviZoom = opcions.canviZoom || (() => {});
    this.marges = opcions.marges || null;
    this.fullsSolts = opcions.fullsSolts || null;
    this.zoom = 1;
    this.document = null;
    this.url = null;
    this.generacio = 0;
    this.marcades = [];
    this.llocs = []; // {llenc, n, escala} de la vista actual
    this.observador = null;

    let ampladaAnterior = contenidor.clientWidth;
    new ResizeObserver(() => {
      if (Math.abs(contenidor.clientWidth - ampladaAnterior) < 40) return;
      ampladaAnterior = contenidor.clientWidth;
      clearTimeout(this._redimensio);
      this._redimensio = setTimeout(() => this.dibuixa(), 200);
    }).observe(contenidor);

    // Ctrl/⌘ + roda (i el gest de pinça del trackpad, que el navegador envia igual) fa zoom.
    const zonaZoom = this.desplacament === document.scrollingElement ? contenidor : this.desplacament;
    zonaZoom.addEventListener("wheel", (e) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      this._rodaAcumulada = (this._rodaAcumulada || 0) + e.deltaY;
      if (Math.abs(this._rodaAcumulada) < 40) return;
      this.passaZoom(this._rodaAcumulada < 0 ? 1 : -1, e);
      this._rodaAcumulada = 0;
    }, { passive: false });
  }

  get total() {
    return this.document ? this.document.numPages : 0;
  }

  /** Carrega un PDF (si l'URL no ha canviat, no fa res). Manté la posició de scroll. */
  async carrega(url) {
    if (url === this.url && this.document) return;
    const generacio = ++this.generacio;
    const document = await pdfjs.getDocument({ url, isEvalSupported: false }).promise;
    if (generacio !== this.generacio) {
      document.destroy();
      return;
    }
    const anterior = this.document;
    this.document = document;
    this.url = url;
    await this.dibuixa();
    if (anterior) anterior.destroy();
  }

  async canviaMode(mode, url) {
    this.mode = mode;
    this.url = null;
    await this.carrega(url);
  }

  // ---------------------------------------------------------------- Zoom

  /** Puja (+1) o baixa (-1) un nivell de zoom, mantenint fix el punt sota el ratolí si n'hi ha. */
  passaZoom(direccio, esdeveniment = null) {
    const i = NIVELLS_ZOOM.findIndex((z) => z >= this.zoom - 1e-6);
    const actual = i < 0 ? NIVELLS_ZOOM.length - 1 : i;
    const nou = NIVELLS_ZOOM[Math.min(NIVELLS_ZOOM.length - 1, Math.max(0, actual + direccio))];
    this.posaZoom(nou, esdeveniment);
  }

  posaZoom(zoom, esdeveniment = null) {
    if (Math.abs(zoom - this.zoom) < 1e-6) return;
    const d = this.desplacament;
    // Punt de referència: el cursor o el centre de la zona visible.
    const caixa = d === document.scrollingElement ? { left: 0, top: 0 } : d.getBoundingClientRect();
    const px = esdeveniment ? esdeveniment.clientX - caixa.left : d.clientWidth / 2;
    const py = esdeveniment ? esdeveniment.clientY - caixa.top : d.clientHeight / 2;
    const fraccioX = (d.scrollLeft + px) / Math.max(1, d.scrollWidth);
    const fraccioY = (d.scrollTop + py) / Math.max(1, d.scrollHeight);

    this.zoom = zoom;
    this.canviZoom(zoom);
    this.dibuixa({ mantenirScroll: false }).then(() => {
      d.scrollLeft = fraccioX * d.scrollWidth - px;
      d.scrollTop = fraccioY * d.scrollHeight - py;
    });
  }

  // ---------------------------------------------------------------- Dibuix

  /** Construeix la vista nova, dibuixa les pàgines visibles i la substitueix d'un cop (sense parpelleig). */
  async dibuixa({ mantenirScroll = true } = {}) {
    if (!this.document) return;
    const generacio = this.generacio;
    const nou = document.createElement("div");
    nou.className = `visor-pagines visor-${this.mode}`;

    // Amplada de cada pàgina: ajustada a l'espai disponible i multiplicada pel zoom.
    // Es descompta el padding horitzontal (2×16 px) i l'espai entre columnes (40 px).
    const amplada = Math.max(200, this.desplacament === document.scrollingElement
      ? this.contenidor.clientWidth : this.desplacament.clientWidth);
    const columnes = this.mode === "dobles" && this.zoom <= 1 && amplada > 1100 ? 2 : 1;
    const ampladaGrup = Math.min((amplada - 32 - (columnes - 1) * 40) / columnes, this.mode === "dobles" ? 720 : 880);
    const ampladaPagina = Math.floor((this.mode === "dobles" ? ampladaGrup / 2 : ampladaGrup) * this.zoom);

    const pagina1 = await this.document.getPage(1);
    const base = pagina1.getViewport({ scale: 1 });
    const altPagina = Math.round(ampladaPagina * base.height / base.width);

    const grups = this.mode === "dobles" ? this._dobles() : this._fulls();
    const llocs = [];
    for (const grup of grups) {
      const figura = document.createElement("figure");
      figura.className = this.mode === "dobles" ? "visor-doble" : "visor-full";
      // Les dues pàgines d'una doble van juntes, amb l'ombra del plec al mig.
      const fulls = document.createElement("div");
      fulls.className = "fulls-doble";
      if (!grup.pagines.includes(null)) fulls.classList.add("amb-plec");
      for (const n of grup.pagines) {
        if (n === null) {
          const buit = Object.assign(document.createElement("span"), { className: "visor-buit" });
          buit.style.width = `${ampladaPagina}px`;
          buit.style.height = `${altPagina}px`;
          fulls.append(buit);
          continue;
        }
        const llenc = document.createElement("canvas");
        llenc.dataset.pagina = n;
        llenc.style.width = `${ampladaPagina}px`;
        llenc.style.height = `${altPagina}px`;
        if (this.clicPagina && this.mode === "dobles") {
          llenc.classList.add("clicable");
          llenc.title = "Edita aquesta cançó";
          llenc.addEventListener("click", () => this.clicPagina(n));
        }
        // Capa amb el número de pàgina (només a la pantalla; es mostra amb la classe .amb-ordre).
        const pagina = document.createElement("span");
        pagina.className = "pagina-visor";
        pagina.append(llenc);
        if (this.mode === "dobles") pagina.append(capaOrdre([{ numero: n, text: `pàgina ${n}` }]));
        if (this.marges) {
          // En una doble A5, la pàgina n; en un full A4, les dues A5 de la cara. Una pàgina parella té el
          // plec (marge interior) a la dreta; les mitges cares en blanc (fulls solts) no en porten.
          const a5 = this.mode === "dobles" ? [[n % 2 === 0, 0, 1]]
            : [[grup.cara.esquerra, 0], [grup.cara.dreta, 0.5]].filter(([p]) => p).map(([p, x0]) => [p % 2 === 0, x0, 0.5]);
          for (const [esquerra, x0, ample] of a5) pagina.append(guiaMarges(this.marges, esquerra, x0, ample));
        }
        fulls.append(pagina);
        llocs.push({ llenc, n, dibuixat: false });
      }
      if (grup.cara) {
        const c = grup.cara;
        const capa = capaOrdre([
          { numero: c.esquerra || "–", text: c.esquerra ? "esquerra" : "en blanc" },
          { numero: c.dreta || "–", text: c.dreta ? "dreta" : "en blanc" },
        ], `Full ${c.full} · ${c.costat === "davant" ? "cara davantera" : "cara del darrere"}`);
        capa.classList.add("ordre-full");
        fulls.append(capa);
      }
      const llegenda = document.createElement("figcaption");
      llegenda.innerHTML = grup.llegenda;
      llegenda.style.maxWidth = `${ampladaPagina * grup.pagines.length}px`;
      figura.append(fulls, llegenda);
      figura.dataset.pagines = grup.pagines.filter((n) => n !== null).join(",");
      nou.append(figura);
    }

    // Abans de substituir la vista, es dibuixen les pàgines que quedaran visibles.
    const scrollX = this.desplacament.scrollLeft;
    const scrollY = this.desplacament.scrollTop;
    const visibles = this._visiblesAprox(llocs, altPagina, nou);
    for (const lloc of visibles) {
      if (generacio !== this.generacio) return;
      await this._dibuixaPagina(lloc, ampladaPagina);
    }
    if (generacio !== this.generacio) return;

    this.contenidor.replaceChildren(nou);
    if (mantenirScroll) {
      this.desplacament.scrollLeft = scrollX;
      this.desplacament.scrollTop = scrollY;
    }
    this.llocs = llocs;
    this.marca(this.marcades);

    // La resta, quan s'hi arribi fent scroll.
    if (this.observador) this.observador.disconnect();
    this.observador = new IntersectionObserver((entrades) => {
      for (const entrada of entrades) {
        if (!entrada.isIntersecting) continue;
        const lloc = llocs.find((l) => l.llenc === entrada.target);
        this.observador.unobserve(entrada.target);
        if (lloc && !lloc.dibuixat && generacio === this.generacio) this._dibuixaPagina(lloc, ampladaPagina);
      }
    }, { root: this.desplacament === document.scrollingElement ? null : this.desplacament, rootMargin: "800px 0px" });
    llocs.filter((l) => !l.dibuixat).forEach((l) => this.observador.observe(l.llenc));
  }

  /** Pàgines que, amb el scroll actual, caurien a la zona visible (estimació per files). */
  _visiblesAprox(llocs, altPagina, nou) {
    const d = this.desplacament;
    const dalt = d.scrollTop - 800;
    const baix = d.scrollTop + (d === document.scrollingElement ? window.innerHeight : d.clientHeight) + 800;
    // Al document principal, el visor no comença a dalt de tot: es dibuixen les primeres.
    if (d === document.scrollingElement) return llocs.slice(0, 4);
    const altFila = altPagina + 60; // pàgina + llegenda + espai entre files
    return llocs.filter((l) => {
      const figura = l.llenc.closest("figure");
      const fila = [...nou.children].indexOf(figura);
      const y = 24 + fila * altFila;
      return y + altFila >= dalt && y <= baix;
    }).slice(0, 12);
  }

  async _dibuixaPagina(lloc, ampladaPagina) {
    lloc.dibuixat = true;
    const pagina = await this.document.getPage(lloc.n);
    const base = pagina.getViewport({ scale: 1 });
    // A zoom alt es limita la resolució perquè els llenços no es mengin la memòria.
    const ratio = Math.min(window.devicePixelRatio || 1, ampladaPagina > 900 ? 1.5 : 2);
    const vista = pagina.getViewport({ scale: (ampladaPagina / base.width) * ratio });
    const llenc = lloc.llenc;
    llenc.width = Math.floor(vista.width);
    llenc.height = Math.floor(vista.height);
    await pagina.render({ canvasContext: llenc.getContext("2d"), viewport: vista }).promise;
  }

  _dobles() {
    const n = this.total;
    const grups = [{ pagines: [null, 1], llegenda: "Portada" }];
    for (let e = 2; e < n; e += 2) {
      const titol = this.titols(e) || this.titols(e + 1);
      grups.push({
        pagines: [e, e + 1],
        llegenda: `Pàgines ${e} i ${e + 1}${titol ? " · " + escapa(titol) : ""}`,
      });
    }
    if (n > 1) grups.push({ pagines: [n, null], llegenda: "Contraportada" });
    return grups;
  }

  _fulls() {
    // El PDF A4 té les cares en ordre: davant full 1, darrere full 1, davant full 2...
    const cares = this.fullsSolts ? caresTallaIApila(this.fullsSolts) : caresImposicio(this.total * 2);
    const num = (n) => n || "–";
    return cares.map((c, i) => ({
      pagines: [i + 1],
      cara: c,
      llegenda: `Full ${c.full} · ${c.costat === "davant" ? "cara davantera" : "cara del darrere"}: ` +
        `<strong>${num(c.esquerra)} | ${num(c.dreta)}</strong>`,
    }));
  }

  /** Ressalta unes pàgines A5 (per exemple, les de la cançó que s'està editant). */
  marca(pagines) {
    this.marcades = pagines || [];
    this.contenidor.querySelectorAll("canvas").forEach((llenc) => {
      const n = Number(llenc.dataset.pagina);
      llenc.classList.toggle("marcada", this.mode === "dobles" && this.marcades.includes(n));
    });
  }

  /** Fa scroll fins a la doble pàgina que conté la pàgina n. */
  anarAPagina(n, suau = true) {
    if (this.mode !== "dobles") return;
    const figura = [...this.contenidor.querySelectorAll("figure")]
      .find((f) => f.dataset.pagines.split(",").map(Number).includes(n));
    if (!figura) return;
    const pagina = this.desplacament === document.scrollingElement;
    const dalt = pagina ? 0 : this.desplacament.getBoundingClientRect().top;
    const objectiu = figura.getBoundingClientRect().top - dalt + this.desplacament.scrollTop - 8;
    this.desplacament.scrollTo({ top: objectiu, behavior: suau ? "smooth" : "auto" });
  }
}

/**
 * Connecta els controls de zoom d'una barra d'eines amb un visor:
 *   [data-zoom="-1"], [data-zoom="1"], [data-zoom="ajusta"] i un element [data-zoom-valor].
 */
export function connectaZoom(visor, arrel) {
  const valor = arrel.querySelector("[data-zoom-valor]");
  const actualitza = (zoom) => {
    if (valor) valor.textContent = `${Math.round(zoom * 100)} %`;
    arrel.querySelector('[data-zoom="-1"]').disabled = zoom <= NIVELLS_ZOOM[0];
    arrel.querySelector('[data-zoom="1"]').disabled = zoom >= NIVELLS_ZOOM.at(-1);
    arrel.querySelector('[data-zoom="ajusta"]').disabled = zoom === 1;
  };
  const anterior = visor.canviZoom;
  visor.canviZoom = (zoom) => {
    anterior(zoom);
    actualitza(zoom);
  };
  arrel.querySelectorAll("[data-zoom]").forEach((boto) => {
    boto.addEventListener("click", () => {
      if (boto.dataset.zoom === "ajusta") visor.posaZoom(1);
      else visor.passaZoom(Number(boto.dataset.zoom));
    });
  });
  actualitza(visor.zoom);
}

/** Dibuixa pàgines soltes d'un PDF en llenços ja existents (n < 0 compta des del final). */
export async function dibuixaPagines(url, llocs) {
  const document = await pdfjs.getDocument({ url, isEvalSupported: false }).promise;
  const ratio = window.devicePixelRatio || 1;
  try {
    for (const { n, llenc } of llocs) {
      const pagina = await document.getPage(n < 0 ? document.numPages + 1 + n : n);
      const base = pagina.getViewport({ scale: 1 });
      const vista = pagina.getViewport({ scale: (llenc.clientWidth / base.width) * ratio });
      llenc.width = Math.floor(vista.width);
      llenc.height = Math.floor(vista.height);
      await pagina.render({ canvasContext: llenc.getContext("2d"), viewport: vista }).promise;
    }
  } finally {
    document.destroy();
  }
}

/** Capa que mostra el número de cada pàgina a sobre del PDF (no s'imprimeix: és només a la pantalla). */
/** Guia dels marges d'una pàgina A5 (en una part de la imatge: x0 i ample, en fracció de l'amplada). */
function guiaMarges(m, esquerra, x0, ample) {
  const guia = document.createElement("span");
  guia.className = "guia-marges-visor";
  const esq = (esquerra ? m.exterior : m.interior) / 148;
  const dre = (esquerra ? m.interior : m.exterior) / 148;
  Object.assign(guia.style, {
    left: `${(x0 + esq * ample) * 100}%`, right: `${(1 - x0 - ample + dre * ample) * 100}%`,
    top: `${(m.superior / 210) * 100}%`, bottom: `${(m.inferior / 210) * 100}%`,
  });
  return guia;
}

function capaOrdre(caselles, titol = "") {
  const capa = document.createElement("span");
  capa.className = "capa-ordre";
  capa.setAttribute("aria-hidden", "true");
  if (titol) {
    const t = document.createElement("span");
    t.className = "titol-ordre";
    t.textContent = titol;
    capa.append(t);
  }
  for (const { numero, text } of caselles) {
    const casella = document.createElement("span");
    casella.className = "casella-ordre";
    const n = document.createElement("span");
    n.className = "numero-ordre";
    n.textContent = numero;
    const t = document.createElement("span");
    t.className = "text-ordre";
    t.textContent = text;
    casella.append(n, t);
    capa.append(casella);
  }
  return capa;
}

function escapa(text) {
  return text.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
}
