// Editor de pàgines del cançoner. Les pàgines es dibuixen amb el mateix motor que la pàgina
// d'impressió que Gotenberg converteix en PDF: el que es veu aquí és exactament el que s'imprimeix.
import {
  ALT, AMPLE, FONTS, QR_MINIM, acordsDePagines, acordsDelDocument, ajustaMarcs, aplicaEstils, dibuixaElement,
  colorCss, dibuixaPagina, esAcord, esperaFonts, posaAcord, posaMida, registraFonts, reposiciona, transportaPagines, treuAcord,
} from "./dist/canconer.js";
import { selectorColor } from "./selector-color.js";

const dades = JSON.parse(document.getElementById("dades-editor").textContent);
const urls = dades.urls;
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const PX_MM = 96 / 25.4; // píxels CSS per mil·límetre a escala 1
const MARGE = 13;
const TOLERANCIA = 1.6;
const ACORDS_COMUNS = ["C", "D", "E", "F", "G", "A", "B", "Am", "Bm", "Dm", "Em", "F#m", "C7", "D7", "E7", "G7", "A7", "B7", "Cmaj7", "Fmaj7", "Dsus4", "Asus4"];

// ------------------------------------------------------------ Estat

let K = null; // cançoner (meta + entrades)
let PLA = null; // pla del llibret (números de pàgina, índex, diagrames)
let obert = null; // {tipus: "canco"|"especial"|"mestra"|"llibre", id}
let pagines = []; // pàgines que s'editen (models)
let canco = null; // esborrany de la cançó oberta {id, titol, autor, contingut}
let editable = true;
let seleccio = null; // {p: índex de pàgina, id: element principal, ids: tots els seleccionats}
let zoom = 1; // 1 = ajustat a la finestra
let escala = 1; // escala real aplicada a les pàgines
let edicio = null; // edició de text en curs: {tipus: "lletra"|"text", p, id, node, editor}
let TIPOGRAFIES = dades.fonts; // [{clau, nom, categoria, css}]
registraFonts(TIPOGRAFIES);

const llenc = $("#llenc");
const entradaActual = () => (obert?.tipus === "canco" ? K.cancons.find((c) => c.id === obert.id) : null);
const transport = () => Number(entradaActual()?.transport || 0);
const elementDe = (p, id) => pagines[p]?.elements.find((e) => e.id === id);
const idsSel = () => (seleccio ? (seleccio.ids ?? (seleccio.id ? [seleccio.id] : [])) : []);
const elementsSel = () => idsSel().map((id) => elementDe(seleccio.p, id)).filter(Boolean);
const elementSel = () => (idsSel().length === 1 ? elementDe(seleccio.p, idsSel()[0]) : null);
const nouId = () => Math.random().toString(36).slice(2, 10);
const arrodoneix = (v) => Math.round(v * 10) / 10;
const copia = (v) => structuredClone(v);

function el(etiqueta, { text = "", classe = "", atributs = {} } = {}) {
  const e = document.createElement(etiqueta);
  if (text) e.textContent = text;
  if (classe) e.className = classe;
  for (const [k, v] of Object.entries(atributs)) e.setAttribute(k, v);
  return e;
}

async function api(url, metode = "GET", cos = undefined) {
  const opcions = { method: metode, headers: {} };
  if (cos instanceof FormData) opcions.body = cos;
  else if (cos !== undefined) {
    opcions.headers["Content-Type"] = "application/json";
    opcions.body = JSON.stringify(cos);
  }
  const r = await fetch(url, opcions);
  if (!r.ok) {
    let missatge = `${r.status} ${r.statusText}`;
    try { missatge = (await r.json()).error || missatge; } catch { /* sense cos JSON */ }
    throw new Error(missatge);
  }
  return r.json();
}

function mostraEstat(text, tipus = "ok") {
  $("#text-estat").textContent = text;
  $("#estat").dataset.tipus = tipus;
}

// ------------------------------------------------------------ Desat

let pendent = false;
let temporitzador = null;

function canviat({ refesLlenc = false } = {}) {
  if (!editable) return;
  pendent = true;
  mostraEstat("Canvis sense desar", "treballant");
  clearTimeout(temporitzador);
  temporitzador = setTimeout(desa, 700);
  if (refesLlenc) pintaLlenc();
}

async function desa() {
  clearTimeout(temporitzador);
  if (!pendent || !obert) return;
  pendent = false;
  mostraEstat("Desant…", "treballant");
  try {
    if (obert.tipus === "canco" && canco) {
      await api(urls.canco + canco.id, "PUT", { titol: canco.titol, autor: canco.autor, contingut: { format: 2, pagines, videos: videosCanco() } });
    } else if (obert.tipus === "especial") {
      await api(urls.disseny, "PUT", { especials: { [obert.id]: pagines[0] } });
    } else if (obert.tipus === "mestra") {
      await api(urls.disseny, "PUT", { mestres: K.mestres });
    }
  } catch (e) {
    pendent = true;
    mostraEstat("No s'ha pogut desar: " + e.message, "error");
    return;
  }
  mostraEstat("Tot desat");
  refrescaPla();
}

let temporitzadorPla = null;
function refrescaPla() {
  clearTimeout(temporitzadorPla);
  temporitzadorPla = setTimeout(async () => {
    [K, PLA] = await Promise.all([api(urls.canconer), api(urls.pla)]);
    pintaLlista();
    if (obert?.tipus === "llibre") pintaLlenc();
    $("#total-pagines").textContent = `${PLA.total} pàg.`;
  }, 400);
}

let temporitzadorEstils = null;
function desaEstils() {
  mostraEstat("Canvis sense desar", "treballant");
  clearTimeout(temporitzadorEstils);
  temporitzadorEstils = setTimeout(async () => {
    try {
      await api(urls.disseny, "PUT", { estils: K.estils });
      mostraEstat("Tot desat");
      refrescaPla();
    } catch (e) {
      mostraEstat("No s'han pogut desar els estils", "error");
    }
  }, 600);
}

window.addEventListener("beforeunload", (e) => {
  if (pendent) {
    desa();
    e.preventDefault();
  }
});

// ------------------------------------------------------------ Desfer i refer

const historia = new Map(); // clau de l'element obert → {enrere, endavant}
let ultimaFoto = 0;
const clauObert = () => `${obert?.tipus}:${obert?.id}`;
const pilaActual = () => {
  if (!historia.has(clauObert())) historia.set(clauObert(), { enrere: [], endavant: [] });
  return historia.get(clauObert());
};

function foto(forca = false) {
  if (!editable) return;
  const ara = Date.now();
  if (!forca && ara - ultimaFoto < 600) return;
  ultimaFoto = ara;
  const pila = pilaActual();
  pila.enrere.push(JSON.stringify(pagines));
  if (pila.enrere.length > 80) pila.enrere.shift();
  pila.endavant = [];
}

function desfes(enrere = true) {
  if (!editable) return;
  const pila = pilaActual();
  const origen = enrere ? pila.enrere : pila.endavant;
  if (!origen.length) return;
  (enrere ? pila.endavant : pila.enrere).push(JSON.stringify(pagines));
  substitueixPagines(JSON.parse(origen.pop()));
  seleccio = null;
  canviat({ refesLlenc: true });
}

/** Canvia el contingut de les pàgines mantenint les referències del model obert. */
function substitueixPagines(noves) {
  pagines.splice(0, pagines.length, ...noves);
  if (obert?.tipus === "especial") K.especials[obert.id] = pagines[0];
  if (obert?.tipus === "mestra") {
    const m = K.mestres.find((x) => x.id === obert.id);
    m.parell = pagines[0];
    m.senar = pagines[1];
  }
}

// ------------------------------------------------------------ Dades per dibuixar

/** Números de pàgina del que hi ha obert (per saber si cada pàgina és esquerra o dreta). */
function numerosPagina() {
  if (obert.tipus === "mestra") return [2, 3];
  if (obert.tipus === "especial") {
    const p = PLA.pagines.find((x) => x.tipus === obert.id);
    return [p?.numero ?? (obert.id === "portada" ? 1 : 2)];
  }
  const propies = PLA.pagines.filter((p) => p.entrada === obert.id).map((p) => p.numero);
  const inici = propies[0] ?? 2; // si no surt al PDF, es mostra com si comencés a l'esquerra
  return pagines.map((_, i) => propies[i] ?? inici + i);
}

/** Costat de la mestra: el forçat a la pàgina ("esquerra"/"dreta") o, si no, el de la paritat. */
function mestraDe(idMestra, numero, costat) {
  const m = K.mestres.find((x) => x.id === idMestra);
  const esquerra = costat === "esquerra" || costat === "dreta" ? costat === "esquerra" : numero % 2 === 0;
  return m ? m[esquerra ? "parell" : "senar"] : null;
}

function contextDe(numero) {
  const base = { titol: K.titol, subtitol: K.subtitol, any: K.any, contraportada: K.contraportada, pagina: numero };
  if (obert.tipus === "canco" && canco) {
    const acords = acordsDePagines(transportaPagines(pagines, transport()));
    return { ...base, titol: canco.titol, autor: canco.autor, acords: acords.join(" · "), videos: videosPerDibuixar() };
  }
  if (obert.tipus === "mestra") return { ...base, titol: "Títol de la cançó", autor: "Autor", acords: "C · G · Am · F" };
  return base;
}

function dadesPagina(i, numero) {
  const model = pagines[i];
  const deLlibre = obert.tipus === "especial" ? PLA.pagines.find((x) => x.tipus === obert.id) : null;
  const visibles = obert.tipus === "canco" ? transportaPagines([model], transport())[0] : model;
  return {
    fons: model.fons,
    elements: visibles.elements,
    mestra: obert.tipus === "mestra" ? null : mestraDe(model.mestra, numero, model.costat),
    context: contextDe(numero),
    index: deLlibre?.index,
    diagrames: deLlibre?.diagrames,
    qrs: deLlibre?.qrs,
  };
}

// ------------------------------------------------------------ Dibuix del llenç

function calculaEscala() {
  const amplada = llenc.clientWidth - 88;
  const alcada = llenc.clientHeight - 80;
  const doble = obert?.tipus !== "especial" || false;
  const ajust = Math.min(amplada / ((doble ? 2 : 1) * AMPLE * PX_MM), alcada / (ALT * PX_MM));
  escala = Math.max(0.25, ajust * zoom);
  $("[data-zoom-valor]").textContent = `${Math.round(zoom * 100)} %`;
}

function opcionsDibuix() {
  return {
    urlImatge: (id) => urls.imatge + id,
    converteix: async (text) => (await api(urls.converteix, "POST", { text })).doc,
    editaAcord: ({ pos, nom, element }) => obrePopoverAcord(pos, nom, element.getBoundingClientRect()),
    grup: "obert",
  };
}

/** Zona de seguretat de la mestra de marges triada a «Imprimir» (no s'imprimeix). */
function guiaMarges(numero) {
  const m = dades.marge;
  if (!m) return "";
  const esquerra = numero % 2 === 0; // a l'esquerra, el plec és a la dreta
  const guia = el("div", { classe: "guia-marges", atributs: {
    title: `Marges «${m.nom}»: en imprimir, la pàgina es redueix al ${Math.round(m.escala * 1000) / 10} % per deixar ${m.interior} mm al plec. Deixa el contingut important dins de la línia.` } });
  const mm = (v) => `${v * PX_MM * escala}px`;
  Object.assign(guia.style, {
    top: mm(m.superior), bottom: mm(m.inferior),
    left: mm(esquerra ? m.exterior : m.interior), right: mm(esquerra ? m.interior : m.exterior),
  });
  return guia;
}

/** Embolcall d'una pàgina: la pàgina real (en mm, escalada) + la capa de selecció (en píxels). */
function embolcall(i, numero) {
  const caixa = el("div", { classe: "pagina-editor", atributs: { "data-pagina": i } });
  caixa.style.width = `${AMPLE * PX_MM * escala}px`;
  caixa.style.height = `${ALT * PX_MM * escala}px`;
  const pagina = dibuixaPagina(dadesPagina(i, numero), opcionsDibuix());
  pagina.style.transform = `scale(${escala})`;
  pagina.style.transformOrigin = "0 0";
  const capa = el("div", { classe: "capa-seleccio" });
  caixa.append(pagina, guiaMarges(numero), capa);
  const peu = el("div", { classe: "peu-pagina-editor", text: obert.tipus === "mestra" ? (numero % 2 === 0 ? "Pàgines parells (esquerra)" : "Pàgines senars (dreta)") : `Pàgina ${numero}` });
  const columna = el("div", { classe: "flex flex-col items-center gap-2" });
  columna.append(caixa, peu);
  return columna;
}

async function pintaLlenc() {
  if (!obert) return;
  if (obert.tipus === "llibre") return pintaLlibre();
  sortEdicio();
  calculaEscala();
  const numeros = numerosPagina();
  // Dobles pàgines com al llibret obert: la parella (2k, 2k+1).
  const dobles = new Map();
  numeros.forEach((n, i) => {
    const clau = Math.floor(n / 2);
    if (!dobles.has(clau)) dobles.set(clau, [null, null]);
    dobles.get(clau)[n % 2 === 0 ? 0 : 1] = { i, n };
  });
  const files = [...dobles.values()].map(([esquerra, dreta]) => {
    const fila = el("div", { classe: "doble-editor" });
    for (const costat of [esquerra, dreta]) {
      if (costat) fila.append(embolcall(costat.i, costat.n));
      else {
        const buit = el("div", { classe: "pagina-buida" });
        buit.style.width = `${AMPLE * PX_MM * escala}px`;
        fila.append(buit);
      }
    }
    return fila;
  });
  const contenidor = el("div", { classe: "contingut-llenc" });
  contenidor.append(...files);
  llenc.replaceChildren(contenidor);
  await esperaFonts();
  ajustaMarcs(llenc, (id) => pagines.flatMap((p) => p.elements).find((e) => e.id === id));
  pintaSeleccio();
  pintaPropietats();
  pintaAvisLlenc();
}

/** Vista de tot el llibret (només lectura): clica una pàgina per obrir-la. */
async function pintaLlibre() {
  sortEdicio();
  calculaEscala();
  // Graella de miniatures: unes tres dobles pàgines per fila a zoom 100 %.
  const mida = Math.max(0.12, Math.min(0.6, ((llenc.clientWidth - 160) / (3 * 2 * AMPLE * PX_MM)) * zoom));
  const dobles = [];
  for (let i = 0; i < PLA.pagines.length; i++) {
    const p = PLA.pagines[i];
    const clau = Math.floor(p.numero / 2);
    dobles[clau] ??= [null, null];
    dobles[clau][p.numero % 2 === 0 ? 0 : 1] = p;
  }
  const contenidor = el("div", { classe: "contingut-llenc vista-llibre" });
  for (const doble of dobles.filter(Boolean)) {
    const fila = el("div", { classe: "doble-editor" });
    for (const p of doble) {
      const caixa = el("div", { classe: p ? "pagina-editor clicable" : "pagina-buida" });
      caixa.style.width = `${AMPLE * PX_MM * mida}px`;
      caixa.style.height = `${ALT * PX_MM * mida}px`;
      if (p) {
        const pagina = dibuixaPagina(p, { ...opcionsDibuix(), grup: p.entrada });
        pagina.style.transform = `scale(${mida})`;
        pagina.style.transformOrigin = "0 0";
        caixa.append(pagina);
        caixa.title = `Pàgina ${p.numero}`;
        caixa.addEventListener("click", () => {
          if (p.entrada) obre({ tipus: "canco", id: p.entrada });
          else if (["portada", "index", "acords", "index_qr", "contraportada"].includes(p.tipus)) obre({ tipus: "especial", id: p.tipus });
        });
      }
      const columna = el("div", { classe: "flex flex-col items-center gap-1" });
      columna.append(caixa, el("div", { classe: "peu-pagina-editor", text: p ? String(p.numero) : "" }));
      fila.append(columna);
    }
    contenidor.append(fila);
  }
  llenc.replaceChildren(contenidor);
  await esperaFonts();
  const perId = new Map(PLA.pagines.flatMap((p) => p.elements || []).map((e) => [e.id, e]));
  ajustaMarcs(llenc, (id) => perId.get(id));
  pintaPropietats();
  pintaAvisLlenc();
}

function nodeElement(p, id) {
  return llenc.querySelector(`.pagina-editor[data-pagina="${p}"] .capa-elements [data-id="${id}"]`);
}

/** Torna a dibuixar una sola pàgina (després de canviar-ne un element). */
async function repintaPagina(p) {
  const caixa = llenc.querySelector(`.pagina-editor[data-pagina="${p}"]`);
  if (!caixa) return pintaLlenc();
  const numero = numerosPagina()[p];
  const pagina = dibuixaPagina(dadesPagina(p, numero), opcionsDibuix());
  pagina.style.transform = `scale(${escala})`;
  pagina.style.transformOrigin = "0 0";
  caixa.querySelector(".pagina").replaceWith(pagina);
  await esperaFonts();
  reajusta();
  pintaSeleccio();
}

function reajusta() {
  ajustaMarcs(llenc, (id) => pagines.flatMap((p) => p.elements).find((e) => e.id === id));
  if (seleccio) pintaInfoMarc();
  pintaMidaMarc();
}

// ------------------------------------------------------------ Selecció
// La selecció pot tenir diversos elements (seleccio.ids). Els elements amb el mateix camp «grup»
// es seleccionen junts; amb doble clic s'entra dins del grup per tocar-ne un de sol.

/** Requadre que envolta uns elements, tenint en compte la rotació de cadascun. */
function cantonades(e) {
  const cx = e.x + e.w / 2;
  const cy = e.y + e.h / 2;
  const a = ((e.rotacio || 0) * Math.PI) / 180;
  const [c, s] = [Math.cos(a), Math.sin(a)];
  return [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([dx, dy]) => {
    const x = (dx * e.w) / 2;
    const y = (dy * e.h) / 2;
    return [cx + x * c - y * s, cy + x * s + y * c];
  });
}

function requadre(elements) {
  const punts = elements.flatMap(cantonades);
  const xs = punts.map((q) => q[0]);
  const ys = punts.map((q) => q[1]);
  const x = Math.min(...xs);
  const y = Math.min(...ys);
  return { x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y };
}

function idsGrup(p, id) {
  const e = elementDe(p, id);
  if (!e?.grup) return [id];
  return pagines[p].elements.filter((x) => x.grup === e.grup).map((x) => x.id);
}

function nanses(marc) {
  for (const n of ["nw", "n", "ne", "e", "se", "s", "sw", "w"]) marc.append(el("span", { classe: `nansa-disseny nansa-${n}`, atributs: { "data-nansa": n } }));
  marc.append(el("span", { classe: "nansa-rotacio", atributs: { "data-nansa": "rotacio", title: "Arrossega per girar (⇧: de 15° en 15°)" } }));
}

function pintaSeleccio() {
  $$(".capa-seleccio").forEach((c) => c.replaceChildren());
  const elements = elementsSel();
  if (!elements.length || obert?.tipus === "llibre") return;
  const capa = llenc.querySelector(`.pagina-editor[data-pagina="${seleccio.p}"] .capa-seleccio`);
  if (!capa) return;
  const k = PX_MM * escala;
  const posa = (node, r, rotacio = 0) => Object.assign(node.style, {
    left: `${r.x * k - 1}px`, top: `${r.y * k - 1}px`, width: `${r.w * k + 2}px`, height: `${r.h * k + 2}px`,
    transform: rotacio ? `rotate(${rotacio}deg)` : "",
  });
  if (elements.length === 1) {
    const e = elements[0];
    const marc = el("div", { classe: "marc-seleccio" + (edicio ? " editant" : "") });
    posa(marc, e, e.rotacio);
    if (!edicio && editable) nanses(marc);
    capa.append(marc);
    return;
  }
  // Diversos elements: el contorn de cadascun i un marc comú amb nanses.
  for (const e of elements) {
    const contorn = el("div", { classe: "contorn-seleccio" });
    posa(contorn, e, e.rotacio);
    capa.append(contorn);
  }
  const marc = el("div", { classe: "marc-seleccio multiple" });
  posa(marc, requadre(elements));
  if (editable) nanses(marc);
  capa.append(marc);
}

/**
 * Selecciona un element (i el seu grup).
 *   afegeix: ⇧ + clic, afegeix o treu de la selecció actual
 *   sol: només aquest element, encara que sigui d'un grup (doble clic, capes)
 */
function selecciona(p, id, { afegeix = false, sol = false } = {}) {
  if (edicio && !(edicio.p === p && edicio.id === id)) sortEdicio();
  if (p === null) seleccio = null;
  else if (!id) seleccio = { p, id: null, ids: [] };
  else {
    const nous = sol ? [id] : idsGrup(p, id);
    const actuals = seleccio?.p === p ? idsSel() : [];
    if (afegeix && actuals.length) {
      const ja = nous.every((x) => actuals.includes(x));
      const ids = ja ? actuals.filter((x) => !nous.includes(x)) : [...new Set([...actuals, ...nous])];
      seleccio = { p, id: ids.includes(id) ? id : (ids[0] ?? null), ids };
    } else seleccio = { p, id, ids: nous };
  }
  pintaSeleccio();
  pintaPropietats();
}

function seleccionaMolts(p, ids, afegeix = false) {
  const actuals = afegeix && seleccio?.p === p ? idsSel() : [];
  const tots = [...new Set([...actuals, ...ids.flatMap((id) => idsGrup(p, id))])];
  seleccio = { p, id: tots[0] ?? null, ids: tots };
  pintaSeleccio();
  pintaPropietats();
}

// ------------------------------------------------------------ Arrossegar, canviar la mida i girar

let gest = null;

function puntMm(ev, caixa) {
  const r = caixa.getBoundingClientRect();
  const k = PX_MM * escala;
  return { x: (ev.clientX - r.left) / k, y: (ev.clientY - r.top) / k };
}

function guies(p, exclou) {
  const xs = [0, MARGE, AMPLE / 2, AMPLE - MARGE, AMPLE];
  const ys = [0, MARGE, ALT / 2, ALT - MARGE, ALT];
  for (const e of pagines[p].elements) {
    if (exclou.includes(e.id)) continue;
    xs.push(e.x, e.x + e.w / 2, e.x + e.w);
    ys.push(e.y, e.y + e.h / 2, e.y + e.h);
  }
  return { xs, ys };
}

function enganxa(valors, candidates) {
  let millor = null;
  for (const v of valors) for (const c of candidates) {
    const d = c - v;
    if (Math.abs(d) <= TOLERANCIA && (!millor || Math.abs(d) < Math.abs(millor.d))) millor = { d, linia: c };
  }
  return millor;
}

function pintaGuies(p, lx, ly) {
  const capa = llenc.querySelector(`.pagina-editor[data-pagina="${p}"] .capa-seleccio`);
  capa?.querySelectorAll(".guia").forEach((g) => g.remove());
  const k = PX_MM * escala;
  for (const x of lx) {
    const g = el("span", { classe: "guia absolute inset-y-0 w-px bg-sky-500" });
    g.style.left = `${x * k}px`;
    capa?.append(g);
  }
  for (const y of ly) {
    const g = el("span", { classe: "guia absolute inset-x-0 h-px bg-sky-500" });
    g.style.top = `${y * k}px`;
    capa?.append(g);
  }
}

/** Mida de lletra d'un element (la seva o la de l'estil). */
function midaDe(e) {
  const defecte = { text: "text", lletra: "lletra", numero: "numero", index: "index" }[e.tipus];
  return Number(e.format?.mida ?? K.estils[e.estil || defecte]?.mida ?? 10);
}

/** En escalar un grup, els textos també es fan més grans o més petits. */
function escalaLletra(e, original, factor) {
  if (!["text", "lletra", "numero", "index"].includes(e.tipus)) return;
  const mida = Math.max(3, Math.round(midaDe(original) * factor * 10) / 10);
  e.format = { ...(original.format || {}), mida };
  const node = nodeElement(gest.p, e.id);
  if (node) node.style.fontSize = `calc(${mida}pt * var(--escala, 1))`;
}

llenc.addEventListener("pointerdown", (ev) => {
  if (obert?.tipus === "llibre" || ev.button !== 0) return;
  const caixa = ev.target.closest(".pagina-editor");
  if (!caixa) {
    if (!ev.target.closest("#popover-acord")) { sortEdicio(); selecciona(null, null); }
    return;
  }
  const p = Number(caixa.dataset.pagina);
  if (ev.target.closest(".editant, [contenteditable='true'], [contenteditable='plaintext-only']")) return; // s'està escrivint
  const nansa = ev.target.closest("[data-nansa]");
  let node = ev.target.closest(".capa-elements [data-id]");
  let sol = false;
  if (ev.altKey && !nansa) {
    // ⌥ + clic: va seleccionant els elements que hi ha sota el punt, d'un en un (també els bloquejats).
    const pt = puntMm(ev, caixa);
    const sota = pagines[p].elements.filter((e) => pt.x >= e.x && pt.x <= e.x + e.w && pt.y >= e.y && pt.y <= e.y + e.h).reverse();
    if (sota.length) {
      const i = sota.findIndex((e) => e.id === seleccio?.id);
      node = nodeElement(p, sota[(i + 1) % sota.length].id);
      sol = true;
    }
  }
  if (!nansa && !node) {
    // Clic en una zona buida: comença un rectangle de selecció.
    sortEdicio();
    if (!ev.shiftKey) selecciona(p, null);
    gest = { p, caixa, tipus: "rectangle", inici: puntMm(ev, caixa), afegeix: ev.shiftKey, mogut: false };
    llenc.setPointerCapture(ev.pointerId);
    ev.preventDefault();
    return;
  }
  if (node) {
    const id = node.dataset.id;
    const jaSeleccionat = seleccio?.p === p && idsSel().includes(id);
    if (ev.shiftKey) selecciona(p, id, { afegeix: true });
    else if (!jaSeleccionat || sol) selecciona(p, id, { sol });
    if (!idsSel().includes(id)) return; // l'ha tret de la selecció: no s'arrossega
  }
  if (!editable) return;
  const originals = elementsSel().map(copia);
  if (!originals.length) return;
  foto(true);
  const tipus = nansa?.dataset.nansa === "rotacio" ? "rota" : nansa ? "mida" : "mou";
  gest = { p, caixa, tipus, nansa: nansa?.dataset.nansa, inici: puntMm(ev, caixa), originals, requadre: requadre(originals), mogut: false };
  llenc.setPointerCapture(ev.pointerId);
  ev.preventDefault();
});

llenc.addEventListener("pointermove", (ev) => {
  if (!gest) return;
  const pt = puntMm(ev, gest.caixa);
  const dx = pt.x - gest.inici.x;
  const dy = pt.y - gest.inici.y;
  if (!gest.mogut && Math.hypot(dx, dy) < 0.4) return;
  gest.mogut = true;

  if (gest.tipus === "rectangle") {
    const r = { x: Math.min(pt.x, gest.inici.x), y: Math.min(pt.y, gest.inici.y), w: Math.abs(dx), h: Math.abs(dy) };
    const capa = llenc.querySelector(`.pagina-editor[data-pagina="${gest.p}"] .capa-seleccio`);
    let rect = capa.querySelector(".rectangle-seleccio");
    if (!rect) capa.append(rect = el("div", { classe: "rectangle-seleccio" }));
    const k = PX_MM * escala;
    Object.assign(rect.style, { left: `${r.x * k}px`, top: `${r.y * k}px`, width: `${r.w * k}px`, height: `${r.h * k}px` });
    gest.rect = r;
    return;
  }

  const ids = gest.originals.map((o) => o.id);
  const elements = ids.map((id) => elementDe(gest.p, id));
  const b = gest.requadre;
  const ambGuies = !ev.altKey;
  const { xs, ys } = guies(gest.p, ids);
  let lx = [];
  let ly = [];

  if (gest.tipus === "rota") {
    // Angle entre el centre (de l'element o del grup) i el punter; la nansa és a dalt (0°).
    const cx = b.x + b.w / 2;
    const cy = b.y + b.h / 2;
    const angle = (p) => (Math.atan2(p.y - cy, p.x - cx) * 180) / Math.PI;
    let delta = elements.length === 1 ? angle(pt) + 90 - (gest.originals[0].rotacio || 0) : angle(pt) - angle(gest.inici);
    const final = (o) => ((Math.round((o.rotacio || 0) + delta) % 360) + 540) % 360 - 180;
    if (ev.shiftKey) delta = Math.round(delta / 15) * 15;
    else if (elements.length === 1) {
      const g = final(gest.originals[0]);
      if (Math.abs(g - Math.round(g / 90) * 90) <= 3) delta += Math.round(g / 90) * 90 - g; // s'enganxa a 0/90/180
    }
    const rad = (delta * Math.PI) / 180;
    gest.originals.forEach((o, i) => {
      const e = elements[i];
      const ox = o.x + o.w / 2 - cx;
      const oy = o.y + o.h / 2 - cy;
      e.x = arrodoneix(cx + ox * Math.cos(rad) - oy * Math.sin(rad) - o.w / 2);
      e.y = arrodoneix(cy + ox * Math.sin(rad) + oy * Math.cos(rad) - o.h / 2);
      e.rotacio = final(o);
    });
  } else if (gest.tipus === "mou") {
    // Si el punter és sobre una altra pàgina, els elements s'hi mouran en deixar-los anar (#6).
    const desti = paginaSota(ev);
    if (desti !== null && desti !== gest.p) return arrossegaAPagina(ev, desti);
    treuFantasma(gest);
    let mx = dx;
    let my = dy;
    if (ambGuies) {
      const gx = enganxa([b.x + dx, b.x + dx + b.w / 2, b.x + dx + b.w], xs);
      const gy = enganxa([b.y + dy, b.y + dy + b.h / 2, b.y + dy + b.h], ys);
      if (gx) { mx += gx.d; lx = [gx.linia]; }
      if (gy) { my += gy.d; ly = [gy.linia]; }
    }
    gest.originals.forEach((o, i) => {
      elements[i].x = arrodoneix(o.x + mx);
      elements[i].y = arrodoneix(o.y + my);
    });
  } else {
    // Canvi de mida sobre el requadre (d'un element o del grup sencer).
    const n = gest.nansa;
    const sol = elements.length === 1;
    const o0 = sol ? gest.originals[0] : b;
    let { x, y, w, h } = o0;
    if (n.includes("e")) w = o0.w + dx;
    if (n.includes("s")) h = o0.h + dy;
    if (n.includes("w")) { w = o0.w - dx; x = o0.x + dx; }
    if (n.includes("n")) { h = o0.h - dy; y = o0.y + dy; }
    const cantonada = n.length === 2;
    const proporcio = cantonada && (ev.shiftKey || !sol || elements[0].tipus === "imatge");
    if (proporcio) {
      h = w * (o0.h / o0.w);
      if (n.includes("n")) y = o0.y + o0.h - h;
    } else if (ambGuies) {
      if (n.includes("e")) { const g = enganxa([x + w], xs); if (g) { w += g.d; lx = [g.linia]; } }
      if (n.includes("w")) { const g = enganxa([x], xs); if (g) { x += g.d; w -= g.d; lx = [g.linia]; } }
      if (n.includes("s")) { const g = enganxa([y + h], ys); if (g) { h += g.d; ly = [g.linia]; } }
      if (n.includes("n")) { const g = enganxa([y], ys); if (g) { y += g.d; h -= g.d; ly = [g.linia]; } }
    }
    w = Math.max(2, w);
    h = Math.max(2, h);
    if (sol) Object.assign(elements[0], { x: arrodoneix(x), y: arrodoneix(y), w: arrodoneix(w), h: arrodoneix(h) });
    else {
      const sx = w / b.w;
      const sy = h / b.h;
      gest.originals.forEach((o, i) => {
        const e = elements[i];
        Object.assign(e, {
          x: arrodoneix(x + (o.x - b.x) * sx), y: arrodoneix(y + (o.y - b.y) * sy),
          w: arrodoneix(Math.max(1, o.w * sx)), h: arrodoneix(Math.max(1, o.h * sy)),
        });
        if (proporcio) escalaLletra(e, o, sx);
      });
    }
  }
  for (const e of elements) {
    const node = nodeElement(gest.p, e.id);
    if (node) reposiciona(node, e);
  }
  pintaSeleccio();
  pintaGuies(gest.p, lx, ly);
  pintaPropietatsPosicio();
});

// ------------------------------------------------------------ Moure elements a una altra pàgina

/** Índex de la pàgina que hi ha sota el punter (o null). */
function paginaSota(ev) {
  for (const caixa of llenc.querySelectorAll(".pagina-editor[data-pagina]")) {
    const r = caixa.getBoundingClientRect();
    if (ev.clientX >= r.left && ev.clientX <= r.right && ev.clientY >= r.top && ev.clientY <= r.bottom) return Number(caixa.dataset.pagina);
  }
  return null;
}

const caixaPagina = (p) => llenc.querySelector(`.pagina-editor[data-pagina="${p}"]`);

/** Mentre s'arrossega sobre una altra pàgina: fantasma dels elements a la pàgina de destí. */
function arrossegaAPagina(ev, desti) {
  const g = gest;
  const caixa = caixaPagina(desti);
  const pt = puntMm(ev, caixa);
  const mobils = g.originals.filter((o) => !o.bloquejat); // els bloquejats no canvien de pàgina
  let mx = pt.x - g.inici.x;
  let my = pt.y - g.inici.y;
  let lx = [];
  let ly = [];
  if (!ev.altKey && mobils.length) {
    const b = requadre(mobils);
    const { xs, ys } = guies(desti, []);
    const gx = enganxa([b.x + mx, b.x + mx + b.w / 2, b.x + mx + b.w], xs);
    const gy = enganxa([b.y + my, b.y + my + b.h / 2, b.y + my + b.h], ys);
    if (gx) { mx += gx.d; lx = [gx.linia]; }
    if (gy) { my += gy.d; ly = [gy.linia]; }
  }
  if (g.desti?.p !== desti) {
    treuFantasma(g);
    // A l'origen, els elements tornen al lloc i es veuen esvaïts.
    for (const o of g.originals) {
      const e = elementDe(g.p, o.id);
      Object.assign(e, { x: o.x, y: o.y });
      const node = nodeElement(g.p, o.id);
      if (node) { reposiciona(node, e); node.classList.add("origen-arrossegat"); }
    }
    caixa.classList.add("desti-arrossegament");
    const capa = caixa.querySelector(".pagina .capa-elements");
    g.fantasmes = mobils.map((o) => {
      const clon = nodeElement(g.p, o.id)?.cloneNode(true);
      if (!clon) return null;
      clon.removeAttribute("data-id");
      clon.classList.remove("origen-arrossegat", "ressaltat");
      clon.classList.add("fantasma-arrossegament");
      capa.append(clon);
      return clon;
    });
    $$(".capa-seleccio").forEach((c) => c.replaceChildren());
  }
  mobils.forEach((o, i) => { if (g.fantasmes[i]) reposiciona(g.fantasmes[i], { ...o, x: o.x + mx, y: o.y + my }); });
  g.desti = { p: desti, mx, my, copia: ev.altKey };
  pintaGuies(desti, lx, ly);
}

function treuFantasma(g) {
  if (!g?.desti) return;
  g.fantasmes?.forEach((f) => f?.remove());
  g.fantasmes = null;
  caixaPagina(g.desti.p)?.classList.remove("desti-arrossegament");
  pintaGuies(g.desti.p, [], []);
  for (const o of g.originals) nodeElement(g.p, o.id)?.classList.remove("origen-arrossegat");
  g.desti = null;
}

/** Passa els elements seleccionats d'una pàgina a una altra (o els hi copia), amb els desplaçaments donats. */
function passaAPagina(origen, desti, originals, { mx = 0, my = 0, copia: copiar = false } = {}) {
  const mobils = originals.filter((o) => !o.bloquejat);
  if (!mobils.length || !pagines[desti]) return false;
  const ids = mobils.map((o) => o.id);
  const nous = copiar ? clona(mobils.map((o) => elementDe(origen, o.id)), 0) : ids.map((id) => elementDe(origen, id));
  if (!copiar) pagines[origen].elements = pagines[origen].elements.filter((e) => !ids.includes(e.id));
  nous.forEach((e, i) => {
    e.x = arrodoneix(mobils[i].x + mx);
    e.y = arrodoneix(mobils[i].y + my);
    pagines[desti].elements.push(e);
  });
  seleccio = { p: desti, id: nous[0].id, ids: nous.map((e) => e.id) };
  canviat();
  repintaPagina(origen).then(() => repintaPagina(desti)).then(() => { pintaSeleccio(); pintaPropietats(); });
  return true;
}

function acabaGest() {
  if (!gest) return;
  const g = gest;
  gest = null;
  if (g.tipus === "mou" && g.desti) {
    const { p: desti, mx, my, copia: copiar } = g.desti;
    treuFantasma(g);
    if (!passaAPagina(g.p, desti, g.originals, { mx, my, copia: copiar })) pintaSeleccio();
    return;
  }
  if (g.tipus === "rectangle") {
    llenc.querySelector(".rectangle-seleccio")?.remove();
    if (!g.mogut || !g.rect) return;
    // Elements que toquen el rectangle (els bloquejats no).
    const r = g.rect;
    const dins = pagines[g.p].elements.filter((e) => {
      if (e.bloquejat) return false;
      const q = requadre([e]);
      return q.x < r.x + r.w && q.x + q.w > r.x && q.y < r.y + r.h && q.y + q.h > r.y;
    });
    seleccionaMolts(g.p, dins.map((e) => e.id), g.afegeix);
    return;
  }
  pintaGuies(g.p, [], []);
  if (!g.mogut) {
    pilaActual().enrere.pop(); // un clic no és un canvi
    return;
  }
  if (g.tipus === "rota") pintaPropietats();
  if (g.tipus === "mida") reajusta();
  canviat();
}
llenc.addEventListener("pointerup", acabaGest);
llenc.addEventListener("pointercancel", acabaGest);

llenc.addEventListener("dblclick", (ev) => {
  if (!editable || obert?.tipus === "llibre") return;
  const caixa = ev.target.closest(".pagina-editor");
  const node = ev.target.closest(".capa-elements [data-id]");
  if (!caixa || !node) return;
  const p = Number(caixa.dataset.pagina);
  const e = elementDe(p, node.dataset.id);
  if (edicio && edicio.id === e?.id) return; // dins del marc que s'edita, el doble clic selecciona la paraula
  if (e?.tipus === "lletra") editaLletra(p, e.id);
  else if (e?.tipus === "text") editaText(p, e.id, node);
  else if (e?.grup) selecciona(p, e.id, { sol: true }); // entra dins del grup
});

// Zoom amb Ctrl/⌘ + roda o el gest de pinça.
llenc.addEventListener("wheel", (ev) => {
  if (!ev.ctrlKey && !ev.metaKey) return;
  ev.preventDefault();
  posaZoom(zoom * (ev.deltaY < 0 ? 1.1 : 1 / 1.1));
}, { passive: false });

function posaZoom(z) {
  zoom = Math.max(0.3, Math.min(4, z));
  clearTimeout(posaZoom.t);
  posaZoom.t = setTimeout(pintaLlenc, 60);
}
$$("[data-zoom]").forEach((b) => b.addEventListener("click", () => {
  if (b.dataset.zoom === "ajusta") posaZoom(1);
  else posaZoom(zoom * (b.dataset.zoom === "1" ? 1.25 : 0.8));
}));
new ResizeObserver(() => { if (!gest && !edicio) pintaLlenc(); }).observe(llenc);

// ------------------------------------------------------------ Edició de text i lletra

function editaLletra(p, id) {
  const e = elementDe(p, id);
  if (!e || !editable) return;
  if (transport()) {
    avisa("Aquesta cançó té transport en aquest cançoner. Per editar la lletra, posa el transport a 0 o aplica'l a la cançó (pestanya Cançó).");
    return;
  }
  sortEdicio();
  const node = nodeElement(p, id);
  const editor = node?._editor;
  if (!editor) return;
  selecciona(p, id, { sol: true });
  foto(true);
  edicio = { tipus: "lletra", p, id, node, editor };
  node.classList.add("editant");
  editor.setEditable(true);
  editor.commands.focus("end");
  const actualitza = () => {
    e.doc = editor.getJSON();
    canviat();
    clearTimeout(actualitza.t);
    actualitza.t = setTimeout(() => {
      reajusta();
      actualitzaVariables();
    }, 250);
  };
  edicio.desconnecta = () => {
    editor.off("update", actualitza);
    editor.off("transaction", actualitzaBarraText);
  };
  editor.on("update", actualitza);
  editor.on("transaction", actualitzaBarraText);
  $("#barra-text").classList.replace("hidden", "flex");
  pintaSeleccio();
  actualitzaBarraText();
  pintaMidaMarc();
}

function editaText(p, id, node) {
  const e = elementDe(p, id);
  sortEdicio();
  selecciona(p, id, { sol: true });
  foto(true);
  edicio = { tipus: "text", p, id, node };
  node.textContent = e.text; // es veuen les variables per poder-les editar
  node.contentEditable = "plaintext-only";
  node.classList.add("editant");
  node.focus();
  document.getSelection().selectAllChildren(node);
  node.addEventListener("input", () => {
    e.text = node.innerText.replace(/\n$/, "");
    canviat();
    const camp = $('[data-prop="text"]');
    if (camp) camp.value = e.text;
  });
  pintaSeleccio();
}

function sortEdicio() {
  if (!edicio) return;
  const { tipus, p, node, editor } = edicio;
  edicio.desconnecta?.();
  edicio = null;
  if (tipus === "lletra") {
    editor.setEditable(false);
    node.classList.remove("editant");
    $("#barra-text").classList.replace("flex", "hidden");
    amagaBombolla();
    tancaPopover();
  } else {
    node.contentEditable = "false";
    node.classList.remove("editant");
    repintaPagina(p);
  }
  pintaSeleccio();
}

/** Actualitza els textos amb variables (p. ex. {acords}) sense tornar a dibuixar la pàgina. */
function actualitzaVariables() {
  numerosPagina().forEach((numero, p) => {
    for (const e of pagines[p].elements) {
      if (e.tipus !== "text" || !/\{(acords|titol|autor)\}/.test(e.text)) continue;
      const node = nodeElement(p, e.id);
      if (node && !node.classList.contains("editant")) {
        const nou = dibuixaElement(e, { ...opcionsDibuix(), context: contextDe(numero) });
        node.textContent = nou.textContent;
      }
    }
  });
}

// Barra de format de la lletra
const FORMATS = {
  acord: (ed) => {
    const coords = ed.view.coordsAtPos(ed.state.selection.from);
    obrePopoverAcord(null, "", { left: coords.left, top: coords.top - 8, bottom: coords.bottom });
  },
  tonica: (ed) => ed.chain().focus().toggleMark("tonica").run(),
  bold: (ed) => ed.chain().focus().toggleMark("bold").run(),
  italic: (ed) => ed.chain().focus().toggleMark("italic").run(),
  cor: (ed) => ed.chain().focus().toggleMark("cor").run(),
  seccio: (ed) => ed.chain().focus().toggleNode("seccio", "linia").run(),
  nota: (ed) => ed.chain().focus().toggleNode("nota", "linia").run(),
  imatge: () => { $("#fitxer-imatge").dataset.desti = "lletra"; $("#fitxer-imatge").click(); },
  enganxa: () => $("#dialeg-text").showModal(),
  talla: () => tallaAqui(),
  surt: () => sortEdicio(),
};
$$("[data-format]").forEach((b) => {
  b.addEventListener("mousedown", (ev) => ev.preventDefault());
  b.addEventListener("click", () => edicio?.editor && FORMATS[b.dataset.format]?.(edicio.editor));
});

function actualitzaBarraText() {
  const ed = edicio?.editor;
  if (!ed) return;
  for (const nom of ["tonica", "bold", "italic", "cor", "seccio", "nota"]) {
    $(`[data-format="${nom}"]`)?.setAttribute("aria-pressed", String(ed.isActive(nom)));
    $(`[data-bombolla="${nom}"]`)?.setAttribute("aria-pressed", String(ed.isActive(nom)));
  }
  pintaBombolla();
}

// Bombolla sobre el text seleccionat: acord, marques i mida del text.
const bombolla = $("#bombolla");

function amagaBombolla() {
  bombolla.classList.replace("flex", "hidden");
}

function pintaBombolla() {
  const ed = edicio?.editor;
  const { from, to, empty } = ed?.state.selection || {};
  if (!ed || empty || !popover.classList.contains("hidden") || ed.state.selection.node) return amagaBombolla();
  const inici = ed.view.coordsAtPos(from);
  const fi = ed.view.coordsAtPos(to);
  bombolla.classList.replace("hidden", "flex");
  const amplada = bombolla.offsetWidth;
  const centre = (inici.left + fi.right) / 2;
  bombolla.style.left = `${Math.min(window.innerWidth - amplada - 8, Math.max(8, centre - amplada / 2))}px`;
  // A sobre de la selecció, deixant lloc per a la fila dels acords; si no hi cap, a sota.
  const dalt = Math.min(inici.top, fi.top) - bombolla.offsetHeight - 26;
  bombolla.style.top = `${dalt > 8 ? dalt : Math.max(inici.bottom, fi.bottom) + 8}px`;
  $("#mida-seleccio").value = String(ed.getAttributes("mida").valor || 1);
}

bombolla.querySelectorAll("button").forEach((b) => b.addEventListener("mousedown", (ev) => ev.preventDefault()));
bombolla.querySelectorAll("[data-bombolla]").forEach((b) => b.addEventListener("click", () => {
  const ed = edicio?.editor;
  if (ed) FORMATS[b.dataset.bombolla]?.(ed);
}));
$("#mida-seleccio").addEventListener("change", (ev) => {
  if (edicio?.editor) posaMida(edicio.editor, ev.target.value);
});

// Mida de la lletra de tot el marc que s'edita.
function midaMarc(e) {
  return Number(e.format?.mida ?? K.estils[e.estil || "lletra"]?.mida ?? 11);
}

function pintaMidaMarc() {
  if (edicio?.tipus !== "lletra") return;
  const e = elementDe(edicio.p, edicio.id);
  const mida = midaMarc(e);
  if (document.activeElement !== $("#mida-marc")) $("#mida-marc").value = mida;
  $("#ajusta-marc").checked = e.ajusta !== false;
  const escala = Number(edicio.node.dataset.escala || 1);
  const desborda = edicio.node.classList.contains("desborda");
  $("#mida-efectiva").textContent = desborda ? "no hi cap!" : escala < 0.999 ? `→ ${(mida * escala).toFixed(1)} pt perquè hi càpiga` : "";
  $("#mida-efectiva").classList.toggle("text-vermello-600", desborda);
}

function canviaMidaMarc(mida, ajusta) {
  if (edicio?.tipus !== "lletra") return;
  const e = elementDe(edicio.p, edicio.id);
  foto();
  if (mida !== undefined && Number.isFinite(mida)) {
    mida = Math.max(5, Math.min(40, Math.round(mida * 2) / 2));
    e.format = { ...(e.format || {}), mida };
    edicio.node.style.fontSize = `calc(${mida}pt * var(--escala, 1))`;
  }
  if (ajusta !== undefined) e.ajusta = ajusta;
  reajusta();
  pintaMidaMarc();
  canviat();
}

$$("[data-mida-marc]").forEach((b) => {
  b.addEventListener("mousedown", (ev) => ev.preventDefault());
  b.addEventListener("click", () => {
    const e = edicio && elementDe(edicio.p, edicio.id);
    if (e) canviaMidaMarc(midaMarc(e) + Number(b.dataset.midaMarc));
  });
});
$("#mida-marc").addEventListener("change", (ev) => canviaMidaMarc(Number(ev.target.value)));
$("#ajusta-marc").addEventListener("change", (ev) => canviaMidaMarc(undefined, ev.target.checked));

/** Mou la lletra que hi ha després del cursor al primer marc de lletra de la pàgina següent. */
function tallaAqui() {
  if (obert.tipus !== "canco" || !edicio?.editor) return;
  const { editor, p, id } = edicio;
  const pos = editor.state.selection.from;
  const resta = editor.state.doc.cut(pos).toJSON();
  const primera = editor.state.doc.cut(0, pos).toJSON();
  const e = elementDe(p, id);
  foto(true);
  e.doc = primera;
  let seguent = pagines[p + 1];
  if (!seguent) {
    seguent = paginaNova(e);
    pagines.push(seguent);
  }
  let desti = seguent.elements.find((x) => x.tipus === "lletra");
  if (!desti) {
    desti = { ...copia(e), id: nouId(), doc: { type: "doc", content: [] } };
    seguent.elements.push(desti);
  }
  desti.doc = { type: "doc", content: [...(resta.content || []), ...(desti.doc.content || [])] };
  if (!desti.doc.content.length) desti.doc.content = [{ type: "linia" }];
  sortEdicio();
  canviat({ refesLlenc: true });
}

// ------------------------------------------------------------ Popover d'acords

const popover = $("#popover-acord");
let posAcord = null;
let posInsercio = null;

function obrePopoverAcord(pos, nom, rect) {
  if (!edicio?.editor) return;
  posAcord = pos;
  posInsercio = pos === null ? edicio.editor.state.selection.from : null;
  amagaBombolla();
  $("#nom-acord").value = nom;
  $("#error-acord").classList.add("hidden");
  $("#elimina-acord").classList.toggle("hidden", pos === null);
  const suggeriments = [...new Set([...acordsDelDocument(edicio.editor), ...ACORDS_COMUNS])].slice(0, 24);
  $("#suggeriments-acord").replaceChildren(...suggeriments.map((a) => {
    const b = el("button", { text: a, classe: "xip-acord cursor-pointer hover:bg-vermello-100", atributs: { type: "button" } });
    b.addEventListener("click", () => confirmaAcord(a));
    return b;
  }));
  popover.classList.remove("hidden");
  const left = Math.min(window.innerWidth - popover.offsetWidth - 8, Math.max(8, rect.left - 12));
  const top = rect.top - popover.offsetHeight - 6 > 8 ? rect.top - popover.offsetHeight - 6 : rect.bottom + 6;
  popover.style.left = `${left}px`;
  popover.style.top = `${top}px`;
  $("#nom-acord").focus();
  $("#nom-acord").select();
}

function tancaPopover() {
  popover.classList.add("hidden");
  posAcord = null;
}

function confirmaAcord(nom) {
  nom = nom.trim();
  if (!esAcord(nom)) return $("#error-acord").classList.remove("hidden");
  posaAcord(edicio.editor, nom, posAcord, posInsercio);
  tancaPopover();
  pintaBombolla();
}
$("#form-acord").addEventListener("submit", (ev) => { ev.preventDefault(); confirmaAcord($("#nom-acord").value); });
$("#elimina-acord").addEventListener("click", () => { if (posAcord !== null) treuAcord(edicio.editor, posAcord); tancaPopover(); });
popover.addEventListener("keydown", (ev) => { if (ev.key === "Escape") { tancaPopover(); edicio?.editor.commands.focus(); } });
document.addEventListener("pointerdown", (ev) => {
  if (!popover.classList.contains("hidden") && !popover.contains(ev.target) && !ev.target.closest(".acord-nom")) tancaPopover();
});

$("#form-text").addEventListener("submit", async (ev) => {
  if (ev.submitter?.value !== "importa") return;
  const text = $("#text-importa").value;
  if (!text.trim()) return;
  const { doc } = await api(urls.converteix, "POST", { text });
  const substitueix = $("#substitueix-text").checked;
  $("#text-importa").value = "";
  if (edicio?.editor) {
    if (substitueix) edicio.editor.commands.setContent(doc, { emitUpdate: true });
    else edicio.editor.chain().focus().insertContent(doc.content).run();
    return;
  }
  // Sense cap marc en edició: es fa servir el marc de lletra seleccionat o el de la pàgina (o se'n crea un).
  const p = paginaActual();
  let marc = elementSel()?.tipus === "lletra" ? elementSel() : pagines[p]?.elements.find((e) => e.tipus === "lletra");
  foto(true);
  if (!marc) {
    marc = { id: nouId(), rotacio: 0, opacitat: 1, ...NOUS["nou-lletra"](), doc: { type: "doc", content: [] } };
    pagines[p].elements.push(marc);
  }
  const anterior = (marc.doc?.content || []).filter((b) => b.content?.length || b.type !== "linia");
  marc.doc = { type: "doc", content: substitueix || !anterior.length ? doc.content : [...marc.doc.content, { type: "linia" }, ...doc.content] };
  seleccio = { p, id: marc.id };
  canviat({ refesLlenc: true });
});

// ------------------------------------------------------------ Afegir elements i pàgines

function paginaNova(referencia = null) {
  const lletra = referencia
    ? { ...copia(referencia), id: nouId(), doc: { type: "doc", content: [{ type: "linia" }] }, y: 13, h: 179 }
    : { id: nouId(), tipus: "lletra", x: MARGE, y: 13, w: AMPLE - 2 * MARGE, h: 179, rotacio: 0, opacitat: 1, estil: "lletra", ajusta: true, columnes: 1, doc: { type: "doc", content: [{ type: "linia" }] } };
  // La pàgina nova fa servir la mateixa mestra que la de la cançó (sense forçar-ne el costat).
  const mestra = obert.tipus === "canco" && pagines.length ? (pagines[paginaActual()] ?? pagines[0]).mestra ?? null : "estandard";
  return { id: nouId(), mestra, fons: "#ffffff", elements: obert.tipus === "canco" ? [lletra] : [] };
}

function paginaActual() {
  return seleccio?.p ?? 0;
}

function afegeix(element) {
  if (!editable || obert?.tipus === "llibre") return;
  const p = paginaActual();
  foto(true);
  pagines[p].elements.push(element);
  seleccio = { p, id: element.id };
  canviat();
  repintaPagina(p).then(() => pintaPropietats());
}

const NOUS = {
  "nou-lletra": () => ({ tipus: "lletra", x: MARGE, y: 40, w: AMPLE - 2 * MARGE, h: 120, estil: "lletra", ajusta: true, columnes: 1, separacio: 6, doc: { type: "doc", content: [{ type: "linia" }] } }),
  "nou-text": () => ({ tipus: "text", x: 24, y: 24, w: 100, h: 14, text: "Text", estil: "text", alineacio: "left" }),
  "nou-forma": () => ({ tipus: "forma", forma: "rectangle", x: 34, y: 80, w: 80, h: 50, fons: "#c4321f", radi: 0, vora: "", gruix: 0 }),
  "nou-elipse": () => ({ tipus: "forma", forma: "elipse", x: 44, y: 75, w: 60, h: 60, fons: "#c4321f", radi: 0, vora: "", gruix: 0 }),
  "nou-numero": () => ({ tipus: "numero", x: 59, y: 197, w: 30, h: 6, estil: "numero", alineacio: "center" }),
  "nou-qr": () => ({ tipus: "qr", x: 105, y: 160, w: 28, h: 33, video: videosCanco()[0]?.id || "", peu: true, color: "cmyk(0,0,0,100)" }),
};

const EINES = {
  desfes: () => desfes(true),
  refes: () => desfes(false),
  "nou-imatge": () => { $("#fitxer-imatge").dataset.desti = "element"; $("#fitxer-imatge").click(); },
  "importa-text": () => {
    if (obert?.tipus !== "canco" || !editable) return avisa("Obre una cançó per importar-hi text amb acords, o fes servir «Importa» a la llista per crear-ne una de nova.");
    if (transport()) return avisa("Aquesta cançó té transport en aquest cançoner. Posa'l a 0 o aplica'l a la cançó abans d'importar-hi text.");
    $("#dialeg-text").showModal();
  },
  "pagina-nova": () => {
    if (obert?.tipus !== "canco" || !editable) return;
    foto(true);
    const p = paginaActual();
    const lletra = pagines[p]?.elements.find((e) => e.tipus === "lletra");
    pagines.splice(p + 1, 0, paginaNova(lletra));
    seleccio = { p: p + 1, id: null };
    canviat({ refesLlenc: true });
  },
  "pagina-duplica": () => {
    if (obert?.tipus !== "canco" || !editable) return;
    foto(true);
    const p = paginaActual();
    const nova = copia(pagines[p]);
    nova.id = nouId();
    nova.elements.forEach((e) => (e.id = nouId()));
    pagines.splice(p + 1, 0, nova);
    seleccio = { p: p + 1, id: null };
    canviat({ refesLlenc: true });
  },
  "pagina-esborra": () => {
    if (obert?.tipus !== "canco" || !editable || pagines.length < 2) return;
    if (!confirm("Vols esborrar aquesta pàgina de la cançó? (Ho pots desfer amb ⌘Z)")) return;
    foto(true);
    pagines.splice(paginaActual(), 1);
    seleccio = null;
    canviat({ refesLlenc: true });
  },
  "pagina-esquerra": () => mouPagina(-1),
  "pagina-dreta": () => mouPagina(1),
};
for (const tipus of Object.keys(NOUS)) EINES[tipus] = () => afegeix({ id: nouId(), rotacio: 0, opacitat: 1, ...NOUS[tipus]() });

function mouPagina(d) {
  if (obert?.tipus !== "canco" || !editable) return;
  const p = paginaActual();
  const q = p + d;
  if (q < 0 || q >= pagines.length) return;
  foto(true);
  [pagines[p], pagines[q]] = [pagines[q], pagines[p]];
  seleccio = { p: q, id: seleccio?.id ?? null };
  canviat({ refesLlenc: true });
}

$$("[data-eina]").forEach((b) => {
  b.addEventListener("mousedown", (ev) => ev.preventDefault());
  b.addEventListener("click", () => EINES[b.dataset.eina]?.());
});

$("#fitxer-imatge").addEventListener("change", async (ev) => {
  const fitxer = ev.target.files[0];
  const desti = ev.target.dataset.desti;
  ev.target.value = "";
  if (!fitxer) return;
  const formulari = new FormData();
  formulari.append("imatge", fitxer);
  mostraEstat("Pujant la imatge…", "treballant");
  let r;
  try {
    r = await api(urls.imatges, "POST", formulari);
  } catch (e) {
    return mostraEstat(e.message, "error");
  }
  mostraEstat("Tot desat");
  if (desti === "lletra" && edicio?.editor) {
    edicio.editor.chain().focus().insertContent({ type: "imatge", attrs: { src: r.id, posicio: "dreta", amplada: 40 } }).run();
    return;
  }
  if (desti === "substitueix" && elementSel()) return canviaPropietats({ src: r.id });
  const img = new Image();
  img.src = r.url;
  await img.decode().catch(() => {});
  const proporcio = img.naturalWidth ? img.naturalHeight / img.naturalWidth : 0.75;
  const w = 90;
  const h = Math.min(ALT - 20, arrodoneix(w * proporcio));
  afegeix({ id: nouId(), tipus: "imatge", x: (AMPLE - w) / 2, y: (ALT - h) / 2, w, h, src: r.id, ajust: "cover", radi: 0, rotacio: 0, opacitat: 1 });
});

// Arrossegar imatges des de l'ordinador directament a una pàgina.
llenc.addEventListener("dragover", (ev) => { if (ev.dataTransfer?.types.includes("Files")) ev.preventDefault(); });
llenc.addEventListener("drop", async (ev) => {
  const fitxer = [...(ev.dataTransfer?.files || [])].find((f) => f.type.startsWith("image/"));
  const caixa = ev.target.closest(".pagina-editor");
  if (!fitxer || !caixa || !editable) return;
  ev.preventDefault();
  seleccio = { p: Number(caixa.dataset.pagina), id: null };
  const dt = new DataTransfer();
  dt.items.add(fitxer);
  $("#fitxer-imatge").files = dt.files;
  $("#fitxer-imatge").dataset.desti = "element";
  $("#fitxer-imatge").dispatchEvent(new Event("change"));
});

// ------------------------------------------------------------ Accions sobre l'element

let portapapers = null;
try { portapapers = JSON.parse(localStorage.getItem("canconer.portapapers") || "null"); } catch { /* sense emmagatzematge */ }

/** Còpies d'uns elements amb ids nous; els grups es copien com a grups nous (no s'ajunten amb l'original). */
function clona(elements, desplaça = 0) {
  const grups = new Map();
  return elements.map((e) => {
    const c = { ...copia(e), id: nouId(), x: arrodoneix(e.x + desplaça), y: arrodoneix(e.y + desplaça) };
    if (e.grup) {
      if (!grups.has(e.grup)) grups.set(e.grup, nouId());
      c.grup = grups.get(e.grup);
    }
    return c;
  });
}

function accio(nom) {
  const els = elementsSel();
  if (!els.length || !editable) return;
  const p = seleccio.p;
  const llista = pagines[p].elements;
  const ids = els.map((e) => e.id);
  const ordenats = llista.filter((e) => ids.includes(e.id)); // en l'ordre de les capes
  foto(true);
  if (nom === "esborra") {
    pagines[p].elements = llista.filter((e) => !ids.includes(e.id));
    seleccio = { p, id: null, ids: [] };
  } else if (nom === "duplica") {
    const copies = clona(ordenats, 4);
    const darrer = Math.max(...ordenats.map((e) => llista.indexOf(e)));
    llista.splice(darrer + 1, 0, ...copies);
    seleccio = { p, id: copies[0].id, ids: copies.map((c) => c.id) };
  } else if (nom === "bloqueja") {
    const tots = els.every((e) => e.bloquejat);
    els.forEach((e) => (tots ? delete e.bloquejat : (e.bloquejat = true)));
  } else if (nom === "davant") {
    pagines[p].elements = [...llista.filter((e) => !ids.includes(e.id)), ...ordenats];
  } else if (nom === "darrere") {
    pagines[p].elements = [...ordenats, ...llista.filter((e) => !ids.includes(e.id))];
  } else if (nom === "a-pagina-anterior" || nom === "a-pagina-seguent") {
    const desti = p + (nom === "a-pagina-anterior" ? -1 : 1);
    if (!passaAPagina(p, desti, ordenats.map(copia))) {
      pilaActual().enrere.pop();
      mostraEstat(pagines[desti] ? "Els elements bloquejats no es mouen" : "No hi ha cap pàgina en aquella direcció");
    }
    return;
  } else if (nom === "agrupa") {
    if (els.length < 2) return;
    const grup = nouId();
    els.forEach((e) => (e.grup = grup));
  } else if (nom === "desagrupa") {
    els.forEach((e) => delete e.grup);
  }
  canviat();
  repintaPagina(p).then(() => { pintaSeleccio(); pintaPropietats(); });
}
$$("[data-accio]").forEach((b) => b.addEventListener("click", () => accio(b.dataset.accio)));

/** Alinea els elements seleccionats entre ells (sobre el requadre comú). */
function alinea(tipus) {
  const els = elementsSel();
  if (els.length < 2 || !editable) return;
  const r = requadre(els);
  foto(true);
  for (const e of els) {
    const q = requadre([e]); // requadre visible (amb la rotació); es desplaça l'element sencer
    if (tipus === "esquerra") e.x = arrodoneix(e.x + r.x - q.x);
    if (tipus === "centre") e.x = arrodoneix(e.x + r.x + r.w / 2 - (q.x + q.w / 2));
    if (tipus === "dreta") e.x = arrodoneix(e.x + r.x + r.w - (q.x + q.w));
    if (tipus === "dalt") e.y = arrodoneix(e.y + r.y - q.y);
    if (tipus === "mig") e.y = arrodoneix(e.y + r.y + r.h / 2 - (q.y + q.h / 2));
    if (tipus === "baix") e.y = arrodoneix(e.y + r.y + r.h - (q.y + q.h));
    const node = nodeElement(seleccio.p, e.id);
    if (node) reposiciona(node, e);
  }
  pintaSeleccio();
  canviat();
}
$$("[data-alinea-multi]").forEach((b) => b.addEventListener("click", () => alinea(b.dataset.alineaMulti)));

$$("[data-gira]").forEach((b) => b.addEventListener("click", () => {
  const e = elementSel();
  if (!e || !editable) return;
  foto(true);
  e.rotacio = ((((e.rotacio || 0) + Number(b.dataset.gira)) % 360) + 540) % 360 - 180;
  const node = nodeElement(seleccio.p, e.id);
  if (node) reposiciona(node, e);
  pintaSeleccio();
  pintaPropietats();
  canviat();
}));

function copiaElement() {
  const els = elementsSel();
  if (!els.length) return;
  const ordre = pagines[seleccio.p].elements;
  portapapers = copia(els.sort((a, b) => ordre.indexOf(a) - ordre.indexOf(b)));
  try { localStorage.setItem("canconer.portapapers", JSON.stringify(portapapers)); } catch { /* sense emmagatzematge */ }
  mostraEstat(els.length > 1 ? `${els.length} elements copiats` : "Element copiat");
}

function enganxaElements(elements, desplaça = 4) {
  if (!elements?.length || !editable || obert?.tipus === "llibre") return;
  const p = paginaActual();
  foto(true);
  const nous = clona(elements, desplaça);
  pagines[p].elements.push(...nous);
  seleccio = { p, id: nous[0].id, ids: nous.map((e) => e.id) };
  canviat();
  repintaPagina(p).then(() => { pintaSeleccio(); pintaPropietats(); });
}

// ------------------------------------------------------------ Teclat

document.addEventListener("keydown", (ev) => {
  const escrivint = edicio || ev.target.matches?.("input, textarea, select, [contenteditable='true'], [contenteditable='plaintext-only']");
  const mod = ev.metaKey || ev.ctrlKey;
  if (ev.key === "Escape") {
    if (!$("#historial").classList.contains("hidden")) return tancaHistorial();
    if (edicio) return sortEdicio();
    return selecciona(null, null);
  }
  if (mod && ev.key.toLowerCase() === "s") {
    ev.preventDefault();
    return desa();
  }
  if (mod && ev.key.toLowerCase() === "k" && edicio?.tipus === "lletra") {
    ev.preventDefault();
    return FORMATS.acord(edicio.editor);
  }
  if (escrivint) return;
  if (mod && ev.key.toLowerCase() === "z") {
    ev.preventDefault();
    return desfes(!ev.shiftKey);
  }
  if (mod && ev.key.toLowerCase() === "c" && idsSel().length) return copiaElement();
  if (mod && ev.key.toLowerCase() === "v" && portapapers) {
    ev.preventDefault();
    return enganxaElements(portapapers);
  }
  if (mod && ev.key.toLowerCase() === "a" && obert?.tipus !== "llibre" && pagines.length) {
    ev.preventDefault();
    const p = paginaActual();
    return seleccionaMolts(p, pagines[p].elements.filter((e) => !e.bloquejat).map((e) => e.id));
  }
  if (!idsSel().length) return;
  if (mod && ev.key.toLowerCase() === "g") {
    ev.preventDefault();
    return accio(ev.shiftKey ? "desagrupa" : "agrupa");
  }
  if (ev.key === "Delete" || ev.key === "Backspace") {
    ev.preventDefault();
    accio("esborra");
  } else if (mod && ev.key.toLowerCase() === "d") {
    ev.preventDefault();
    accio("duplica");
  } else if (ev.key === "Enter" && elementSel() && ["lletra", "text"].includes(elementSel().tipus)) {
    ev.preventDefault();
    const e = elementSel();
    if (e.tipus === "lletra") editaLletra(seleccio.p, e.id);
    else editaText(seleccio.p, e.id, nodeElement(seleccio.p, e.id));
  } else if (ev.key.startsWith("Arrow") && editable) {
    ev.preventDefault();
    const pas = ev.shiftKey ? 5 : 0.5;
    foto();
    for (const e of elementsSel()) {
      if (ev.key === "ArrowLeft") e.x = arrodoneix(e.x - pas);
      if (ev.key === "ArrowRight") e.x = arrodoneix(e.x + pas);
      if (ev.key === "ArrowUp") e.y = arrodoneix(e.y - pas);
      if (ev.key === "ArrowDown") e.y = arrodoneix(e.y + pas);
      const node = nodeElement(seleccio.p, e.id);
      if (node) reposiciona(node, e);
    }
    pintaSeleccio();
    pintaPropietatsPosicio();
    canviat();
  }
});

// ------------------------------------------------------------ Panell de propietats

const NOMS_TIPUS = { text: "Text", lletra: "Marc de lletra", imatge: "Imatge", forma: "Forma", numero: "Número de pàgina", index: "Índex", diagrames: "Diagrames d'acords", qr: "Codi QR", index_qr: "Índex de vídeos" };

function omplenaEstils(select) {
  const valor = select.value;
  select.replaceChildren(...Object.entries(K.estils).map(([clau, e]) => el("option", { text: e.nom, atributs: { value: clau } })));
  select.value = valor;
}

function pintaPropietats() {
  pintaPropietatsElement();
  // Botons per passar la selecció a la pàgina anterior o següent (alternativa a arrossegar).
  $$("[data-moure-pagina]").forEach((d) => d.classList.toggle("hidden", pagines.length < 2 || obert?.tipus === "llibre"));
  $$('[data-accio="a-pagina-anterior"]').forEach((b) => (b.disabled = !editable || !seleccio || seleccio.p === 0));
  $$('[data-accio="a-pagina-seguent"]').forEach((b) => (b.disabled = !editable || !seleccio || seleccio.p >= pagines.length - 1));
}

function pintaPropietatsElement() {
  pintaCapes();
  const multi = idsSel().length > 1;
  $("#props-multi").classList.toggle("hidden", !multi);
  $("#props-multi").classList.toggle("flex", multi);
  if (multi) {
    const els = elementsSel();
    const grup = els[0].grup && els.every((x) => x.grup === els[0].grup) && idsGrup(seleccio.p, els[0].id).length === els.length;
    $("#props-pagina").classList.add("hidden");
    $("#props-element").classList.add("hidden");
    $("#props-element").classList.remove("flex");
    $("#titol-multi").textContent = grup ? `Grup (${els.length} elements)` : `${els.length} elements seleccionats`;
    $("#info-multi").textContent = grup ? "Es mou, s'escala i es gira com un sol element." : "Agrupa'ls perquè es moguin sempre junts.";
    $('#props-multi [data-accio="agrupa"]').classList.toggle("hidden", grup);
    $('#props-multi [data-accio="desagrupa"]').classList.toggle("hidden", !els.some((x) => x.grup));
    $$("#props-multi button").forEach((b) => (b.disabled = !editable));
    return;
  }
  const e = elementSel();
  $("#props-pagina").classList.toggle("hidden", !!e);
  $("#props-element").classList.toggle("hidden", !e);
  $("#props-element").classList.toggle("flex", !!e);
  $$("#props-element input, #props-element select, #props-element textarea, #props-element button").forEach((c) => (c.disabled = !editable));
  if (!e) return pintaPropietatsPagina();
  $("#titol-props").textContent = NOMS_TIPUS[e.tipus] || "Element";
  $$("[data-per]").forEach((b) => b.classList.toggle("hidden", !b.dataset.per.split(" ").includes(e.tipus)));
  omplenaEstils($('[data-prop="estil"]'));
  if (e.tipus === "qr") omplenaVideosQR(e);
  $$("[data-prop]").forEach((camp) => {
    const valor = e[camp.dataset.prop];
    if (camp.type === "checkbox") camp.checked = camp.dataset.prop === "ajusta" ? valor !== false : !!valor;
    else if (document.activeElement !== camp) camp.value = camp.type === "color" ? valor || "#000000" : valor ?? "";
  });
  const format = e.format || {};
  $$("[data-format-prop]").forEach((camp) => {
    const valor = format[camp.dataset.formatProp];
    if (camp.type === "checkbox") camp.checked = !!valor;
    else if (camp.type === "color") camp.value = valor || K.estils[e.estil]?.color || "#000000";
    else if (document.activeElement !== camp) camp.value = valor ?? "";
  });
  $$("[data-alinea]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.alinea === (e.alineacio || "left"))));
  $('#props-element [data-accio="bloqueja"]').setAttribute("aria-pressed", String(!!e.bloquejat));
  $("#nota-grup").classList.toggle("hidden", !e.grup);
  $("#nota-grup").classList.toggle("flex", !!e.grup);
  const font = TIPOGRAFIES.find((f) => f.clau === format.font);
  const fontEstil = TIPOGRAFIES.find((f) => f.clau === K.estils[e.estil]?.font);
  $("#font-element .nom-font").textContent = font ? font.nom : `De l'estil (${fontEstil?.nom || "—"})`;
  $("#font-element .nom-font").style.fontFamily = FONTS[format.font || K.estils[e.estil]?.font] || "";
  $$("[data-ajust]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.ajust === (e.ajust || "cover"))));
  if (e.tipus === "lletra") pintaInfoMarc();
}

function pintaPropietatsPosicio() {
  const e = elementSel();
  if (!e) return;
  for (const prop of ["x", "y", "w", "h"]) {
    const camp = $(`[data-prop="${prop}"]`);
    if (camp && document.activeElement !== camp) camp.value = e[prop];
  }
}

function pintaInfoMarc() {
  const e = elementSel();
  if (e?.tipus !== "lletra") return;
  const node = nodeElement(seleccio.p, e.id);
  const factor = Number(node?.dataset.escala || 1);
  const mida = (Number(e.format?.mida || K.estils[e.estil || "lletra"]?.mida) || 11) * factor;
  const info = $("#info-marc");
  if (node?.classList.contains("desborda")) {
    info.className = "rounded-md bg-vermello-50 px-3 py-2 text-[13px] leading-snug text-vermello-700";
    info.textContent = "La lletra no hi cap. Fes el marc més gran, activa l'ajust, afegeix columnes o fes servir «Talla aquí» per passar-ne una part a la pàgina següent.";
  } else {
    info.className = "rounded-md bg-paper-200/60 px-3 py-2 text-[13px] leading-snug text-ink-700";
    info.textContent = factor < 1 ? `Lletra ajustada a ${mida.toFixed(1)} pt perquè hi càpiga.` : `Lletra a ${mida.toFixed(1)} pt.`;
  }
}

function pintaPropietatsPagina() {
  const especial = obert?.tipus === "especial";
  const mestra = obert?.tipus === "mestra";
  const llibre = obert?.tipus === "llibre";
  $("#titol-props-pagina").textContent = llibre ? "Tot el llibret" : mestra ? "Pàgina mestra" : "Pàgina";
  const model = pagines[paginaActual()];
  $("#camp-mestra").classList.toggle("hidden", mestra || llibre);
  $("#camp-costat").classList.toggle("hidden", mestra || llibre || !model?.mestra);
  $("#ajuda-mestra").classList.toggle("hidden", !mestra);
  $("#fons-pagina").closest("label").classList.toggle("hidden", llibre || mestra);
  $("#desa-pagina-biblioteca").classList.toggle("hidden", llibre);
  if (llibre || !model) return;
  const select = $("#mestra-pagina");
  select.replaceChildren(el("option", { text: "Cap (pàgina neta)", atributs: { value: "" } }),
    ...K.mestres.map((m) => el("option", { text: m.nom, atributs: { value: m.id } })));
  select.value = model.mestra || "";
  select.disabled = !editable;
  $("#costat-pagina").value = model.costat || "";
  $("#costat-pagina").disabled = !editable;
  $("#fons-pagina").value = model.fons || "#ffffff";
  $("#fons-pagina").disabled = !editable;
  if (mestra) {
    const m = K.mestres.find((x) => x.id === obert.id);
    $("#nom-mestra").value = m?.nom || "";
    $("#esborra-mestra").classList.toggle("hidden", m?.id === "estandard");
  }
  void especial;
}

function canviaPropietats(propietats, { repinta = true } = {}) {
  const e = elementSel();
  if (!e || !editable) return;
  foto();
  Object.assign(e, propietats);
  canviat();
  if (repinta) repintaPagina(seleccio.p).then(() => pintaPropietats());
}

$$("[data-prop]").forEach((camp) => camp.addEventListener("input", () => {
  const prop = camp.dataset.prop;
  let valor;
  if (camp.type === "checkbox") valor = camp.checked;
  else if (camp.type === "number" || camp.type === "range") {
    if (camp.value === "") return;
    valor = Number(camp.value);
  } else valor = camp.value;
  const nomesPosicio = ["x", "y", "w", "h", "rotacio", "opacitat"].includes(prop);
  if (nomesPosicio) {
    const e = elementSel();
    foto();
    e[prop] = valor;
    const node = nodeElement(seleccio.p, e.id);
    if (node) reposiciona(node, e);
    pintaSeleccio();
    canviat();
    if (prop === "w" || prop === "h") reajusta();
  } else canviaPropietats({ [prop]: valor });
}));

$$("[data-format-prop]").forEach((camp) => camp.addEventListener("input", () => {
  const e = elementSel();
  if (!e) return;
  const format = { ...(e.format || {}) };
  const prop = camp.dataset.formatProp;
  if (camp.type === "checkbox") format[prop] = camp.checked;
  else if (camp.value === "") delete format[prop];
  else format[prop] = camp.type === "number" || prop === "pes" ? Number(camp.value) : camp.value;
  canviaPropietats({ format });
}));
$("#treu-format").addEventListener("click", () => canviaPropietats({ format: {} }));
$$("[data-alinea]").forEach((b) => b.addEventListener("click", () => canviaPropietats({ alineacio: b.dataset.alinea })));
$$("[data-ajust]").forEach((b) => b.addEventListener("click", () => canviaPropietats({ ajust: b.dataset.ajust })));
$$("[data-centra]").forEach((b) => b.addEventListener("click", () => {
  const e = elementSel();
  if (e) canviaPropietats(b.dataset.centra === "x" ? { x: arrodoneix((AMPLE - e.w) / 2) } : { y: arrodoneix((ALT - e.h) / 2) });
}));
$$("[data-variable]").forEach((b) => b.addEventListener("click", () => {
  const camp = $('[data-prop="text"]');
  camp.setRangeText(`{${b.dataset.variable}}`, camp.selectionStart, camp.selectionEnd, "end");
  camp.dispatchEvent(new Event("input"));
}));
$("#canvia-imatge").addEventListener("click", () => { $("#fitxer-imatge").dataset.desti = "substitueix"; $("#fitxer-imatge").click(); });
$("#edita-lletra").addEventListener("click", () => { const e = elementSel(); if (e) editaLletra(seleccio.p, e.id); });

$("#mestra-pagina").addEventListener("change", (ev) => {
  const model = pagines[paginaActual()];
  foto(true);
  model.mestra = ev.target.value || null;
  if (!model.mestra) delete model.costat;
  canviat();
  repintaPagina(paginaActual());
  pintaPropietatsPagina();
});
$("#costat-pagina").addEventListener("change", (ev) => {
  const model = pagines[paginaActual()];
  foto(true);
  if (ev.target.value) model.costat = ev.target.value;
  else delete model.costat;
  canviat();
  repintaPagina(paginaActual());
});
$("#fons-pagina").addEventListener("input", (ev) => {
  foto();
  pagines[paginaActual()].fons = ev.target.value;
  canviat();
  repintaPagina(paginaActual());
});

// Pestanyes del panell dret
$$("[data-pestanya]").forEach((b) => b.addEventListener("click", () => mostraPestanya(b.dataset.pestanya)));
function mostraPestanya(nom) {
  $$("[data-pestanya]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.pestanya === nom)));
  $$("[data-panell-pestanya]").forEach((s) => {
    const visible = s.dataset.panellPestanya === nom;
    s.classList.toggle("hidden", !visible);
    s.classList.toggle("flex", visible);
  });
  if (nom === "biblioteca") pintaBiblioteca();
  if (nom === "estils") pintaEstils();
  if (nom === "capes") pintaCapes();
}

// ------------------------------------------------------------ Capes

const ICONES_CAPA = {
  text: "M4 5h12M10 5v11", lletra: "M4 5h12M4 9h12M4 13h8", imatge: "M3 4h14v12H3zM3 13l4-4 3 3 2-2 5 5",
  forma: "M4 5h12v10H4z", numero: "M7 4 5.5 16M12.5 4 11 16M4 8h11M3.5 12h11", index: "M4 5h12M4 9h12M4 13h12",
  diagrames: "M5 4v12M8 4v12M11 4v12M14 4v12M5 7h9M5 10h9",
};

function nomCapa(e, p) {
  if (e.tipus === "text") {
    const node = nodeElement(p, e.id);
    return (node?.textContent || e.text || "").trim().slice(0, 40) || "Text buit";
  }
  if (e.tipus === "lletra") {
    const primera = (e.doc?.content || []).map((b) => (b.content || []).map((n) => n.text || "").join("")).find((t) => t.trim());
    return `Lletra: ${(primera || "buida").slice(0, 30)}`;
  }
  return NOMS_TIPUS[e.tipus] || e.tipus;
}

function pintaCapes() {
  const seccio = $('[data-panell-pestanya="capes"]');
  if (seccio.classList.contains("hidden")) return;
  const caixa = $("#llista-capes");
  if (!obert || obert.tipus === "llibre") return caixa.replaceChildren(el("p", { text: "Obre una cançó o una pàgina per veure'n les capes.", classe: "text-[13px] text-ink-500" }));
  const numeros = numerosPagina();
  caixa.replaceChildren(...pagines.map((pagina, p) => {
    const grup = el("div", { classe: "flex flex-col gap-0.5" });
    const etiqueta = obert.tipus === "mestra" ? (p === 0 ? "Pàgines parells" : "Pàgines senars") : `Pàgina ${numeros[p]}`;
    grup.append(el("h4", { text: etiqueta, classe: "mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400" }));
    if (!pagina.elements.length) grup.append(el("p", { text: "Sense elements.", classe: "px-2 text-[12px] text-ink-400" }));
    const llista = [...pagina.elements].reverse(); // el de davant, primer
    // Els membres d'un grup es mostren junts, sota la capçalera del grup (a l'altura del primer).
    const ordre = [];
    const vistos = new Set();
    for (const e of llista) {
      if (!e.grup) ordre.push(e);
      else if (!vistos.has(e.grup)) {
        vistos.add(e.grup);
        const membres = llista.filter((x) => x.grup === e.grup);
        ordre.push({ capcalera: e.grup, membres }, ...membres);
      }
    }
    ordre.forEach((e) => {
      if (e.capcalera) {
        const seleccionat = e.membres.every((m) => seleccio?.p === p && idsSel().includes(m.id));
        const fila = el("button", { classe: "fila-capa w-full font-medium", atributs: { type: "button", "aria-current": String(seleccionat) } });
        fila.innerHTML = '<svg class="h-4 w-4 shrink-0 text-ink-400" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 6h5l1.5 2H17v8H3z"/></svg>';
        fila.append(el("span", { text: `Grup (${e.membres.length})`, classe: "flex-1 text-left" }));
        fila.addEventListener("mouseenter", () => e.membres.forEach((m) => nodeElement(p, m.id)?.classList.add("ressaltat")));
        fila.addEventListener("mouseleave", () => e.membres.forEach((m) => nodeElement(p, m.id)?.classList.remove("ressaltat")));
        fila.addEventListener("click", (ev) => {
          e.membres.forEach((m) => nodeElement(p, m.id)?.classList.remove("ressaltat"));
          sortEdicio();
          selecciona(p, e.membres[0].id, { afegeix: ev.shiftKey });
        });
        grup.append(fila);
        return;
      }
      const fila = el("div", { classe: "fila-capa group" + (e.grup ? " ml-4" : ""), atributs: { "aria-current": String(seleccio?.p === p && idsSel().includes(e.id)) } });
      const icona = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      icona.setAttribute("viewBox", "0 0 20 20");
      icona.setAttribute("class", "h-4 w-4 shrink-0 text-ink-400");
      icona.innerHTML = `<path d="${ICONES_CAPA[e.tipus] || ICONES_CAPA.forma}" fill="none" stroke="currentColor" stroke-width="1.5"/>`;
      const nom = el("button", { text: nomCapa(e, p), classe: "min-w-0 flex-1 truncate text-left" + (e.bloquejat ? " text-ink-500" : ""), atributs: { type: "button" } });
      if (e.tipus === "text" || e.tipus === "lletra") nom.style.fontFamily = FONTS[e.format?.font || K.estils[e.estil]?.font] || "";
      const candau = el("button", { classe: "flex h-6 w-6 shrink-0 items-center justify-center rounded text-ink-400 hover:bg-paper-200 hover:text-ink-900" + (e.bloquejat ? " text-vermello-600" : " opacity-0 group-hover:opacity-100"), atributs: { type: "button", title: e.bloquejat ? "Desbloqueja" : "Bloqueja (els clics hi passen a través)" } });
      candau.innerHTML = e.bloquejat
        ? '<svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M5 7V5a3 3 0 0 1 6 0v2M4 7h8v6.5H4z"/></svg>'
        : '<svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M5 7V5a3 3 0 0 1 5.8-1M4 7h8v6.5H4z"/></svg>';
      const amunt = el("button", { text: "↑", classe: "h-6 w-5 shrink-0 rounded text-ink-400 opacity-0 hover:bg-paper-200 group-hover:opacity-100 disabled:invisible", atributs: { type: "button", title: "Porta endavant" } });
      const avall = el("button", { text: "↓", classe: "h-6 w-5 shrink-0 rounded text-ink-400 opacity-0 hover:bg-paper-200 group-hover:opacity-100 disabled:invisible", atributs: { type: "button", title: "Envia enrere" } });
      const index = pagina.elements.indexOf(e);
      amunt.disabled = index === pagina.elements.length - 1 || !editable;
      avall.disabled = index === 0 || !editable;
      candau.disabled = !editable;
      const ressalta = (si) => nodeElement(p, e.id)?.classList.toggle("ressaltat", si);
      fila.addEventListener("mouseenter", () => ressalta(true));
      fila.addEventListener("mouseleave", () => ressalta(false));
      nom.addEventListener("click", (ev) => {
        ressalta(false);
        sortEdicio();
        selecciona(p, e.id, ev.shiftKey ? { afegeix: true, sol: true } : { sol: true });
        nodeElement(p, e.id)?.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
      });
      candau.addEventListener("click", () => {
        foto(true);
        if (e.bloquejat) delete e.bloquejat;
        else e.bloquejat = true;
        canviat();
        repintaPagina(p).then(pintaPropietats);
      });
      const mou = (d) => {
        const i = pagina.elements.indexOf(e);
        const j = i + d;
        if (j < 0 || j >= pagina.elements.length) return;
        foto(true);
        [pagina.elements[i], pagina.elements[j]] = [pagina.elements[j], pagina.elements[i]];
        canviat();
        repintaPagina(p).then(pintaPropietats);
      };
      amunt.addEventListener("click", () => mou(1));
      avall.addEventListener("click", () => mou(-1));
      fila.append(icona, nom, candau, amunt, avall);
      grup.append(fila);
    });
    const mestra = obert.tipus !== "mestra" && mestraDe(pagina.mestra, numeros[p], pagina.costat);
    if (mestra?.elements?.length) {
      grup.append(el("p", { text: `+ ${mestra.elements.length} de la pàgina mestra (s'editen a Pàgines mestres)`, classe: "px-2 pt-1 text-[11.5px] text-ink-400" }));
    }
    return grup;
  }));
}

// ------------------------------------------------------------ Tipografies

const CATEGORIES_FONT = [["serif", "Serif"], ["sans", "Sense serif"], ["display", "Display"], ["manuscrita", "Manuscrites"], ["mono", "Monoespaiades"], ["importada", "Importades"]];
const popoverFonts = $("#popover-fonts");
let selectorFont = null; // {actual, permetBuit, tria(clau|null)}

function obreSelectorFont(boto, opcions) {
  selectorFont = opcions;
  $("#cerca-fonts").value = "";
  pintaLlistaFonts();
  popoverFonts.classList.replace("hidden", "flex");
  const r = boto.getBoundingClientRect();
  const alt = popoverFonts.offsetHeight;
  popoverFonts.style.left = `${Math.max(8, Math.min(window.innerWidth - popoverFonts.offsetWidth - 8, r.right - popoverFonts.offsetWidth))}px`;
  popoverFonts.style.top = `${r.bottom + 6 + alt < window.innerHeight ? r.bottom + 6 : Math.max(8, r.top - alt - 6)}px`;
  $("#cerca-fonts").focus();
  popoverFonts.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: "center" });
}

function tancaSelectorFont() {
  popoverFonts.classList.replace("flex", "hidden");
}

function pintaLlistaFonts() {
  const filtre = $("#cerca-fonts").value.trim().toLowerCase();
  const items = [];
  if (selectorFont?.permetBuit && !filtre) items.push({ clau: null, nom: "De l'estil", css: "" });
  const llista = $("#llista-fonts");
  const files = [];
  const afegeix = (f) => {
    const b = el("button", { text: f.nom, classe: "flex w-full items-center justify-between gap-2 px-3 py-1.5 text-left text-[17px] hover:bg-paper-100 aria-selected:bg-vermello-50 aria-selected:text-vermello-700", atributs: { type: "button", "aria-selected": String((selectorFont?.actual ?? null) === f.clau) } });
    if (f.css) b.style.fontFamily = f.css;
    b.addEventListener("click", () => {
      selectorFont?.tria(f.clau);
      tancaSelectorFont();
    });
    files.push(el("li").appendChild(b).parentNode);
  };
  items.forEach(afegeix);
  for (const [categoria, titol] of CATEGORIES_FONT) {
    const fonts = TIPOGRAFIES.filter((f) => f.categoria === categoria && (!filtre || f.nom.toLowerCase().includes(filtre)));
    if (!fonts.length) continue;
    files.push(el("li", { text: titol, classe: "px-3 pb-1 pt-3 text-[10.5px] font-semibold uppercase tracking-[0.14em] text-ink-400" }));
    fonts.forEach(afegeix);
  }
  if (!files.length) files.push(el("li", { text: "Cap tipografia coincideix.", classe: "px-3 py-4 text-[13px] text-ink-500" }));
  llista.replaceChildren(...files);
}

$("#cerca-fonts").addEventListener("input", pintaLlistaFonts);
popoverFonts.addEventListener("keydown", (ev) => { if (ev.key === "Escape") tancaSelectorFont(); });
document.addEventListener("pointerdown", (ev) => {
  if (popoverFonts.classList.contains("flex") && !popoverFonts.contains(ev.target) && !ev.target.closest("[data-selector-font]")) tancaSelectorFont();
});

$("#font-element").addEventListener("click", (ev) => {
  const e = elementSel();
  if (!e || !editable) return;
  obreSelectorFont(ev.currentTarget, {
    actual: e.format?.font ?? null,
    permetBuit: true,
    tria: (clau) => {
      const format = { ...(e.format || {}) };
      if (clau) format.font = clau;
      else delete format.font;
      canviaPropietats({ format });
    },
  });
});

// Importar tipografies (TTF, OTF, WOFF, WOFF2)
const dialegFont = $("#dialeg-font");
$("#obre-importa-font").addEventListener("click", () => {
  tancaSelectorFont();
  $("#error-font").classList.add("hidden");
  $("#form-font").reset();
  dialegFont.showModal();
});
$("#fitxers-font").addEventListener("change", (ev) => {
  const primer = ev.target.files[0];
  if (primer && !$("#nom-font").value) {
    $("#nom-font").value = primer.name.replace(/\.[^.]+$/, "")
      .replace(/[-_ ]?(thin|hairline|extralight|ultralight|light|regular|book|medium|semibold|demibold|extrabold|ultrabold|bold|black|heavy|italic|oblique)+$/gi, "")
      .replace(/[-_]+/g, " ").trim();
  }
});

function gruixDeNom(nom) {
  const n = nom.toLowerCase().replace(/[-_ ]/g, "");
  const regles = [[/thin|hairline/, 100], [/extralight|ultralight/, 200], [/semibold|demibold/, 600], [/extrabold|ultrabold/, 800],
    [/black|heavy/, 900], [/light/, 300], [/medium/, 500], [/bold/, 700]];
  for (const [regex, pes] of regles) if (regex.test(n)) return pes;
  return 400;
}

$("#form-font").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const fitxers = [...$("#fitxers-font").files];
  const nom = $("#nom-font").value.trim();
  if (!fitxers.length || !nom) return;
  let clau = null;
  try {
    for (const f of fitxers) {
      const formulari = new FormData();
      formulari.append("font", f);
      formulari.append("nom", nom);
      formulari.append("pes", gruixDeNom(f.name));
      formulari.append("estil", /italic|oblique/i.test(f.name) ? "italic" : "normal");
      clau = (await api(urls.fonts, "POST", formulari)).clau;
    }
  } catch (e) {
    $("#error-font").textContent = e.message;
    return $("#error-font").classList.remove("hidden");
  }
  dialegFont.close();
  await recarregaFonts();
  if (clau && selectorFont) selectorFont.tria(clau); // s'aplica on s'havia obert el selector
  mostraEstat(`Tipografia «${nom}» importada`);
});

async function recarregaFonts() {
  TIPOGRAFIES = (await api(urls.fonts)).fonts;
  registraFonts(TIPOGRAFIES);
  const enllac = document.querySelector(`link[href^="${urls.fontsCss}"]`);
  await new Promise((resol) => {
    const nou = enllac.cloneNode();
    nou.href = `${urls.fontsCss}?v=${Date.now()}`;
    nou.onload = nou.onerror = resol;
    enllac.after(nou);
    enllac.remove();
  });
  aplicaEstils(K.estils);
  await pintaLlenc();
  if (!$('[data-panell-pestanya="estils"]').classList.contains("hidden")) pintaEstils();
}

// ------------------------------------------------------------ Avisos del llenç

function avisa(text, accions = []) {
  const caixa = $("#avis-llenc");
  $("#text-avis-llenc").textContent = text;
  $("#accions-avis-llenc").replaceChildren(...accions.map(([t, f, primari]) => {
    const b = el("button", { text: t, classe: `btn btn-petit${primari ? " btn-primari" : ""}`, atributs: { type: "button" } });
    b.addEventListener("click", f);
    return b;
  }));
  caixa.classList.replace("hidden", "flex");
}

function pintaAvisLlenc() {
  const caixa = $("#avis-llenc");
  caixa.classList.replace("flex", "hidden");
  const entrada = entradaActual();
  if (!entrada || !entrada.versio_id) return;
  const mesNova = entrada.versio_numero < entrada.versio_ultima || entrada.esborrany_modificat;
  avisa(`Aquest cançoner fa servir la versió ${entrada.versio_numero} d'aquesta cançó, fixada.` +
    (mesNova ? " N'hi ha una de més nova." : "") + " Si l'edites, aquest cançoner passarà a fer servir sempre l'última versió.", [
    ["Edita la cançó", async () => { await canviaEntrada(entrada.id, { versio_id: null }); await obre(obert, { forca: true }); }, true],
    ...(mesNova ? [["Fes servir l'última versió", async () => {
      await api(`${urls.canco}${entrada.id}/versions`, "POST", { nota: "" });
      const { versions } = await api(`${urls.canco}${entrada.id}/versions`);
      await canviaEntrada(entrada.id, { versio_id: versions[0].id });
      await obre(obert, { forca: true });
    }]] : []),
  ]);
}

// ------------------------------------------------------------ Llista (llibret, cançons, mestres)

function pintaLlista() {
  $("#compte-cancons").textContent = K.cancons.length ? `${K.cancons.filter((c) => c.inclosa).length}/${K.cancons.length}` : "";
  $$("[data-obre]").forEach((b) => b.setAttribute("aria-current", String(b.dataset.obre === `${obert?.tipus === "llibre" ? "llibre" : `${obert?.tipus}:${obert?.id}`}`)));
  const llista = $("#llista-ev");
  llista.replaceChildren(...K.cancons.map((c, i) => {
    const p = PLA?.cancons.find((x) => x.id === c.id);
    const numeros = PLA?.pagines.filter((x) => x.entrada === c.id).map((x) => x.numero) || [];
    const actiu = obert?.tipus === "canco" && obert.id === c.id;
    const li = el("li", {
      classe: "group relative flex items-center rounded-md transition " + (actiu ? "bg-white shadow-suau ring-1 ring-paper-300" : "hover:bg-paper-200/70") + (c.inclosa ? "" : " opacity-60"),
      atributs: { "data-id": c.id },
    });
    if (actiu) li.append(el("span", { classe: "absolute inset-y-2 left-0 w-0.5 rounded-full bg-vermello-500" }));
    li.append(el("span", { text: "⠿", classe: "nansa flex w-4 shrink-0 cursor-grab touch-none select-none items-center justify-center self-stretch text-ink-300 opacity-0 transition group-hover:opacity-100 max-lg:opacity-100", atributs: { title: "Arrossega per reordenar" } }));
    const casella = el("input", { classe: "h-3.5 w-3.5 shrink-0 cursor-pointer accent-vermello-500", atributs: { type: "checkbox", title: "Surt al PDF" } });
    casella.checked = c.inclosa;
    casella.addEventListener("change", () => canviaEntrada(c.id, { inclosa: casella.checked }));
    const boto = el("button", { classe: "flex min-w-0 flex-1 items-center gap-2 py-1.5 pl-2 pr-1 text-left", atributs: { type: "button" } });
    const textos = el("span", { classe: "flex min-w-0 flex-1 flex-col" });
    const lliure = c.tipus === "pagina";
    textos.append(el("span", { text: `${lliure ? "▫ " : ""}${c.titol || "Sense títol"}`, classe: "truncate text-[13.5px] " + (actiu ? "font-semibold text-ink-900" : "font-medium text-ink-700") + (lliure ? " italic" : "") }));
    const meta = el("span", { classe: "flex items-center gap-1.5 text-[11px] text-ink-400" });
    if (numeros.length) meta.append(el("span", { text: numeros.length > 1 ? `pàg. ${numeros[0]}–${numeros.at(-1)}` : `pàg. ${numeros[0]}` }));
    else if (!c.inclosa) meta.append(el("span", { text: "fora del PDF" }));
    if (c.inici === "qualsevol" && !lliure) meta.append(el("span", { text: "↦", atributs: { title: "Comença on toqui" } }));
    if (c.versio_id) {
      const desfasada = c.versio_numero < c.versio_ultima || c.esborrany_modificat;
      meta.append(el("span", { text: `v${c.versio_numero}${desfasada ? " ↑" : ""}`, classe: "rounded bg-sky-100 px-1 font-mono text-[10px] text-sky-900", atributs: { title: "Versió fixada" } }));
    }
    if (c.usos > 1) meta.append(el("span", { text: `${c.usos}×`, atributs: { title: "És en més d'un cançoner" } }));
    textos.append(meta);
    boto.append(textos);
    void p;
    boto.addEventListener("click", () => obre({ tipus: "canco", id: c.id }));
    const moure = el("span", { classe: "flex shrink-0 flex-col opacity-0 transition focus-within:opacity-100 group-hover:opacity-100 max-lg:opacity-100" });
    for (const [d, cami, t] of [[-1, "M4 10l4-4 4 4", "Mou amunt"], [1, "M4 6l4 4 4-4", "Mou avall"]]) {
      const b = el("button", { classe: "flex h-4 w-5 items-center justify-center rounded text-ink-400 hover:bg-paper-300 hover:text-ink-900 disabled:invisible", atributs: { type: "button", "aria-label": t, title: t } });
      b.innerHTML = `<svg class="h-3 w-3" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="${cami}"/></svg>`;
      b.disabled = (d < 0 && i === 0) || (d > 0 && i === K.cancons.length - 1);
      b.addEventListener("click", () => mouEntrada(c.id, d));
      moure.append(b);
    }
    li.append(casella, boto, moure);
    return li;
  }));

  const mestres = $("#llista-mestres");
  mestres.replaceChildren(...K.mestres.map((m) => {
    const actiu = obert?.tipus === "mestra" && obert.id === m.id;
    const b = el("button", { classe: "item-llista w-full", atributs: { type: "button", "aria-current": String(actiu) } });
    b.append(el("span", { text: "M", classe: "flex h-4 w-4 shrink-0 items-center justify-center rounded bg-paper-300 font-mono text-[9px] font-bold text-ink-700" }),
      el("span", { text: m.nom, classe: "flex-1 truncate text-left" }));
    b.addEventListener("click", () => obre({ tipus: "mestra", id: m.id }));
    const li = el("li");
    li.append(b);
    return li;
  }));
  $("#total-pagines").textContent = PLA ? `${PLA.total} pàg.` : "";
}

$$("[data-obre]").forEach((b) => b.addEventListener("click", () => {
  const [tipus, id] = b.dataset.obre.split(":");
  obre(tipus === "llibre" ? { tipus: "llibre" } : { tipus, id });
}));

async function canviaEntrada(id, canvis) {
  try {
    await api(urls.entrada + id, "PATCH", canvis);
  } catch (e) {
    return mostraEstat("No s'ha pogut desar", "error");
  }
  Object.assign(K.cancons.find((c) => c.id === id) || {}, canvis);
  [K, PLA] = await Promise.all([api(urls.canconer), api(urls.pla)]);
  pintaLlista();
  if (obert?.tipus === "canco" && obert.id === id && ("transport" in canvis || "inici" in canvis)) pintaLlenc();
  pintaCanco();
}

async function desaOrdre(ordre) {
  if (ordre.join() === K.cancons.map((c) => c.id).join()) return;
  K.cancons = ordre.map((id) => K.cancons.find((c) => c.id === id));
  pintaLlista();
  try {
    await api(urls.ordre, "POST", { ordre });
  } catch {
    return mostraEstat("No s'ha pogut desar l'ordre", "error");
  }
  refrescaPla();
  if (obert?.tipus === "canco") setTimeout(pintaLlenc, 500);
}

function mouEntrada(id, d) {
  const ordre = K.cancons.map((c) => c.id);
  const i = ordre.indexOf(id);
  if (i + d < 0 || i + d >= ordre.length) return;
  [ordre[i], ordre[i + d]] = [ordre[i + d], ordre[i]];
  desaOrdre(ordre);
}

(function arrossegarLlista() {
  const llista = $("#llista-ev");
  let arrossegat = null;
  llista.addEventListener("pointerdown", (ev) => {
    const nansa = ev.target.closest(".nansa");
    if (!nansa) return;
    arrossegat = nansa.closest("li");
    arrossegat.classList.add("arrossegant");
    nansa.setPointerCapture(ev.pointerId);
    ev.preventDefault();
  });
  llista.addEventListener("pointermove", (ev) => {
    if (!arrossegat) return;
    const seguent = [...llista.children].filter((li) => li !== arrossegat).find((li) => ev.clientY < li.getBoundingClientRect().top + li.offsetHeight / 2);
    llista.insertBefore(arrossegat, seguent || null);
  });
  const deixa = () => {
    if (!arrossegat) return;
    arrossegat.classList.remove("arrossegant");
    arrossegat = null;
    desaOrdre([...llista.children].map((li) => li.dataset.id));
  };
  llista.addEventListener("pointerup", deixa);
  llista.addEventListener("pointercancel", deixa);
})();

// ------------------------------------------------------------ Obrir una cançó, una pàgina especial o una mestra

async function obre(desti, { forca = false } = {}) {
  if (!forca && obert && desti.tipus === obert.tipus && desti.id === obert.id) return;
  sortEdicio();
  await desa();
  obert = desti;
  seleccio = null;
  canco = null;
  editable = true;
  tancaHistorial();
  const params = new URLSearchParams();
  if (desti.tipus === "canco") {
    const entrada = entradaActual();
    if (entrada?.versio_id) {
      // Versió fixada en aquest cançoner: es mostra tal com és, en només lectura.
      editable = false;
      pagines = copia(entrada.contingut.pagines);
      canco = { id: entrada.id, titol: entrada.titol, autor: entrada.autor, contingut: entrada.contingut };
    } else {
      const c = await api(urls.canco + desti.id);
      if (obert !== desti) return;
      canco = c;
      pagines = c.contingut.pagines;
    }
    params.set("canco", desti.id);
  } else if (desti.tipus === "especial") {
    pagines = [K.especials[desti.id]];
    params.set("especial", desti.id);
  } else if (desti.tipus === "mestra") {
    const m = K.mestres.find((x) => x.id === desti.id);
    pagines = [m.parell, m.senar];
  } else {
    pagines = [];
  }
  history.replaceState(null, "", params.size ? `?${params}` : location.pathname);
  $("#barra-llenc").classList.toggle("eines-inactives", !editable || desti.tipus === "llibre");
  $$('[data-eina^="pagina-"]').forEach((b) => (b.disabled = desti.tipus !== "canco" || !editable));
  pintaLlista();
  pintaCanco();
  if (desti.tipus === "canco" && esMobil()) mostraPanell("panell-llenc");
  await pintaLlenc();
}

const esMobil = () => window.matchMedia("(max-width: 1023px)").matches;

// ------------------------------------------------------------ Pestanya Cançó

function pintaCanco() {
  const entrada = entradaActual();
  $("#sense-canco").classList.toggle("hidden", !!entrada);
  $("#dades-canco").classList.toggle("hidden", !entrada);
  if (!entrada || !canco) return;
  $("#titol-ev").value = canco.titol || "";
  $("#autor-ev").value = canco.autor || "";
  $("#titol-ev").readOnly = $("#autor-ev").readOnly = !editable;
  const n = Number(entrada.transport || 0);
  $("#valor-transport").textContent = n > 0 ? `+${n}` : String(n);
  $("#aplica-transport").disabled = !n || !editable;
  $("#inclosa-ev").checked = entrada.inclosa;
  $("#inici-ev").checked = entrada.inici !== "qualsevol";
  pintaVideos();
  $("#etiqueta-versio").textContent = entrada.versio_id ? `v${entrada.versio_numero} fixada` : entrada.versio_ultima ? `${entrada.versio_ultima} versions` : "";
}

// Selectors de color (CMYK exacte per a impremta, o RGB)

/** Colors que ja fa servir el cançoner (estils i pàgina oberta), per oferir-los al selector. */
function colorsDelDocument() {
  const trobats = Object.values(K.estils).map((e) => e.color);
  for (const p of pagines) {
    trobats.push(p.fons);
    for (const e of p.elements) trobats.push(e.color, e.fons, e.vora, e.format?.color);
  }
  return trobats.filter((c) => c && c !== "#ffffff");
}
selectorColor($("#fons-pagina"), { colors: colorsDelDocument });
selectorColor($('[data-format-prop="color"]'), { colors: colorsDelDocument, buit: "Color de l'estil",
  perDefecte: () => (typeof K !== "undefined" && seleccio ? K.estils[elementSel()?.estil]?.color : undefined) });
selectorColor($('[data-per="qr"] [data-prop="color"]'), { colors: colorsDelDocument });
selectorColor($('[data-prop="fons"]'), { colors: colorsDelDocument, buit: "Sense fons" });
selectorColor($('[data-prop="vora"]'), { colors: colorsDelDocument, buit: "Sense vora" });

// Vídeos de YouTube de la cançó (es desen amb el contingut i es versionen amb ella)

function videosCanco() {
  return canco?.contingut?.videos || [];
}

const urlCurta = (v) => `https://youtu.be/${v.video}${v.inici ? `?t=${v.inici}` : ""}`;

function videosPerDibuixar() {
  return videosCanco().map((v) => ({ id: v.id, titol: v.titol, url: urlCurta(v) }));
}

function canviaVideos(llista) {
  if (!canco || !editable) return;
  canco.contingut = { ...(canco.contingut || {}), videos: llista };
  canviat();
  pintaVideos();
  pintaLlenc();
}

function omplenaVideosQR(e) {
  const llista = videosCanco();
  $("#video-qr").replaceChildren(...(llista.length
    ? llista.map((v, i) => el("option", { text: v.titol || `Vídeo ${i + 1}`, atributs: { value: v.id } }))
    : [el("option", { text: "La cançó no té cap vídeo", atributs: { value: "" } })]));
  const costat = Math.min(e.w, e.h - (e.peu ? 4.5 : 0));
  const avis = $("#avis-qr");
  avis.classList.toggle("hidden", costat >= QR_MINIM && llista.length > 0);
  avis.textContent = !llista.length
    ? "Afegeix un vídeo a la pestanya Cançó."
    : `El codi fa ${costat.toFixed(1)} mm. Per escanejar-lo bé, fes-lo de ${QR_MINIM} mm o més.`;
}

function pintaVideos() {
  const llista = videosCanco();
  $("#nou-video").classList.toggle("hidden", !editable);
  $("#llista-videos").replaceChildren(...llista.map((v, i) => {
    const li = el("li", { classe: "flex gap-2 rounded-md border border-paper-300 bg-white p-1.5" });
    const mini = el("button", { classe: "relative h-12 w-20 shrink-0 overflow-hidden rounded bg-ink-900", atributs: { type: "button", title: "Mira el vídeo" } });
    const img = el("img", { classe: "h-full w-full object-cover", atributs: { src: `https://i.ytimg.com/vi/${v.video}/mqdefault.jpg`, alt: "", loading: "lazy" } });
    img.addEventListener("error", () => img.remove()); // sense connexió
    mini.append(img, el("span", { text: "▶", classe: "absolute inset-0 flex items-center justify-center text-white drop-shadow" }));
    mini.addEventListener("click", () => mostraVideo(v));
    const cos = el("div", { classe: "flex min-w-0 flex-1 flex-col gap-1" });
    const titol = el("input", { classe: "camp px-2 py-1 text-[13px]", atributs: { value: v.titol, placeholder: "Títol del vídeo", "aria-label": "Títol del vídeo" } });
    titol.readOnly = !editable;
    titol.addEventListener("change", () => canviaVideos(videosCanco().map((x) => (x.id === v.id ? { ...x, titol: titol.value } : x))));
    const fila = el("div", { classe: "flex items-center gap-1 text-[12px] text-ink-500" });
    const qr = el("input", { classe: "h-3.5 w-3.5 accent-vermello-500", atributs: { type: "checkbox", title: "Surt a l'índex de vídeos" } });
    qr.checked = v.inclou_qr;
    qr.disabled = !editable;
    qr.addEventListener("change", () => canviaVideos(videosCanco().map((x) => (x.id === v.id ? { ...x, inclou_qr: qr.checked } : x))));
    const etiqueta = el("label", { classe: "flex flex-1 items-center gap-1" });
    etiqueta.append(qr, el("span", { text: v.inici ? `A l'índex · des de ${Math.floor(v.inici / 60)}:${String(v.inici % 60).padStart(2, "0")}` : "A l'índex" }));
    fila.append(etiqueta);
    if (editable) {
      for (const [text, desp, titolBoto] of [["↑", -1, "Puja"], ["↓", 1, "Baixa"]]) {
        const b = el("button", { text, classe: "btn btn-fantasma h-6 min-h-0 w-6 px-0 text-[12px]", atributs: { type: "button", title: titolBoto } });
        b.disabled = !llista[i + desp];
        b.addEventListener("click", () => {
          const nova = [...videosCanco()];
          [nova[i], nova[i + desp]] = [nova[i + desp], nova[i]];
          canviaVideos(nova);
        });
        fila.append(b);
      }
      const treu = el("button", { text: "✕", classe: "btn btn-perill h-6 min-h-0 w-6 px-0 text-[12px]", atributs: { type: "button", title: "Treu el vídeo" } });
      treu.addEventListener("click", () => {
        if (confirm(`Vols treure «${v.titol || urlCurta(v)}»? Els QR que hi apunten quedaran buits.`)) canviaVideos(videosCanco().filter((x) => x.id !== v.id));
      });
      fila.append(treu);
    }
    cos.append(titol, fila);
    li.append(mini, cos);
    return li;
  }));
}

function mostraVideo(v) {
  $("#titol-dialeg-video").textContent = v.titol || urlCurta(v);
  $("#reproductor-video").src = `https://www.youtube-nocookie.com/embed/${v.video}?autoplay=1${v.inici ? `&start=${v.inici}` : ""}`;
  $("#dialeg-video").showModal();
}
$("#dialeg-video").addEventListener("close", () => { $("#reproductor-video").src = "about:blank"; });

$("#nou-video").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const error = $("#error-video");
  error.classList.add("hidden");
  const boto = ev.target.querySelector("button");
  boto.disabled = true;
  try {
    const r = await fetch(urls.video, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url: $("#url-video").value }) });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || "No s'ha pogut afegir el vídeo.");
    if (videosCanco().some((x) => x.video === d.video.video && x.inici === d.video.inici)) throw new Error("Aquest vídeo ja hi és.");
    canviaVideos([...videosCanco(), d.video]);
    $("#url-video").value = "";
  } catch (e) {
    error.textContent = e.message;
    error.classList.remove("hidden");
  } finally {
    boto.disabled = false;
  }
});

for (const [camp, prop] of [["#titol-ev", "titol"], ["#autor-ev", "autor"]]) {
  $(camp).addEventListener("input", (ev) => {
    if (!canco || !editable) return;
    canco[prop] = ev.target.value;
    canviat();
    actualitzaVariables();
    const fila = $(`#llista-ev li[data-id="${canco.id}"] .truncate`);
    if (fila && prop === "titol") fila.textContent = ev.target.value || "Sense títol";
  });
}
$$("[data-transport]").forEach((b) => b.addEventListener("click", () => {
  const entrada = entradaActual();
  if (!entrada) return;
  let n = Number(entrada.transport || 0) + Number(b.dataset.transport);
  if (n > 11) n -= 12;
  if (n < -11) n += 12;
  canviaEntrada(entrada.id, { transport: n });
}));
$("#aplica-transport").addEventListener("click", async () => {
  const entrada = entradaActual();
  if (!entrada?.transport || !editable) return;
  const { contingut } = await api(urls.transporta, "POST", { contingut: { format: 2, pagines, videos: videosCanco() }, semitons: entrada.transport });
  foto(true);
  substitueixPagines(contingut.pagines);
  await api(urls.canco + canco.id, "PUT", { contingut });
  await canviaEntrada(entrada.id, { transport: 0 });
  pintaLlenc();
});
$("#inclosa-ev").addEventListener("change", (ev) => canviaEntrada(obert.id, { inclosa: ev.target.checked }));
$("#inici-ev").addEventListener("change", (ev) => canviaEntrada(obert.id, { inici: ev.target.checked ? "esquerra" : "qualsevol" }));
$("#treu-canco").addEventListener("click", async () => {
  const entrada = entradaActual();
  if (!entrada) return;
  const on = entrada.usos > 1 ? "Continuarà als altres cançoners on surt i a la biblioteca." : "Continuarà a la biblioteca.";
  if (!confirm(`Vols treure «${entrada.titol || "Sense títol"}» d'aquest cançoner? ${on}`)) return;
  await desa();
  await api(urls.entrada + entrada.id, "DELETE");
  [K, PLA] = await Promise.all([api(urls.canconer), api(urls.pla)]);
  obert = null;
  await obre(K.cancons[0] ? { tipus: "canco", id: K.cancons[0].id } : { tipus: "especial", id: "portada" });
});

// Noves cançons, pàgines lliures i importació
async function creaEntrada(tipus, mestra) {
  if (mestra === undefined && K.mestres.length > 1) return triaPlantilla(tipus);
  await desa();
  const despres = obert?.tipus === "canco" ? obert.id : undefined;
  const r = await api(urls.nova, "POST", { tipus, despres_de: despres, mestra: mestra || undefined });
  [K, PLA] = await Promise.all([api(urls.canconer), api(urls.pla)]);
  await obre({ tipus: "canco", id: r.id });
  mostraPestanya("canco");
  $("#titol-ev").select();
}
$("#nova-canco").addEventListener("click", () => creaEntrada("canco"));

/** Miniatura d'una pàgina mestra (un costat), per triar-la d'un cop d'ull. */
function miniaturaMestra(costat, numero, mida = 0.22) {
  const caixa = el("div", { classe: "miniatura-mestra" });
  caixa.style.width = `${AMPLE * PX_MM * mida}px`;
  caixa.style.height = `${ALT * PX_MM * mida}px`;
  const pagina = dibuixaPagina({ fons: "#ffffff", elements: [], mestra: costat,
    context: { ...contextDe(numero), titol: "Títol de la cançó", autor: "Autor", acords: "C · G · Am · F", pagina: numero } },
  { urlImatge: (id) => urls.imatge + id, grup: "miniatura" });
  pagina.style.transform = `scale(${mida})`;
  pagina.style.transformOrigin = "0 0";
  caixa.append(pagina);
  return caixa;
}

const dialegPlantilla = $("#dialeg-plantilla");
function triaPlantilla(tipus) {
  $("#titol-plantilla").textContent = tipus === "pagina" ? "Plantilla de la pàgina nova" : "Plantilla de la cançó nova";
  // Per defecte, la mestra de la pàgina oberta (si en té).
  const actual = obert?.tipus === "canco" ? pagines[paginaActual()]?.mestra : null;
  const opcions = [...K.mestres.map((m) => ({ id: m.id, nom: m.nom, m })), { id: "", nom: "Cap (pàgina neta)", m: null }];
  $("#llista-plantilles").replaceChildren(...opcions.map(({ id, nom, m }) => {
    const b = el("button", { classe: "targeta-plantilla", atributs: { type: "button", "aria-current": String(id === (actual ?? "estandard")) } });
    const parella = el("span", { classe: "flex justify-center gap-px" });
    parella.append(miniaturaMestra(m?.parell, 2), miniaturaMestra(m?.senar, 3));
    b.append(parella, el("span", { text: nom, classe: "truncate text-[14px] font-medium" }));
    b.addEventListener("click", () => { dialegPlantilla.close(); creaEntrada(tipus, id || null); });
    const li = el("li");
    li.append(b);
    return li;
  }));
  dialegPlantilla.showModal();
}
$("#nova-pagina").addEventListener("click", () => creaEntrada("pagina"));

const dialegImporta = $("#dialeg-importa");
const seleccionades = new Set();
async function cercaBiblioteca() {
  const { cancons } = await api(`${urls.biblioteca}?q=${encodeURIComponent($("#cerca-biblioteca").value)}`);
  const presents = new Set(K.cancons.map((c) => c.id));
  const ul = $("#resultats-biblioteca");
  if (!cancons.length) return ul.replaceChildren(el("li", { text: "No hi ha cap cançó que coincideixi.", classe: "px-5 py-6 text-center text-[14px] text-ink-500" }));
  ul.replaceChildren(...cancons.map((r) => {
    const ja = presents.has(r.id);
    const li = el("li", { classe: "border-b border-paper-200 last:border-b-0" });
    const etiqueta = el("label", { classe: "flex cursor-pointer items-center gap-3 px-5 py-2.5 hover:bg-paper-100" + (ja ? " opacity-50" : "") });
    const casella = el("input", { classe: "h-4 w-4 accent-vermello-500", atributs: { type: "checkbox" } });
    casella.disabled = ja;
    casella.checked = seleccionades.has(r.id);
    casella.addEventListener("change", () => {
      casella.checked ? seleccionades.add(r.id) : seleccionades.delete(r.id);
      $("#compte-seleccio").textContent = seleccionades.size ? `${seleccionades.size} seleccionades` : "";
      $("#confirma-importa").disabled = !seleccionades.size;
    });
    const textos = el("span", { classe: "flex min-w-0 flex-1 flex-col" });
    textos.append(el("span", { text: r.titol || "Sense títol", classe: "truncate text-[14px] font-medium" }),
      el("span", { text: [r.autor, r.canconers.map((k) => k.titol).join(", ")].filter(Boolean).join(" · ") || "Sense cançoner", classe: "truncate text-[12px] text-ink-500" }));
    etiqueta.append(casella, textos, el("span", { text: ja ? "ja hi és" : r.ultima ? `v${r.ultima}` : "", classe: "font-mono text-[11px] text-ink-400" }));
    li.append(etiqueta);
    return li;
  }));
}
$("#cerca-biblioteca").addEventListener("input", () => { clearTimeout(cercaBiblioteca.t); cercaBiblioteca.t = setTimeout(cercaBiblioteca, 200); });
function mostraPestanyaImporta(nom) {
  $$("[data-pestanya-importa]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.pestanyaImporta === nom)));
  $$("[data-panell-importa]").forEach((p) => p.classList.toggle("hidden", p.dataset.panellImporta !== nom));
  if (nom === "biblioteca") { cercaBiblioteca(); $("#cerca-biblioteca").focus(); } else $("#importa-titol").focus();
}
$$("[data-pestanya-importa]").forEach((b) => b.addEventListener("click", () => mostraPestanyaImporta(b.dataset.pestanyaImporta)));

$("#importa-text").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  await desa();
  const r = await api(urls.nova, "POST", {
    titol: $("#importa-titol").value, autor: $("#importa-autor").value, text: $("#importa-cos").value,
    despres_de: obert?.tipus === "canco" ? obert.id : undefined,
  });
  dialegImporta.close();
  for (const id of ["#importa-titol", "#importa-autor", "#importa-cos"]) $(id).value = "";
  [K, PLA] = await Promise.all([api(urls.canconer), api(urls.pla)]);
  await obre({ tipus: "canco", id: r.id });
});

$("#obre-importa").addEventListener("click", () => {
  seleccionades.clear();
  $("#compte-seleccio").textContent = "";
  $("#confirma-importa").disabled = true;
  $("#cerca-biblioteca").value = "";
  dialegImporta.showModal();
  mostraPestanyaImporta("text");
});
$("#confirma-importa").addEventListener("click", async () => {
  const ids = [...seleccionades];
  await desa();
  await api(urls.importa, "POST", { cancons: ids, despres_de: obert?.tipus === "canco" ? obert.id : undefined });
  dialegImporta.close();
  [K, PLA] = await Promise.all([api(urls.canconer), api(urls.pla)]);
  if (ids.length) await obre({ tipus: "canco", id: ids[0] });
});
$$("[data-tanca-dialeg]").forEach((b) => b.addEventListener("click", () => b.closest("dialog").close()));

// ------------------------------------------------------------ Pàgines mestres

$("#nova-mestra").addEventListener("click", async () => {
  const nom = prompt("Nom de la pàgina mestra nova:", "Mestra nova");
  if (!nom) return;
  await desa();
  const id = "m" + nouId();
  const base = copia(K.mestres.find((m) => m.id === "estandard"));
  K.mestres.push({ id, nom, parell: base.parell, senar: base.senar });
  await api(urls.disseny, "PUT", { mestres: K.mestres });
  await obre({ tipus: "mestra", id });
});
$("#nom-mestra").addEventListener("input", (ev) => {
  const m = K.mestres.find((x) => x.id === obert?.id);
  if (!m) return;
  m.nom = ev.target.value || "Mestra";
  canviat();
  pintaLlista();
});
$("#duplica-mestra").addEventListener("click", async () => {
  const m = K.mestres.find((x) => x.id === obert?.id);
  if (!m) return;
  if (K.mestres.length >= 20) return alert("Com a màxim hi pot haver 20 pàgines mestres.");
  await desa();
  const id = nouId();
  K.mestres.push({ ...copia(m), id, nom: `${m.nom} (còpia)` });
  await api(urls.disseny, "PUT", { mestres: K.mestres });
  await obre({ tipus: "mestra", id });
});

const dialegCopia = $("#dialeg-copia-mestres");
let altresCanconers = [];
function pintaMestresOrigen() {
  const origen = altresCanconers.find((k) => k.id === $("#origen-mestres").value);
  const ul = $("#mestres-origen");
  $("#confirma-copia-mestres").disabled = true;
  if (!origen) return ul.replaceChildren();
  ul.replaceChildren(...origen.mestres.map((m) => {
    const li = el("li");
    const etiqueta = el("label", { classe: "flex cursor-pointer items-center gap-3 rounded-md px-2 py-1.5 hover:bg-paper-100" });
    const casella = el("input", { classe: "h-4 w-4 accent-vermello-500", atributs: { type: "checkbox", value: m.id } });
    casella.addEventListener("change", () => { $("#confirma-copia-mestres").disabled = !ul.querySelector("input:checked"); });
    const parella = el("span", { classe: "flex gap-px" });
    // Les miniatures es dibuixen amb els estils d'aquest cançoner: és com quedaran un cop copiades.
    parella.append(miniaturaMestra(m.parell, 2, 0.16), miniaturaMestra(m.senar, 3, 0.16));
    etiqueta.append(casella, parella, el("span", { text: m.nom, classe: "flex-1 truncate text-[14px]" }));
    li.append(etiqueta);
    return li;
  }));
}
$("#copia-mestres").addEventListener("click", async () => {
  ({ canconers: altresCanconers } = await api(urls.mestresAltres));
  const select = $("#origen-mestres");
  select.replaceChildren(...(altresCanconers.length
    ? altresCanconers.map((k) => el("option", { text: `${k.titol} (${k.mestres.length})`, atributs: { value: k.id } }))
    : [el("option", { text: "No hi ha cap altre cançoner", atributs: { value: "" } })]));
  pintaMestresOrigen();
  dialegCopia.showModal();
});
$("#origen-mestres").addEventListener("change", pintaMestresOrigen);
$("#confirma-copia-mestres").addEventListener("click", async () => {
  const ids = [...$("#mestres-origen").querySelectorAll("input:checked")].map((c) => c.value);
  await desa();
  const r = await api(urls.mestresCopia, "POST", { de: $("#origen-mestres").value, mestres: ids });
  dialegCopia.close();
  [K, PLA] = await Promise.all([api(urls.canconer), api(urls.pla)]);
  aplicaEstils(K.estils);
  if (r.noves.length) await obre({ tipus: "mestra", id: r.noves[0] });
  else pintaLlista();
});

$("#esborra-mestra").addEventListener("click", async () => {
  if (obert?.tipus !== "mestra" || obert.id === "estandard") return;
  if (!confirm("Vols esborrar aquesta pàgina mestra? Les pàgines que la fan servir es quedaran sense mestra.")) return;
  K.mestres = K.mestres.filter((m) => m.id !== obert.id);
  pendent = false;
  await api(urls.disseny, "PUT", { mestres: K.mestres });
  [K, PLA] = await Promise.all([api(urls.canconer), api(urls.pla)]);
  obert = null;
  await obre({ tipus: "mestra", id: "estandard" });
});

// ------------------------------------------------------------ Estils

function pintaEstils() {
  const ul = $("#llista-estils");
  ul.replaceChildren(...Object.entries(K.estils).map(([clau, e]) => {
    const li = el("li", { classe: "rounded-md border border-paper-300 bg-white" });
    const det = el("details", { classe: "group" });
    const resum = el("summary", { classe: "flex items-center gap-3 px-3 py-2" });
    const mostra = el("span", { text: "Aa", classe: "w-8 shrink-0 text-center" });
    Object.assign(mostra.style, { fontFamily: FONTS[e.font], fontWeight: e.pes, fontStyle: e.cursiva ? "italic" : "normal", color: colorCss(e.color), fontSize: "18px" });
    resum.append(mostra, el("span", { text: e.nom, classe: "flex-1 text-[14px] font-medium" }), el("span", { text: `${e.mida} pt`, classe: "font-mono text-[11px] text-ink-400" }));
    const cos = el("div", { classe: "grid grid-cols-2 gap-3 border-t border-paper-200 p-3" });
    const filaFont = el("div", { classe: "col-span-2" });
    const botoFont = el("button", { classe: "selector-font", atributs: { type: "button", "data-selector-font": "estil" } });
    const nomFont = el("span", { text: TIPOGRAFIES.find((f) => f.clau === e.font)?.nom || e.font, classe: "nom-font" });
    nomFont.style.fontFamily = FONTS[e.font] || "";
    botoFont.append(nomFont);
    botoFont.addEventListener("click", () => obreSelectorFont(botoFont, {
      actual: e.font,
      tria: (clau) => {
        e.font = clau;
        aplicaEstils(K.estils);
        reajusta();
        desaEstils();
        pintaEstils();
        pintaLlenc();
      },
    }));
    filaFont.append(el("span", { text: "Tipografia", classe: "etiqueta" }), botoFont);
    cos.append(filaFont);
    const camps = [
      ["mida", "Mida (pt)", "number", 0.5], ["pes", "Gruix", "select", [300, 400, 500, 600, 700, 800].map((v) => [v, v])],
      ["interlineat", "Interlineat", "number", 0.05], ["espaiat", "Espaiat", "number", 0.01], ["color", "Color", "color"],
      ["cursiva", "Cursiva", "checkbox"], ["majuscules", "Majúscules", "checkbox"],
    ];
    for (const [prop, etiqueta, tipus, extra] of camps) {
      const label = el("label", { classe: tipus === "checkbox" ? "flex items-center gap-2 text-[13px]" : "" });
      let input;
      if (tipus === "select") {
        input = el("select", { classe: "camp py-1 text-[13px]" });
        input.append(...extra.map(([v, t]) => el("option", { text: String(t), atributs: { value: v } })));
        input.value = e[prop];
      } else {
        input = el("input", { classe: tipus === "checkbox" ? "h-4 w-4 accent-vermello-500" : tipus === "color" ? "h-8 w-full cursor-pointer rounded border border-paper-300 bg-white p-0.5" : "camp py-1 font-mono text-[13px]", atributs: { type: tipus } });
        if (tipus === "number") input.step = extra;
        if (tipus === "checkbox") input.checked = !!e[prop];
        else input.value = e[prop];
      }
      input.addEventListener("input", () => {
        e[prop] = tipus === "checkbox" ? input.checked : tipus === "number" || prop === "pes" ? Number(input.value) : input.value;
        aplicaEstils(K.estils);
        reajusta();
        desaEstils();
        Object.assign(mostra.style, { fontFamily: FONTS[e.font], fontWeight: e.pes, fontStyle: e.cursiva ? "italic" : "normal", color: colorCss(e.color) });
        resum.lastChild.textContent = `${e.mida} pt`;
      });
      if (tipus === "checkbox") label.append(input, el("span", { text: etiqueta }));
      else label.append(el("span", { text: etiqueta, classe: "etiqueta" }), input);
      cos.append(label);
      if (tipus === "color") selectorColor(input, { colors: colorsDelDocument });
    }
    det.append(resum, cos);
    li.append(det);
    return li;
  }));
}

// ------------------------------------------------------------ Biblioteca d'elements

async function pintaBiblioteca() {
  const { elements } = await api(urls.elements);
  const ul = $("#llista-elements");
  if (!elements.length) return ul.replaceChildren(el("li", { text: "Encara no n'hi ha cap. Selecciona un element i prem «Desa l'element a la biblioteca».", classe: "col-span-2 text-[13px] text-ink-500" }));
  ul.replaceChildren(...elements.map((item) => {
    const li = el("li", { classe: "group relative" });
    const boto = el("button", { classe: "flex w-full flex-col gap-1 rounded-md border border-paper-300 bg-white p-2 text-left transition hover:border-vermello-500", atributs: { type: "button", title: "Afegeix-lo a la pàgina" } });
    // Previsualització: els elements dins del seu requadre, escalats.
    const x0 = Math.min(...item.elements.map((e) => e.x));
    const y0 = Math.min(...item.elements.map((e) => e.y));
    const w = Math.max(...item.elements.map((e) => e.x + e.w)) - x0;
    const h = Math.max(...item.elements.map((e) => e.y + e.h)) - y0;
    const k = Math.min(120 / (w * PX_MM), 70 / (h * PX_MM));
    const vista = el("div", { classe: "relative mx-auto overflow-hidden" });
    vista.style.width = `${w * PX_MM * k}px`;
    vista.style.height = `${h * PX_MM * k}px`;
    const interior = el("div", { classe: "pagina" });
    Object.assign(interior.style, { position: "absolute", left: 0, top: 0, width: `${w}mm`, height: `${h}mm`, background: "transparent", transform: `scale(${k})`, transformOrigin: "0 0" });
    interior.append(...item.elements.map((e) => dibuixaElement({ ...e, x: e.x - x0, y: e.y - y0 }, { ...opcionsDibuix(), context: contextDe(1) })));
    vista.append(interior);
    boto.append(vista, el("span", { text: item.nom, classe: "truncate text-[12px] font-medium" }));
    boto.addEventListener("click", () => enganxaElements(item.elements, 0));
    const esborra = el("button", { text: "×", classe: "absolute right-1 top-1 hidden h-6 w-6 rounded bg-white text-ink-500 shadow-suau hover:text-vermello-600 group-hover:block", atributs: { type: "button", title: "Esborra de la biblioteca" } });
    esborra.addEventListener("click", async () => {
      if (!confirm(`Vols esborrar «${item.nom}» de la biblioteca?`)) return;
      await api(`${urls.elements}/${item.id}`, "DELETE");
      pintaBiblioteca();
    });
    li.append(boto, esborra);
    return li;
  }));
}

async function desaABiblioteca(elements, nomPerDefecte) {
  if (!elements?.length) return;
  const nom = prompt("Nom per a la biblioteca d'elements:", nomPerDefecte);
  if (!nom) return;
  await api(urls.elements, "POST", { nom, elements });
  mostraEstat("Desat a la biblioteca");
  mostraPestanya("biblioteca");
}
$("#selecciona-grup").addEventListener("click", () => { const e = elementSel(); if (e) selecciona(seleccio.p, e.id); });
$("#desa-multi-biblioteca").addEventListener("click", () => desaABiblioteca(copia(elementsSel()), "Grup"));
$("#desa-element-biblioteca").addEventListener("click", () => {
  const e = elementSel();
  if (e) desaABiblioteca([copia(e)], NOMS_TIPUS[e.tipus]);
});
$("#desa-pagina-biblioteca").addEventListener("click", () => desaABiblioteca(copia(pagines[paginaActual()]?.elements || []), "Pàgina"));

// ------------------------------------------------------------ Historial de versions

function tancaHistorial() {
  $("#historial").classList.add("hidden");
}

async function obreHistorial() {
  const entrada = entradaActual();
  if (!entrada) return;
  await desa();
  $("#historial").classList.remove("hidden");
  $("#previsualitzacio-versio").classList.add("hidden");
  await pintaVersions();
}

async function pintaVersions() {
  const entrada = entradaActual();
  const { versions, esborrany_modificat: modificat } = await api(`${urls.canco}${entrada.id}/versions`);
  const items = [];
  const liE = el("li", { classe: "flex items-center gap-3 border-b border-paper-200 px-5 py-3" });
  const t = el("div", { classe: "min-w-0 flex-1" });
  t.append(el("p", { text: "Esborrany actual", classe: "text-[14px] font-semibold" }), el("p", { text: modificat ? "Té canvis que encara no són a cap versió." : "Igual que l'última versió.", classe: "text-[12px] text-ink-500" }));
  liE.append(el("span", { text: "✎", classe: "flex h-7 w-7 items-center justify-center rounded-full bg-paper-200" }), t);
  if (entrada.versio_id) {
    const b = el("button", { text: "Fes-lo servir aquí", classe: "btn btn-petit", atributs: { type: "button" } });
    b.addEventListener("click", async () => { await canviaEntrada(entrada.id, { versio_id: null }); await obre(obert, { forca: true }); });
    liE.append(b);
  } else liE.append(el("span", { text: "en ús aquí", classe: "rounded bg-emerald-100 px-1.5 py-0.5 text-[11px] font-medium text-emerald-900" }));
  items.push(liE);
  if (!versions.length) items.push(el("li", { text: "Encara no hi ha cap versió desada. Es desen soles cada 10 minuts d'edició, o amb «Desa versió».", classe: "px-5 py-6 text-[13px] text-ink-500" }));
  for (const v of versions) {
    const li = el("li", { classe: "border-b border-paper-200" });
    const fila = el("button", { classe: "flex w-full items-center gap-3 px-5 py-3 text-left hover:bg-paper-100", atributs: { type: "button" } });
    const textos = el("div", { classe: "min-w-0 flex-1" });
    textos.append(el("p", { text: v.nota || v.titol, classe: "truncate text-[14px] font-medium" }),
      el("p", { text: new Date(v.creada).toLocaleString("ca", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }), classe: "text-[12px] text-ink-500" }));
    fila.append(el("span", { text: `v${v.numero}`, classe: "flex h-7 min-w-[1.75rem] items-center justify-center rounded-full bg-ink-900 px-1.5 font-mono text-[11px] font-semibold text-white" }), textos);
    if (entrada.versio_id === v.id) fila.append(el("span", { text: "fixada aquí", classe: "rounded bg-sky-100 px-1.5 py-0.5 text-[11px] font-medium text-sky-900" }));
    fila.addEventListener("click", () => mostraVersio(v, li));
    li.append(fila);
    items.push(li);
  }
  $("#llista-versions").replaceChildren(...items);
}

async function mostraVersio(v, li) {
  const detall = await api(urls.versio + v.id);
  const caixa = $("#previsualitzacio-versio");
  caixa.classList.remove("hidden");
  const fila = el("div", { classe: "flex gap-3" });
  const k = 0.32;
  await esperaFonts();
  for (const p of detall.contingut.pagines) {
    const marc = el("div", { classe: "relative shrink-0 overflow-hidden bg-white shadow-full" });
    marc.style.width = `${AMPLE * PX_MM * k}px`;
    marc.style.height = `${ALT * PX_MM * k}px`;
    const pagina = dibuixaPagina({ ...p, mestra: mestraDe(p.mestra, 2, p.costat), context: { ...contextDe(2), titol: detall.titol, autor: detall.autor } }, { ...opcionsDibuix(), grup: "versio" });
    pagina.style.transform = `scale(${k})`;
    pagina.style.transformOrigin = "0 0";
    marc.append(pagina);
    fila.append(marc);
  }
  const accions = el("div", { classe: "mt-3 flex flex-wrap gap-2" });
  const restaura = el("button", { text: `Restaura la v${v.numero}`, classe: "btn btn-petit", atributs: { type: "button" } });
  restaura.addEventListener("click", async () => {
    if (!confirm(`L'esborrany tornarà a ser com la v${v.numero}. L'estat actual es desarà abans com una versió nova. Continuar?`)) return;
    await api(`${urls.canco}${obert.id}/restaura`, "POST", { versio_id: v.id });
    [K, PLA] = await Promise.all([api(urls.canconer), api(urls.pla)]);
    await obre(obert, { forca: true });
  });
  const fixa = el("button", { text: "Fes-la servir en aquest cançoner", classe: "btn btn-primari btn-petit", atributs: { type: "button" } });
  fixa.addEventListener("click", async () => { await canviaEntrada(obert.id, { versio_id: v.id }); await obre(obert, { forca: true }); });
  accions.append(restaura, fixa);
  caixa.replaceChildren(fila, accions);
  ajustaMarcs(caixa, (id) => detall.contingut.pagines.flatMap((p) => p.elements).find((e) => e.id === id));
  $$("#llista-versions li").forEach((l) => l.classList.toggle("bg-paper-100", l === li));
}

$("#obre-historial").addEventListener("click", obreHistorial);
$("#historial").addEventListener("click", (ev) => {
  if (ev.target === $("#historial") || ev.target.closest("[data-tanca-historial]")) tancaHistorial();
});
$("#form-versio").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  await desa();
  await api(`${urls.canco}${obert.id}/versions`, "POST", { nota: $("#nota-versio").value });
  $("#nota-versio").value = "";
  await pintaVersions();
  refrescaPla();
});

// ------------------------------------------------------------ Panells del mòbil

function mostraPanell(id) {
  $$("[data-panell]").forEach((p) => (p.dataset.visible = String(p.id === id)));
  $$("[data-mostra]").forEach((b) => b.setAttribute("aria-current", String(b.dataset.mostra === id)));
  if (id === "panell-llenc") pintaLlenc();
}
$$("[data-mostra]").forEach((b) => b.addEventListener("click", () => mostraPanell(b.dataset.mostra)));

// ------------------------------------------------------------ Inici

[K, PLA] = await Promise.all([api(urls.canconer), api(urls.pla)]);
aplicaEstils(K.estils);
pintaLlista();
if (dades.especial && K.especials[dades.especial]) await obre({ tipus: "especial", id: dades.especial });
else if (K.cancons.some((c) => c.id === dades.actual)) await obre({ tipus: "canco", id: dades.actual });
else if (K.cancons.length) await obre({ tipus: "canco", id: K.cancons[0].id });
else await obre({ tipus: "especial", id: "portada" });
