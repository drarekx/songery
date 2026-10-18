// Editor de pàgines del cançoner. Les pàgines es dibuixen amb el mateix motor que la pàgina
// d'impressió que Gotenberg converteix en PDF: el que es veu aquí és exactament el que s'imprimeix.
import {
  ALT, AMPLE, FONTS, MARGE, acordsDePagines, acordsDelDocument, ajustaMarcs, aplicaEstils, arrodoneix, canviaMida,
  colorCss, dibuixaElement, dibuixaPagina, dinsRectangle, enganxa, esAcord, esperaFonts, gira as calculaGir,
  guies as guiesDe, midaEscalada, mou as calculaMoviment, novaSeleccio, posaAcord, posaMida, registraFonts,
  reposiciona, requadre, transportaAcord, transportaPagines, treuAcord,
} from "./dist/canconer.js";
import {
  TIPUS_ACORD, muntaAvisLlenc, muntaBarraEines, muntaBarraText, muntaMenuContext, muntaPanellAcords, muntaPanellCanco, muntaPanellCapes, muntaPanellEstils, muntaPanellLlista, muntaPanellPropietats, pinia, useEditorStore,
} from "./dist/vue.js";
import { avisa as avisaDialeg, confirma, pregunta } from "./dist/dialegs.js";

const dades = JSON.parse(document.getElementById("dades-editor").textContent);
const urls = dades.urls;
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const PX_MM = 96 / 25.4; // píxels CSS per mil·límetre a escala 1
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
    const visibles = transportaPagines(pagines, transport());
    const acords = acordsDePagines(visibles);
    const ordreAcords = [...new Set(acords.map(baseAcord))];
    demanaDiagrames([...ordreAcords, ...acordsSolts(visibles)]);
    return { ...base, titol: canco.titol, autor: canco.autor, acords: acords.join(" · "), videos: videosPerDibuixar(),
      ordreAcords, diagrames: DIAGRAMES };
  }
  if (obert.tipus === "mestra") return { ...base, titol: "Títol de la cançó", autor: "Autor", acords: "C · G · Am · F" };
  return base;
}

// ------------------------------------------------------------ Estat compartit amb els components Vue

// Els components Vue (panell d'acords, vídeos…) llegeixen l'estat de l'editor de l'store de Pinia;
// aquí s'hi escriu cada cop que canvia el que hi ha obert, i s'hi connecten les accions que encara
// fa aquest fitxer.
const store = useEditorStore(pinia);
function sincronitzaStore() {
  const esCanco = obert?.tipus === "canco" && !!canco;
  const entrada = entradaActual();
  store.sincronitza({
    editable,
    canco: esCanco ? { id: canco.id, titol: canco.titol || "", autor: canco.autor || "" } : null,
    entrada: entrada ? {
      transport: Number(entrada.transport || 0), inclosa: entrada.inclosa, inici: entrada.inici, usos: entrada.usos,
      versio_id: entrada.versio_id, versio_numero: entrada.versio_numero, versio_ultima: entrada.versio_ultima,
    } : null,
    acords: esCanco ? [...new Set(acordsDePagines(transportaPagines(pagines, transport())).map(baseAcord))] : [],
    diagrames: { ...DIAGRAMES },
    videos: esCanco ? copia(videosCanco()) : [],
    urls: { video: urls.video },
  });
  if (esCanco) demanaDiagrames(store.acords);
}
store.connecta({
  afegeixDiagrama: (nom) => afegeixDiagrama(nom),
  canviaVideos: (llista) => canviaVideos(llista),
  colorsDelDocument: () => colorsDelDocument(),
  // Pestanya Cançó
  canviaDadesCanco(prop, valor) {
    if (!canco || !editable) return;
    canco[prop] = valor;
    canviat();
    actualitzaVariables();
  },
  aplicaTransport,
  treuCanco,
  obreHistorial: () => obreHistorial(),
  // Estils
  canviaEstil(clau, prop, valor) {
    const e = K.estils[clau];
    if (!e) return;
    e[prop] = valor;
    aplicaEstils(K.estils);
    reajusta();
    desaEstils();
    if (prop === "font") pintaLlenc();
  },
  triaFont(boto, clau) {
    obreSelectorFont(boto, { actual: K.estils[clau]?.font, tria: (font) => store.canviaEstil(clau, "font", font) });
  },
  // Barres del llenç
  eina: (nom) => EINES[nom]?.(),
  zoom: (factor) => posaZoom(factor === null ? 1 : zoom * factor),
  ma() { ma.fixa = !ma.fixa; pintaMa(); },
  format: (nom) => edicio?.editor && FORMATS[nom]?.(edicio.editor),
  midaMarc: (mida) => canviaMidaMarc(mida),
  ajustaMarc: (ajusta) => canviaMidaMarc(undefined, ajusta),
  // Llista
  obre: (desti) => obre(desti),
  canviaEntrada: (id, canvis) => (typeof id === "string" ? canviaEntrada(id, canvis) : obert?.tipus === "canco" && canviaEntrada(obert.id, id)),
  mouEntrada: (id, d) => mouEntrada(id, d),
  desaOrdre: (ordre) => desaOrdre(ordre),
  creaEntrada: (tipus) => creaEntrada(tipus),
  obreImporta: () => obreImporta(),
  novaMestra: () => novaMestra(),
  copiaMestres: () => obreCopiaMestres(),
  // Propietats
  canviaPropietats: (propietats) => canviaPropietats(propietats),
  canviaPosicio,
  canviaPagina,
  accio: (nom) => accio(nom),
  alinea: (tipus) => alinea(tipus),
  gira,
  centra(eix) {
    const e = elementSel();
    if (e) canviaPropietats(eix === "x" ? { x: arrodoneix((AMPLE - e.w) / 2) } : { y: arrodoneix((ALT - e.h) / 2) });
  },
  seleccionaGrup() {
    const e = elementSel();
    if (e) selecciona(seleccio.p, e.id);
  },
  editaLletra() {
    const e = elementSel();
    if (e) editaLletra(seleccio.p, e.id);
  },
  canviaImatge() {
    $("#fitxer-imatge").dataset.desti = "substitueix";
    $("#fitxer-imatge").click();
  },
  triaFontElement,
  desaABiblioteca: desaSeleccioABiblioteca,
  canviaNomMestra,
  duplicaMestra: () => duplicaMestra(),
  esborraMestra: () => esborraMestra(),
  // Capes
  ressaltaCapes: (p, ids, si) => ids.forEach((id) => nodeElement(p, id)?.classList.toggle("ressaltat", si)),
  seleccionaCapa(p, id, { afegeix = false, sol = false } = {}) {
    sortEdicio();
    selecciona(p, id, { afegeix, sol });
    nodeElement(p, id)?.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
  },
  bloquejaCapa(p, id) {
    const e = pagines[p]?.elements.find((x) => x.id === id);
    if (!e || !editable) return;
    foto(true);
    if (e.bloquejat) delete e.bloquejat;
    else e.bloquejat = true;
    canviat();
    repintaPagina(p).then(pintaPropietats);
  },
  mouCapa(p, id, d) {
    const elements = pagines[p]?.elements;
    const i = elements?.findIndex((x) => x.id === id) ?? -1;
    const j = i + d;
    if (i < 0 || j < 0 || j >= elements.length || !editable) return;
    foto(true);
    [elements[i], elements[j]] = [elements[j], elements[i]];
    canviat();
    repintaPagina(p).then(pintaPropietats);
  },
});
muntaPanellLlista("#panell-llista");
muntaBarraEines("#barra-llenc");
muntaBarraText("#barra-text");
muntaAvisLlenc("#avis-llenc");
muntaMenuContext("#menu-context");
muntaPanellAcords("#llista-acords");
muntaPanellCanco("#panell-canco");
muntaPanellEstils("#panell-estils");
muntaPanellCapes("#panell-capes");
muntaPanellPropietats("#panell-propietats");

// Diagrames d'acords (SVG) per als elements «diagrama» i «tots els acords»: els genera el servidor,
// es guarden aquí i, quan n'arriben de nous, es torna a dibuixar.
const DIAGRAMES = {};
const baseAcord = (a) => String(a || "").split("/")[0];
const acordsSolts = (pags) => pags.flatMap((p) => p.elements.filter((e) => e.tipus === "diagrama" && e.acord).map((e) => baseAcord(e.acord)));
let demanant = null;
function demanaDiagrames(acords) {
  const falten = [...new Set(acords.filter((a) => a && !(a in DIAGRAMES)))];
  if (!falten.length || demanant) return;
  demanant = api(urls.diagrames, "POST", { acords: falten, instrument: K.instrument })
    .then((svgs) => { Object.assign(DIAGRAMES, svgs); for (const a of falten) DIAGRAMES[a] ??= ""; })
    .catch(() => null)
    .finally(() => {
      demanant = null;
      if (!edicio) pintaLlenc(); // mentre s'escriu no es torna a dibuixar (es veuran en acabar)
      sincronitzaStore();
    });
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
  store.sincronitza({ zoom });
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
    seleccio = { p, ...novaSeleccio(actuals, nous, id, afegeix) };
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

/** Guies d'una pàgina (vores, marges, centre i els altres elements). */
const guies = (p, exclou) => guiesDe(pagines[p].elements, exclou);


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
  const mida = midaEscalada(midaDe(original), factor);
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

  // Els càlculs són a geometria.js (amb tests); aquí s'apliquen als elements.
  const guiesGest = ambGuies ? { xs, ys } : null;
  if (gest.tipus === "rota") {
    calculaGir({ originals: gest.originals, requadre: b, inici: gest.inici, punt: pt, majuscules: ev.shiftKey })
      .forEach((r, i) => Object.assign(elements[i], r));
  } else if (gest.tipus === "mou") {
    // Si el punter és sobre una altra pàgina, els elements s'hi mouran en deixar-los anar (#6).
    const desti = paginaSota(ev);
    if (desti !== null && desti !== gest.p) return arrossegaAPagina(ev, desti);
    treuFantasma(gest);
    const r = calculaMoviment({ originals: gest.originals, requadre: b, dx, dy, guies: guiesGest });
    r.posicions.forEach((pos, i) => Object.assign(elements[i], pos));
    [lx, ly] = [r.lx, r.ly];
  } else {
    // Canvi de mida sobre el requadre (d'un element o del grup sencer).
    const r = canviaMida({
      originals: gest.originals, requadre: b, nansa: gest.nansa, dx, dy, guies: guiesGest,
      majuscules: ev.shiftKey, esImatge: elements.length === 1 && elements[0].tipus === "imatge",
    });
    r.posicions.forEach((pos, i) => Object.assign(elements[i], pos));
    if (elements.length > 1 && r.proporcio) gest.originals.forEach((o, i) => escalaLletra(elements[i], o, r.factor));
    [lx, ly] = [r.lx, r.ly];
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
    const dins = dinsRectangle(pagines[g.p].elements, g.rect);
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

// Zoom amb Ctrl/⌘ + roda o el gest de pinça: el punt que hi ha sota el punter es queda on és.
llenc.addEventListener("wheel", (ev) => {
  if (!ev.ctrlKey && !ev.metaKey) return;
  ev.preventDefault();
  const r = llenc.getBoundingClientRect();
  posaZoom(zoom * (ev.deltaY < 0 ? 1.1 : 1 / 1.1), { x: ev.clientX - r.left, y: ev.clientY - r.top });
}, { passive: false });

/** Canvia el zoom. focus: punt del llenç (px) que ha de quedar quiet; per defecte, el centre. */
function posaZoom(z, focus = null) {
  const f = focus || { x: llenc.clientWidth / 2, y: llenc.clientHeight / 2 };
  // On és el punt dins del contingut, en proporció (es manté encara que el contingut canviï de mida).
  posaZoom.fixa ??= { px: (llenc.scrollLeft + f.x) / Math.max(1, llenc.scrollWidth), py: (llenc.scrollTop + f.y) / Math.max(1, llenc.scrollHeight), f };
  zoom = Math.max(0.3, Math.min(4, z));
  clearTimeout(posaZoom.t);
  posaZoom.t = setTimeout(async () => {
    const { px, py, f: punt } = posaZoom.fixa;
    posaZoom.fixa = null;
    await pintaLlenc();
    llenc.scrollLeft = px * llenc.scrollWidth - punt.x;
    llenc.scrollTop = py * llenc.scrollHeight - punt.y;
  }, 60);
}

// Moure el llenç amb la mà: mantenint l'espai premut i arrossegant, amb el botó del mig del ratolí
// o amb el botó de la mà de la barra (que la deixa fixa).
let ma = { espai: false, fixa: false, arrossegant: null };
const pintaMa = () => {
  llenc.classList.toggle("mode-ma", ma.espai || ma.fixa);
  llenc.classList.toggle("movent-ma", !!ma.arrossegant);
  store.sincronitza({ eines: { ...store.eines, ma: ma.fixa } });
};
function escrivintA(objectiu) {
  return !!edicio || !!objectiu?.matches?.("input, textarea, select, [contenteditable='true'], [contenteditable='plaintext-only']");
}
document.addEventListener("keydown", (ev) => {
  if (ev.code !== "Space" || ev.repeat || escrivintA(ev.target) || ev.target.closest?.("dialog, button")) return;
  ev.preventDefault(); // sense això, l'espai faria baixar la pàgina
  ma.espai = true;
  pintaMa();
});
document.addEventListener("keyup", (ev) => {
  if (ev.code !== "Space" || !ma.espai) return;
  ma.espai = false;
  pintaMa();
});
window.addEventListener("blur", () => { ma.espai = false; pintaMa(); });
llenc.addEventListener("pointerdown", (ev) => {
  if (!(ma.espai || ma.fixa || ev.button === 1)) return;
  ev.preventDefault();
  ev.stopImmediatePropagation(); // no és un gest sobre els elements
  ma.arrossegant = { x: ev.clientX, y: ev.clientY, left: llenc.scrollLeft, top: llenc.scrollTop };
  llenc.setPointerCapture(ev.pointerId);
  pintaMa();
}, true);
llenc.addEventListener("pointermove", (ev) => {
  if (!ma.arrossegant) return;
  ev.stopImmediatePropagation();
  llenc.scrollLeft = ma.arrossegant.left - (ev.clientX - ma.arrossegant.x);
  llenc.scrollTop = ma.arrossegant.top - (ev.clientY - ma.arrossegant.y);
}, true);
const deixaMa = (ev) => {
  if (!ma.arrossegant) return;
  ev.stopImmediatePropagation();
  ma.arrossegant = null;
  pintaMa();
};
llenc.addEventListener("pointerup", deixaMa, true);
llenc.addEventListener("pointercancel", deixaMa, true);
llenc.addEventListener("auxclick", (ev) => { if (ev.button === 1) ev.preventDefault(); }); // el clic del mig no obre res
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
    if (store.propietats.element?.id === e.id) store.propietats.element.text = e.text;
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
    store.sincronitza({ edicio: null });
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

function actualitzaBarraText() {
  const ed = edicio?.editor;
  if (!ed) return;
  for (const nom of ["tonica", "bold", "italic", "cor", "seccio", "nota"]) {
    $(`[data-bombolla="${nom}"]`)?.setAttribute("aria-pressed", String(ed.isActive(nom)));
  }
  pintaMidaMarc();
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

/** Estat de la barra de format (el component BarraText): marques actives i mida del marc. */
function pintaMidaMarc() {
  if (edicio?.tipus !== "lletra") return;
  const e = elementDe(edicio.p, edicio.id);
  const mida = midaMarc(e);
  const escala = Number(edicio.node.dataset.escala || 1);
  const desborda = edicio.node.classList.contains("desborda");
  const ed = edicio.editor;
  store.sincronitza({
    edicio: {
      actius: Object.fromEntries(["tonica", "bold", "italic", "cor", "seccio", "nota"].map((nom) => [nom, ed.isActive(nom)])),
      mida, ajusta: e.ajusta !== false,
      efectiva: { alerta: desborda, text: desborda ? "no hi cap!" : escala < 0.999 ? `→ ${(mida * escala).toFixed(1)} pt perquè hi càpiga` : "" },
    },
  });
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
  "pagina-esborra": async () => {
    if (obert?.tipus !== "canco" || !editable || pagines.length < 2) return;
    if (!await confirma({ titol: "Esborrar la pàgina?", text: "S'esborra aquesta pàgina de la cançó. Ho pots desfer amb ⌘Z.", accepta: "Esborra la pàgina", perill: true })) return;
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

// ------------------------------------------------------------ Diagrames d'acords (panell per arrossegar)

const MIDA_DIAGRAMA = { w: 18, h: 23.7 }; // proporció dels diagrames (70 × 92)

/** Afegeix un diagrama (o, amb «*», tots els de la cançó) a la pàgina, centrat on s'ha deixat anar. */
function afegeixDiagrama(nom, p = paginaActual(), punt = null) {
  if (!editable || obert?.tipus !== "canco") return;
  const element = nom === "*"
    ? { tipus: "diagrames", canco: true, mida: 16, w: AMPLE - 2 * MARGE, h: 26 }
    : { tipus: "diagrama", acord: transportaAcord(nom, -transport()), ...MIDA_DIAGRAMA }; // es desa sense el transport
  const centre = punt || { x: AMPLE / 2, y: ALT / 2 };
  Object.assign(element, {
    id: nouId(), rotacio: 0, opacitat: 1,
    x: arrodoneix(Math.min(AMPLE - element.w, Math.max(0, centre.x - element.w / 2))),
    y: arrodoneix(Math.min(ALT - element.h, Math.max(0, centre.y - element.h / 2))),
  });
  seleccio = { p, id: null };
  afegeix(element);
}

EINES.acords = () => {
  const panell = $("#panell-acords");
  const obrir = panell.classList.contains("hidden");
  panell.classList.toggle("hidden", !obrir);
  store.sincronitza({ eines: { ...store.eines, acordsObert: obrir } });
  if (obrir) sincronitzaStore();
};
$("[data-tanca-acords]").addEventListener("click", () => EINES.acords());

// Arrossegar imatges des de l'ordinador, o diagrames del panell d'acords, directament a una pàgina.
llenc.addEventListener("dragover", (ev) => {
  if (ev.dataTransfer?.types.includes(TIPUS_ACORD)) {
    ev.preventDefault();
    ev.dataTransfer.dropEffect = "copy";
  } else if (ev.dataTransfer?.types.includes("Files")) ev.preventDefault();
});
llenc.addEventListener("drop", (ev) => {
  const nom = ev.dataTransfer?.getData(TIPUS_ACORD);
  const caixa = ev.target.closest(".pagina-editor");
  if (!nom || !caixa) return;
  ev.preventDefault();
  ev.stopImmediatePropagation();
  afegeixDiagrama(nom, Number(caixa.dataset.pagina), puntMm(ev, caixa));
});
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

// ------------------------------------------------------------ Menú del botó dret (llenç)

const separador = { separador: true };
const MAC = /Mac|iPhone|iPad/.test(navigator.platform);
const tecla = (d) => (MAC ? d : d.replace("⌘", "Ctrl+").replace("⇧", "Maj+").replace("⌥", "Alt+"));

/** Afegeix un element nou centrat en un punt de la pàgina (des del menú «Afegeix aquí»). */
function afegeixA(tipus, p, punt) {
  if (tipus === "nou-imatge") return EINES["nou-imatge"]();
  const element = { id: nouId(), rotacio: 0, opacitat: 1, ...NOUS[tipus]() };
  element.x = arrodoneix(Math.min(AMPLE - element.w, Math.max(0, punt.x - element.w / 2)));
  element.y = arrodoneix(Math.min(ALT - element.h, Math.max(0, punt.y - element.h / 2)));
  seleccio = { p, id: null };
  afegeix(element);
}

/** Opcions per a la selecció (un element o diversos). */
function menuSeleccio() {
  const els = elementsSel();
  const e = els.length === 1 ? els[0] : null;
  const grup = els.length > 1 && !!els[0].grup && els.every((x) => x.grup === els[0].grup);
  const propies = [];
  if (e?.tipus === "lletra") propies.push({ text: "Edita la lletra", drecera: "doble clic", fes: () => editaLletra(seleccio.p, e.id) });
  if (e?.tipus === "text") propies.push({ text: "Edita el text", drecera: "doble clic", fes: () => editaText(seleccio.p, e.id, nodeElement(seleccio.p, e.id)) });
  if (e?.tipus === "imatge") propies.push({ text: "Canvia la imatge…", fes: () => { $("#fitxer-imatge").dataset.desti = "substitueix"; $("#fitxer-imatge").click(); } });
  if (e?.grup) propies.push({ text: "Selecciona tot el grup", fes: () => selecciona(seleccio.p, e.id) });
  return [
    ...(els.length > 1 ? [{ seccio: grup ? `Grup de ${els.length}` : `${els.length} elements` }] : []),
    ...propies, ...(propies.length ? [separador] : []),
    { text: "Copia", drecera: tecla("⌘C"), fes: copiaElement },
    { text: "Enganxa", drecera: tecla("⌘V"), desactivat: !portapapers || !editable, fes: () => enganxaElements(portapapers) },
    { text: "Duplica", drecera: tecla("⌘D"), desactivat: !editable, fes: () => accio("duplica") },
    separador,
    { text: "Porta al davant", desactivat: !editable, fes: () => accio("davant") },
    { text: "Envia al fons", desactivat: !editable, fes: () => accio("darrere") },
    ...(els.length > 1 && !grup ? [{ text: "Agrupa", drecera: tecla("⌘G"), desactivat: !editable, fes: () => accio("agrupa") }] : []),
    ...(els.some((x) => x.grup) ? [{ text: "Desagrupa", drecera: tecla("⇧⌘G"), desactivat: !editable, fes: () => accio("desagrupa") }] : []),
    { text: els.every((x) => x.bloquejat) ? "Desbloqueja" : "Bloqueja", marcat: els.every((x) => x.bloquejat), desactivat: !editable, fes: () => accio("bloqueja") },
    ...(pagines.length > 1 ? [
      { text: "Passa a la pàgina anterior", desactivat: !editable || seleccio.p === 0, fes: () => accio("a-pagina-anterior") },
      { text: "Passa a la pàgina següent", desactivat: !editable || seleccio.p >= pagines.length - 1, fes: () => accio("a-pagina-seguent") },
    ] : []),
    { text: "Desa a la biblioteca d'elements…", fes: () => desaSeleccioABiblioteca(els.length > 1 ? "multi" : "element") },
    separador,
    { text: "Esborra", drecera: "Supr", perill: true, desactivat: !editable, fes: () => accio("esborra") },
  ];
}

/** Enganxa el que s'ha copiat amb el centre on s'ha clicat. */
function enganxaA(p, punt) {
  const r = requadre(portapapers);
  const dx = punt.x - (r.x + r.w / 2);
  const dy = punt.y - (r.y + r.h / 2);
  seleccio = { p, id: null };
  enganxaElements(portapapers.map((e) => ({ ...e, x: e.x + dx, y: e.y + dy })), 0);
}

/** Opcions per a un lloc buit d'una pàgina. */
function menuPagina(p, punt) {
  const canco = obert?.tipus === "canco";
  const afegir = [
    ["nou-text", "Text"], ["nou-lletra", "Marc de lletra"], ["nou-imatge", "Imatge…"], ["nou-forma", "Rectangle"],
    ["nou-elipse", "El·lipse"], ["nou-numero", "Número de pàgina"], ...(canco ? [["nou-qr", "Codi QR d'un vídeo"]] : []),
  ].map(([tipus, text]) => ({ text, desactivat: !editable, fes: () => afegeixA(tipus, p, punt) }));
  return [
    { text: "Enganxa aquí", drecera: tecla("⌘V"), desactivat: !portapapers || !editable, fes: () => enganxaA(p, punt) },
    { seccio: "Afegeix aquí" }, ...afegir,
    ...(canco ? [{ text: "Diagrames d'acords…", desactivat: !editable, fes: () => { if ($("#panell-acords").classList.contains("hidden")) EINES.acords(); } }] : []),
    separador,
    { text: "Selecciona-ho tot", drecera: tecla("⌘A"), fes: () => seleccionaMolts(p, pagines[p].elements.filter((e) => !e.bloquejat).map((e) => e.id)) },
    ...(canco ? [
      { seccio: "Pàgina" },
      { text: "Afegeix una pàgina després", desactivat: !editable, fes: () => { seleccio = { p, id: null }; EINES["pagina-nova"](); } },
      { text: "Duplica la pàgina", desactivat: !editable, fes: () => { seleccio = { p, id: null }; EINES["pagina-duplica"](); } },
      { text: "Esborra la pàgina…", perill: true, desactivat: !editable || pagines.length < 2, fes: () => { seleccio = { p, id: null }; EINES["pagina-esborra"](); } },
    ] : []),
    separador,
    { text: "Ajusta el zoom a la finestra", fes: () => posaZoom(1) },
  ];
}

llenc.addEventListener("contextmenu", (ev) => {
  // Mentre s'escriu, el menú del navegador (corrector, copiar i enganxar).
  if (ev.target.closest(".editant, [contenteditable='true'], [contenteditable='plaintext-only']")) return;
  const caixa = ev.target.closest(".pagina-editor");
  if (!caixa || obert?.tipus === "llibre") return;
  ev.preventDefault();
  const p = Number(caixa.dataset.pagina);
  const node = ev.target.closest(".capa-elements [data-id]") || ev.target.closest(".capa-seleccio") && seleccio?.p === p && nodeElement(p, idsSel()[0]);
  const id = node?.dataset?.id;
  if (id) {
    // Si l'element no és a la selecció, se selecciona (amb el seu grup); si hi és, es manté tota la selecció.
    if (!(seleccio?.p === p && idsSel().includes(id))) selecciona(p, id);
    store.obreMenu(ev.clientX, ev.clientY, menuSeleccio());
  } else {
    selecciona(p, null);
    store.obreMenu(ev.clientX, ev.clientY, menuPagina(p, puntMm(ev, caixa)));
  }
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

const NOMS_TIPUS = { diagrama: "Diagrama d'acord", text: "Text", lletra: "Marc de lletra", imatge: "Imatge", forma: "Forma", numero: "Número de pàgina", index: "Índex", diagrames: "Diagrames d'acords", qr: "Codi QR", index_qr: "Índex de vídeos" };

/** Estat del panell de propietats (el component PanellPropietats). */
function pintaPropietats() {
  pintaCapes();
  const ids = idsSel();
  const moure = {
    visible: pagines.length > 1 && obert?.tipus !== "llibre",
    anterior: editable && !!seleccio && seleccio.p > 0,
    seguent: editable && !!seleccio && seleccio.p < pagines.length - 1,
  };
  if (ids.length > 1) {
    const els = elementsSel();
    const grup = !!els[0].grup && els.every((x) => x.grup === els[0].grup) && idsGrup(seleccio.p, els[0].id).length === els.length;
    return store.sincronitza({ propietats: { mode: "multi", multi: { n: els.length, grup, algunGrup: els.some((x) => x.grup) }, element: null, pagina: null, moure } });
  }
  const e = elementSel();
  if (e) {
    return store.sincronitza({
      propietats: { mode: "element", element: { ...copia(e), infoMarc: infoMarc(e) }, multi: null, pagina: null, moure },
      estils: copia(K.estils), tipografies: TIPOGRAFIES, videos: copia(videosCanco()),
    });
  }
  const model = pagines[paginaActual()];
  const mestra = obert?.tipus === "mestra" ? K.mestres.find((x) => x.id === obert.id) : null;
  store.sincronitza({
    mestres: K.mestres.map(({ id, nom }) => ({ id, nom })),
    propietats: {
      mode: "pagina", element: null, multi: null, moure,
      pagina: obert && model ? {
        tipus: obert.tipus, mestra: model.mestra || null, costat: model.costat || null, fons: model.fons || "#ffffff",
        nomMestra: mestra?.nom || "", mestraEsborrable: !!mestra && mestra.id !== "estandard",
      } : obert ? { tipus: obert.tipus } : null,
    },
  });
}

/** Posició i mida de l'element seleccionat (mentre s'arrossega, sense tornar a pintar tot el panell). */
function pintaPropietatsPosicio() {
  const e = elementSel();
  const actual = store.propietats.element;
  if (!e || !actual || actual.id !== e.id) return;
  for (const prop of ["x", "y", "w", "h", "rotacio"]) actual[prop] = e[prop];
}

/** Informació d'un marc de lletra: a quina mida ha quedat la lletra o si no hi cap. */
function infoMarc(e) {
  if (e?.tipus !== "lletra") return null;
  const node = nodeElement(seleccio.p, e.id);
  const factor = Number(node?.dataset.escala || 1);
  const mida = (Number(e.format?.mida || K.estils[e.estil || "lletra"]?.mida) || 11) * factor;
  if (node?.classList.contains("desborda")) {
    return { alerta: true, text: "La lletra no hi cap. Fes el marc més gran, activa l'ajust, afegeix columnes o fes servir «Talla aquí» per passar-ne una part a la pàgina següent." };
  }
  return { alerta: false, text: factor < 1 ? `Lletra ajustada a ${mida.toFixed(1)} pt perquè hi càpiga.` : `Lletra a ${mida.toFixed(1)} pt.` };
}

function pintaInfoMarc() {
  const e = elementSel();
  const actual = store.propietats.element;
  if (e?.tipus === "lletra" && actual?.id === e.id) actual.infoMarc = infoMarc(e);
}

function canviaPropietats(propietats, { repinta = true } = {}) {
  const e = elementSel();
  if (!e || !editable) return;
  foto();
  Object.assign(e, propietats);
  canviat();
  if (repinta) repintaPagina(seleccio.p).then(() => pintaPropietats());
}

/** Posició, mida, rotació o opacitat: es mou l'element sense tornar-lo a dibuixar. */
function canviaPosicio(prop, valor) {
  const e = elementSel();
  if (!e || !editable) return;
  foto();
  e[prop] = valor;
  const node = nodeElement(seleccio.p, e.id);
  if (node) reposiciona(node, e);
  pintaSeleccio();
  canviat();
  if (prop === "w" || prop === "h") reajusta();
}

/** Mestra, costat de la mestra o fons de la pàgina oberta. */
function canviaPagina(canvis) {
  const model = pagines[paginaActual()];
  if (!model || !editable) return;
  foto(!("fons" in canvis));
  for (const [clau, valor] of Object.entries(canvis)) {
    if (valor) model[clau] = valor;
    else if (clau === "mestra") model.mestra = null;
    else delete model[clau];
  }
  if (!model.mestra) delete model.costat;
  canviat();
  repintaPagina(paginaActual());
  pintaPropietats();
}

function gira(graus) {
  const e = elementSel();
  if (!e || !editable) return;
  foto(true);
  e.rotacio = ((((e.rotacio || 0) + graus) % 360) + 540) % 360 - 180;
  const node = nodeElement(seleccio.p, e.id);
  if (node) reposiciona(node, e);
  pintaSeleccio();
  pintaPropietats();
  canviat();
}

function triaFontElement(boto) {
  const e = elementSel();
  if (!e || !editable) return;
  obreSelectorFont(boto, {
    actual: e.format?.font ?? null,
    permetBuit: true,
    tria: (clau) => {
      const format = { ...(e.format || {}) };
      if (clau) format.font = clau;
      else delete format.font;
      canviaPropietats({ format });
    },
  });
}

function desaSeleccioABiblioteca(quin) {
  if (quin === "pagina") return desaABiblioteca(copia(pagines[paginaActual()]?.elements || []), "Pàgina");
  if (quin === "multi") return desaABiblioteca(copia(elementsSel()), "Grup");
  const e = elementSel();
  if (e) desaABiblioteca([copia(e)], NOMS_TIPUS[e.tipus]);
}

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

/** Estat del panell de capes (el component PanellCapes): elements de cada pàgina, del de davant al del fons. */
function pintaCapes() {
  if (!obert || obert.tipus === "llibre") return store.sincronitza({ capes: null });
  const numeros = numerosPagina();
  const seleccionats = seleccio ? idsSel() : [];
  store.sincronitza({
    capes: pagines.map((pagina, p) => {
      const mestra = obert.tipus !== "mestra" && mestraDe(pagina.mestra, numeros[p], pagina.costat);
      return {
        etiqueta: obert.tipus === "mestra" ? (p === 0 ? "Pàgines parells" : "Pàgines senars") : `Pàgina ${numeros[p]}`,
        mestra: mestra?.elements?.length || 0,
        elements: [...pagina.elements].reverse().map((e) => ({
          id: e.id, tipus: e.tipus, nom: nomCapa(e, p), grup: e.grup || null, bloquejat: !!e.bloquejat,
          font: e.tipus === "text" || e.tipus === "lletra" ? e.format?.font || K.estils[e.estil]?.font || null : null,
          seleccionat: seleccio?.p === p && seleccionats.includes(e.id),
          index: pagina.elements.indexOf(e), total: pagina.elements.length,
        })),
      };
    }),
  });
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

/**
 * Avís a sobre del llenç (el component AvisLlenc). accions: [[text, funció, primària]].
 * origen "versio": el de la versió fixada, que es posa al dia cada cop que es dibuixa el llenç; la
 * resta es mantenen fins que s'obre una altra cosa (dibuixar-los encongeix el llenç i el redibuixa).
 */
function avisa(text, accions = [], origen = "temporal") {
  store.sincronitza({ avis: { text, origen, accions: accions.map(([t, fes, primari]) => ({ text: t, fes, primari: !!primari })) } });
}

function pintaAvisLlenc() {
  const entrada = entradaActual();
  if (!entrada || !entrada.versio_id) {
    if (store.avis?.origen === "versio") store.sincronitza({ avis: null });
    return;
  }
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
  ], "versio");
}

// ------------------------------------------------------------ Llista (llibret, cançons, mestres)

/** Estat de la columna de l'esquerra (el component PanellLlista). */
function pintaLlista() {
  store.sincronitza({
    mestres: K.mestres.map(({ id, nom }) => ({ id, nom })),
    llista: {
      obert: obert?.tipus === "llibre" ? "llibre" : obert ? `${obert.tipus}:${obert.id}` : null,
      total: PLA?.total ?? null,
      cancons: K.cancons.map((c) => ({
        id: c.id, titol: c.titol, tipus: c.tipus, inclosa: c.inclosa, inici: c.inici, usos: c.usos,
        versio_numero: c.versio_id ? c.versio_numero : null,
        desfasada: !!c.versio_id && (c.versio_numero < c.versio_ultima || c.esborrany_modificat),
        pagines: PLA?.pagines.filter((x) => x.entrada === c.id).map((x) => x.numero) || [],
      })),
    },
  });
}

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


// ------------------------------------------------------------ Obrir una cançó, una pàgina especial o una mestra

async function obre(desti, { forca = false } = {}) {
  if (!forca && obert && desti.tipus === obert.tipus && desti.id === obert.id) return;
  store.sincronitza({ avis: null });
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
  store.sincronitza({ eines: { ...store.eines, inactives: !editable || desti.tipus === "llibre", pagina: desti.tipus === "canco" && editable } });
  pintaLlista();
  pintaCanco();
  if (desti.tipus === "canco" && esMobil()) mostraPanell("panell-llenc");
  await pintaLlenc();
}

const esMobil = () => window.matchMedia("(max-width: 1023px)").matches;

// ------------------------------------------------------------ Pestanya Cançó

/** La pestanya Cançó és el component PanellCanco: només cal posar al dia l'estat. */
function pintaCanco() {
  sincronitzaStore();
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
  pintaLlenc();
}

async function aplicaTransport() {
  const entrada = entradaActual();
  if (!entrada?.transport || !editable) return;
  const { contingut } = await api(urls.transporta, "POST", { contingut: { format: 2, pagines, videos: videosCanco() }, semitons: entrada.transport });
  foto(true);
  substitueixPagines(contingut.pagines);
  await api(urls.canco + canco.id, "PUT", { contingut });
  await canviaEntrada(entrada.id, { transport: 0 });
  pintaLlenc();
}

async function treuCanco() {
  const entrada = entradaActual();
  if (!entrada) return;
  const on = entrada.usos > 1 ? "Continuarà als altres cançoners on surt i a la biblioteca." : "Continuarà a la biblioteca.";
  if (!await confirma({ titol: `Treure «${entrada.titol || "Sense títol"}» del cançoner?`, text: on, accepta: "Treu-la", perill: true })) return;
  await desa();
  await api(urls.entrada + entrada.id, "DELETE");
  [K, PLA] = await Promise.all([api(urls.canconer), api(urls.pla)]);
  obert = null;
  await obre(K.cancons[0] ? { tipus: "canco", id: K.cancons[0].id } : { tipus: "especial", id: "portada" });
}

// Noves cançons, pàgines lliures i importació
async function creaEntrada(tipus, mestra) {
  if (mestra === undefined && K.mestres.length > 1) return triaPlantilla(tipus);
  await desa();
  const despres = obert?.tipus === "canco" ? obert.id : undefined;
  const r = await api(urls.nova, "POST", { tipus, despres_de: despres, mestra: mestra || undefined });
  [K, PLA] = await Promise.all([api(urls.canconer), api(urls.pla)]);
  await obre({ tipus: "canco", id: r.id });
  mostraPestanya("canco");
  requestAnimationFrame(() => $("#titol-ev")?.select()); // el camp el pinta PanellCanco
}

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

function obreImporta() {
  seleccionades.clear();
  $("#compte-seleccio").textContent = "";
  $("#confirma-importa").disabled = true;
  $("#cerca-biblioteca").value = "";
  dialegImporta.showModal();
  mostraPestanyaImporta("text");
}
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

async function novaMestra() {
  const nom = await pregunta({ titol: "Pàgina mestra nova", text: "Com es diu? Després en podràs dissenyar la pàgina esquerra i la dreta.", valor: "Mestra nova", accepta: "Crea-la" });
  if (!nom) return;
  await desa();
  const id = "m" + nouId();
  const base = copia(K.mestres.find((m) => m.id === "estandard"));
  K.mestres.push({ id, nom, parell: base.parell, senar: base.senar });
  await api(urls.disseny, "PUT", { mestres: K.mestres });
  await obre({ tipus: "mestra", id });
}
function canviaNomMestra(nom) {
  const m = K.mestres.find((x) => x.id === obert?.id);
  if (!m) return;
  m.nom = nom || "Mestra";
  canviat();
  pintaLlista();
}
async function duplicaMestra() {
  const m = K.mestres.find((x) => x.id === obert?.id);
  if (!m) return;
  if (K.mestres.length >= 20) return avisaDialeg({ titol: "No n'hi caben més", text: "Com a màxim hi pot haver 20 pàgines mestres." });
  await desa();
  const id = nouId();
  K.mestres.push({ ...copia(m), id, nom: `${m.nom} (còpia)` });
  await api(urls.disseny, "PUT", { mestres: K.mestres });
  await obre({ tipus: "mestra", id });
}

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
async function obreCopiaMestres() {
  ({ canconers: altresCanconers } = await api(urls.mestresAltres));
  const select = $("#origen-mestres");
  select.replaceChildren(...(altresCanconers.length
    ? altresCanconers.map((k) => el("option", { text: `${k.titol} (${k.mestres.length})`, atributs: { value: k.id } }))
    : [el("option", { text: "No hi ha cap altre cançoner", atributs: { value: "" } })]));
  pintaMestresOrigen();
  dialegCopia.showModal();
}
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

async function esborraMestra() {
  if (obert?.tipus !== "mestra" || obert.id === "estandard") return;
  if (!await confirma({ titol: "Esborrar la pàgina mestra?", text: "Les pàgines que la fan servir es quedaran sense mestra.", accepta: "Esborra-la", perill: true })) return;
  K.mestres = K.mestres.filter((m) => m.id !== obert.id);
  pendent = false;
  await api(urls.disseny, "PUT", { mestres: K.mestres });
  [K, PLA] = await Promise.all([api(urls.canconer), api(urls.pla)]);
  obert = null;
  await obre({ tipus: "mestra", id: "estandard" });
}

// ------------------------------------------------------------ Estils

/** Estat del panell d'estils (el component PanellEstils). */
function pintaEstils() {
  store.sincronitza({ estils: copia(K.estils), tipografies: TIPOGRAFIES });
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
      if (!await confirma({ titol: `Esborrar «${item.nom}»?`, text: "Desapareix de la biblioteca d'elements. Les pàgines on ja l'has posat no canvien.", accepta: "Esborra", perill: true })) return;
      await api(`${urls.elements}/${item.id}`, "DELETE");
      pintaBiblioteca();
    });
    li.append(boto, esborra);
    return li;
  }));
}

async function desaABiblioteca(elements, nomPerDefecte) {
  if (!elements?.length) return;
  const nom = await pregunta({ titol: "Desar a la biblioteca d'elements", text: "Podràs posar-ho a qualsevol pàgina o cançoner des de la pestanya Elements.", valor: nomPerDefecte });
  if (!nom) return;
  await api(urls.elements, "POST", { nom, elements });
  mostraEstat("Desat a la biblioteca");
  mostraPestanya("biblioteca");
}
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
    if (!await confirma({ titol: `Tornar a la versió ${v.numero}?`, text: "L'esborrany tornarà a ser com aquesta versió. L'estat actual es desarà abans com una versió nova, així que no es perd res.", accepta: "Restaura-la" })) return;
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
