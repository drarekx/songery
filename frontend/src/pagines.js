// Motor de dibuix de pàgines: el mateix codi pinta les pàgines a l'editor i a la pàgina que
// Gotenberg (Chromium) converteix en PDF. Així el que es veu a l'editor és el que s'imprimeix.
// Totes les mides són en mil·límetres sobre un A5 (148 × 210 mm).
import qrcode from "qrcode-generator";
import { creaEditorCanco } from "./editor-canco.js";

export const AMPLE = 148;
export const ALT = 210;
export const FONTS = {
  display: '"Newsreader", Georgia, serif',
  sans: '"Hanken Grotesk", Helvetica, Arial, sans-serif',
  mono: '"JetBrains Mono", "Courier New", monospace',
};

/** Afegeix les tipografies disponibles (catàleg i importades): [{clau, css}]. */
export function registraFonts(llista) {
  for (const f of llista || []) FONTS[f.clau] = f.css;
}
// ---------------------------------------------------------------- Colors (RGB o CMYK per a impremta)

/** RGB testimoni de cada color CMYK del cançoner (ve del pla); sense taula, l'aproximació directa. */
const TESTIMONIS = {};
export function registraColors(taula) {
  Object.assign(TESTIMONIS, taula || {});
}

/** «cmyk(c,m,y,k)» → [c, m, y, k] (0-100), o null. */
export function llegeixCmyk(valor) {
  const m = /^cmyk\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)$/.exec(String(valor || "").trim());
  return m ? m.slice(1).map((v) => Math.min(100, Math.max(0, Number(v)))) : null;
}

// Color aproximat de cada tinta d'impremta (cian, magenta, groc, negre) sobre paper blanc.
const TINTES = [[0, 158, 224], [226, 0, 122], [255, 236, 0], [30, 28, 27]];

/** Aproximació a la pantalla d'un color CMYK (la mateixa fórmula que colors.py): les tintes es
 *  multipliquen com sobre el paper, cadascuna en la seva proporció. */
export function cmykAHex(cmyk) {
  const canal = (i) => {
    const valor = cmyk.reduce((acc, quantitat, t) => acc * (1 - (quantitat / 100) * (1 - TINTES[t][i] / 255)), 1);
    return Math.round(255 * valor).toString(16).padStart(2, "0");
  };
  return `#${canal(0)}${canal(1)}${canal(2)}`;
}

/** Valor CSS d'un color del disseny (RGB tal qual; CMYK amb el seu testimoni o l'aproximació). */
export function colorCss(valor) {
  if (!valor) return valor;
  const cmyk = llegeixCmyk(valor);
  if (!cmyk) return valor;
  return TESTIMONIS[`cmyk(${cmyk.join(",")})`] || cmykAHex(cmyk);
}

const ESCALA_MINIMA = 0.45; // l'ajust automàtic no redueix la lletra per sota d'aquest factor

// ---------------------------------------------------------------- Estils

/** Declaracions CSS d'un estil. La mida es multiplica per --escala (ajust automàtic dels marcs). */
function declaracions(e) {
  return [
    `font-family:${FONTS[e.font] || FONTS.sans}`,
    `font-size:calc(${Number(e.mida) || 10}pt * var(--escala, 1))`,
    `font-weight:${e.pes || 400}`,
    `font-style:${e.cursiva ? "italic" : "normal"}`,
    `color:${colorCss(e.color) || "#000"}`,
    `line-height:${e.interlineat || 1.2}`,
    `letter-spacing:${e.espaiat || 0}em`,
    `text-transform:${e.majuscules ? "uppercase" : "none"}`,
  ].join(";");
}

/**
 * CSS dels estils del cançoner. Dins dels marcs de lletra, l'acord, la secció i la nota fan servir el seu estil.
 * ambit: selector que limita els estils a una part de la pàgina (p. ex. diversos cançoners a l'inici).
 */
export function cssEstils(estils, ambit = "") {
  const a = ambit ? `${ambit} ` : "";
  const regles = Object.entries(estils).map(([clau, e]) => `${a}.estil-${clau}{${declaracions(e)}}`);
  if (estils.acord) {
    regles.push(`${a}.marc-lletra .acord-nom{${declaracions(estils.acord)}}`);
    // Espai a sobre de les línies amb acords: l'alçada d'una línia de l'estil Acord.
    const alcada = (Number(estils.acord.mida) || 9) * (Number(estils.acord.interlineat) || 1.2);
    regles.push(`${a}.marc-lletra .linia.amb-acords{padding-top:calc(${alcada}pt * var(--escala, 1))}`);
  }
  if (estils.seccio) regles.push(`${a}.marc-lletra .seccio{${declaracions(estils.seccio)}}`);
  if (estils.nota) regles.push(`${a}.marc-lletra .nota{${declaracions(estils.nota)}}`);
  return regles.join("\n");
}

export function aplicaEstils(estils, document_ = document) {
  let etiqueta = document_.getElementById("estils-canconer");
  if (!etiqueta) {
    etiqueta = document_.createElement("style");
    etiqueta.id = "estils-canconer";
    document_.head.append(etiqueta);
  }
  etiqueta.textContent = cssEstils(estils);
}

/** Propietats d'estil sobreescrites en un element concret (camp "format"). */
function formatPropi(node, format) {
  if (!format) return;
  if (format.font) node.style.fontFamily = FONTS[format.font] || "";
  if (format.mida) node.style.fontSize = `calc(${format.mida}pt * var(--escala, 1))`;
  if (format.pes) node.style.fontWeight = format.pes;
  if (format.cursiva !== undefined) node.style.fontStyle = format.cursiva ? "italic" : "normal";
  if (format.color) node.style.color = colorCss(format.color);
  if (format.interlineat) node.style.lineHeight = format.interlineat;
  if (format.espaiat !== undefined) node.style.letterSpacing = `${format.espaiat}em`;
  if (format.majuscules !== undefined) node.style.textTransform = format.majuscules ? "uppercase" : "none";
}

// ---------------------------------------------------------------- Elements

export function substitueix(text, context) {
  return String(text || "").replace(/\{(titol|subtitol|any|contraportada|autor|acords|pagina)\}/g,
    (_, clau) => context?.[clau] ?? "");
}

const mm = (v) => `${v}mm`;

/** Mida mínima (mm) perquè un QR es pugui escanejar amb comoditat. */
export const QR_MINIM = 15;

/** Codi QR en SVG (generat aquí, sense connexió), amb un marge blanc de 2 mòduls. */
export function svgQR(text, color = "#1b1a17") {
  const qr = qrcode(0, "M");
  qr.addData(text);
  qr.make();
  const n = qr.getModuleCount();
  const marge = 2;
  let d = "";
  for (let r = 0; r < n; r++) for (let c = 0; c < n; c++) if (qr.isDark(r, c)) d += `M${c + marge} ${r + marge}h1v1h-1z`;
  const costat = n + 2 * marge;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${costat} ${costat}" shape-rendering="crispEdges">`
    + `<rect width="${costat}" height="${costat}" fill="#fff"/><path d="${d}" fill="${color}"/></svg>`;
}

function textNode(classe, text) {
  const node = document.createElement("span");
  node.className = classe;
  node.textContent = text;
  return node;
}

function posiciona(node, e) {
  Object.assign(node.style, {
    left: mm(e.x), top: mm(e.y), width: mm(e.w), height: mm(e.h),
    transform: e.rotacio ? `rotate(${e.rotacio}deg)` : "",
    opacity: e.opacitat ?? 1,
  });
}

/**
 * Crea el node d'un element.
 * opcions: context (variables), urlImatge(id), diagrames (svg per acord), index (files de l'índex),
 *          editors (llista on es desen els editors Tiptap creats), mestra (true si ve de la pàgina mestra)
 */
export function dibuixaElement(e, opcions) {
  const { context = {}, urlImatge = (id) => id } = opcions;
  let node;
  switch (e.tipus) {
    case "text":
    case "numero": {
      node = document.createElement("div");
      node.className = `el el-text estil-${e.estil || "text"}`;
      node.textContent = e.tipus === "numero" ? String(context.pagina ?? "") : substitueix(e.text, context);
      node.style.textAlign = e.alineacio || "left";
      formatPropi(node, e.format);
      break;
    }
    case "lletra": {
      node = document.createElement("div");
      node.className = `el marc-lletra estil-${e.estil || "lletra"}`;
      node.style.columnCount = e.columnes > 1 ? e.columnes : "";
      node.style.columnGap = e.columnes > 1 ? mm(e.separacio ?? 6) : "";
      formatPropi(node, e.format);
      const cos = document.createElement("div");
      cos.className = "cos-lletra";
      node.append(cos);
      const editor = creaEditorCanco(cos, {
        doc: e.doc, urlImatge,
        converteix: opcions.converteix || (async () => null),
        editaAcord: (dades) => editor.isEditable && opcions.editaAcord?.(dades, editor),
      });
      editor.setEditable(false);
      if (opcions.grup) node.dataset.grup = opcions.grup;
      node._editor = editor;
      opcions.editors?.push(editor);
      break;
    }
    case "imatge": {
      node = document.createElement("img");
      node.className = "el el-imatge";
      node.alt = "";
      node.draggable = false;
      node.src = e.src ? urlImatge(e.src) : "";
      node.style.objectFit = e.ajust || "cover";
      node.style.borderRadius = mm(e.radi || 0);
      break;
    }
    case "forma": {
      node = document.createElement("div");
      node.className = "el el-forma";
      node.style.background = colorCss(e.fons) || "transparent";
      node.style.borderRadius = e.forma === "elipse" ? "50%" : mm(e.radi || 0);
      if (e.vora && e.gruix) node.style.border = `${e.gruix}mm solid ${colorCss(e.vora)}`;
      break;
    }
    case "index": {
      node = document.createElement("div");
      node.className = `el el-index estil-${e.estil || "index"}`;
      for (const fila of opcions.index || []) {
        const f = document.createElement("div");
        f.className = "fila-index";
        const titol = document.createElement("span");
        titol.className = "titol-index";
        titol.textContent = fila.titol;
        const punts = document.createElement("span");
        punts.className = "punts-index";
        const pagina = document.createElement("span");
        pagina.className = "pagina-index";
        pagina.textContent = fila.pagina;
        f.append(titol, punts, pagina);
        node.append(f);
      }
      formatPropi(node, e.format);
      break;
    }
    case "qr": {
      // Si no s'ha triat cap vídeo, el primer de la cançó.
      const llista = context.videos || [];
      const video = llista.find((v) => v.id === e.video) || (!e.video ? llista[0] : null);
      node = document.createElement("div");
      node.className = "el el-qr";
      if (!video) {
        node.append(textNode("qr-buit", llista.length ? "El vídeo d'aquest QR ja no hi és" : "Afegeix un vídeo a la cançó"));
        break;
      }
      const peu = e.peu && video.titol ? 4.5 : 0;
      const costat = Math.max(1, Math.min(e.w, e.h - peu));
      const codi = document.createElement("div");
      codi.className = "codi-qr";
      codi.style.width = codi.style.height = mm(costat);
      codi.innerHTML = svgQR(video.url, colorCss(e.color) || "#1b1a17");
      node.append(codi);
      if (peu) node.append(textNode("peu-qr estil-nota", video.titol));
      if (costat < QR_MINIM) node.dataset.petit = "";
      break;
    }
    case "index_qr": {
      node = document.createElement("div");
      node.className = `el el-index-qr estil-${e.estil || "index"}`;
      for (const fila of opcions.qrs || []) {
        const f = document.createElement("div");
        f.className = "fila-qr";
        const codi = document.createElement("div");
        codi.className = "codi-qr";
        codi.innerHTML = svgQR(fila.url);
        const textos = document.createElement("div");
        textos.className = "textos-qr";
        textos.append(textNode("titol-index", fila.canco), textNode("video-qr", fila.titol || fila.url));
        f.append(codi, textos, textNode("pagina-index", fila.pagina));
        node.append(f);
      }
      formatPropi(node, e.format);
      break;
    }
    case "diagrames": {
      node = document.createElement("div");
      node.className = "el el-diagrames";
      if (e.mida) node.style.setProperty("--mida-diagrama", mm(e.mida));
      if (e.canco) {
        // Tots els acords de la cançó, en l'ordre en què surten.
        node.classList.add("de-canco");
        const llista = (context.ordreAcords || []).map((a) => context.diagrames?.[a]).filter(Boolean);
        node.innerHTML = llista.join("");
        if (!llista.length) node.append(textNode("diagrama-buit", "Els acords de la cançó"));
      } else {
        node.innerHTML = (opcions.diagrames || []).join("");
      }
      break;
    }
    case "diagrama": {
      node = document.createElement("div");
      node.className = "el el-diagrama";
      const svg = context.diagrames?.[String(e.acord || "").split("/")[0]];
      if (svg) node.innerHTML = svg;
      else node.append(textNode("diagrama-buit", e.acord || "Acord"));
      break;
    }
    default:
      node = document.createElement("div");
      node.className = "el";
  }
  node.dataset.id = e.id;
  node.dataset.tipus = e.tipus;
  if (e.bloquejat) node.dataset.bloquejat = "";
  posiciona(node, e);
  return node;
}

/** Actualitza la posició i l'estil d'un element ja dibuixat (mentre s'arrossega a l'editor). */
export function reposiciona(node, e) {
  posiciona(node, e);
}

// ---------------------------------------------------------------- Pàgines

/**
 * Dibuixa una pàgina A5.
 * pagina: {fons, elements, mestra: {elements} | null, context, index, diagrames}
 */
export function dibuixaPagina(pagina, opcions = {}) {
  const node = document.createElement("section");
  node.className = "pagina";
  node.style.background = colorCss(pagina.fons) || "#fff";
  const comunes = { ...opcions, context: pagina.context, index: pagina.index, diagrames: pagina.diagrames, qrs: pagina.qrs,
    grup: opcions.grup ?? pagina.entrada };
  if (pagina.mestra?.elements?.length) {
    const capa = document.createElement("div");
    capa.className = "capa-mestra";
    capa.append(...pagina.mestra.elements.map((e) => dibuixaElement(e, { ...comunes, mestra: true })));
    node.append(capa);
  }
  const capa = document.createElement("div");
  capa.className = "capa-elements";
  capa.append(...(pagina.elements || []).map((e) => dibuixaElement(e, comunes)));
  node.append(capa);
  return node;
}

// ---------------------------------------------------------------- Ajust dels marcs de lletra

function desborda(marc) {
  return marc.scrollHeight > marc.clientHeight + 1 || marc.scrollWidth > marc.clientWidth + 1;
}

/**
 * Ajusta la mida de la lletra perquè hi càpiga (si el marc té "ajusta") i marca els marcs que desborden.
 * Retorna la llista de marcs que no hi caben.
 */
export function ajustaMarcs(arrel, elements) {
  const desbordats = [];
  for (const marc of arrel.querySelectorAll(".marc-lletra")) {
    const e = elements?.(marc.dataset.id);
    marc.style.setProperty("--escala", "1");
    if (e?.ajusta !== false && desborda(marc)) {
      // Cerca binària de l'escala més gran que hi cap.
      let baix = ESCALA_MINIMA;
      let alt = 1;
      for (let i = 0; i < 9; i++) {
        const mig = (baix + alt) / 2;
        marc.style.setProperty("--escala", String(mig));
        if (desborda(marc)) alt = mig;
        else baix = mig;
      }
      marc.style.setProperty("--escala", String(Math.floor(baix * 1000) / 1000));
    }
  }
  // Els marcs d'una mateixa cançó fan servir tots la mateixa mida (la més petita),
  // perquè la lletra no canviï de mida d'una pàgina a l'altra.
  const grups = new Map();
  for (const marc of arrel.querySelectorAll(".marc-lletra[data-grup]")) {
    if (elements?.(marc.dataset.id)?.ajusta === false) continue;
    const escala = Number(marc.style.getPropertyValue("--escala")) || 1;
    grups.set(marc.dataset.grup, Math.min(grups.get(marc.dataset.grup) ?? 1, escala));
  }
  for (const marc of arrel.querySelectorAll(".marc-lletra")) {
    if (marc.dataset.grup && grups.has(marc.dataset.grup) && elements?.(marc.dataset.id)?.ajusta !== false) {
      marc.style.setProperty("--escala", String(grups.get(marc.dataset.grup)));
    }
    const fora = desborda(marc);
    marc.classList.toggle("desborda", fora);
    marc.dataset.escala = marc.style.getPropertyValue("--escala");
    if (fora) desbordats.push(marc.dataset.id);
  }
  return desbordats;
}

/** Acords d'un document Tiptap (JSON), en ordre d'aparició i sense repetir (sense N.C.). */
export function acordsDeDoc(doc, vistos = []) {
  const recorre = (node) => {
    if (node.type === "acord") {
      const nom = node.attrs?.nom || "";
      if (nom && !/^N/i.test(nom) && !vistos.includes(nom)) vistos.push(nom);
    }
    (node.content || []).forEach(recorre);
  };
  if (doc) recorre(doc);
  return vistos;
}

/** Acords de totes les pàgines d'una cançó. */
export function acordsDePagines(pagines) {
  const vistos = [];
  for (const p of pagines || []) for (const e of p.elements || []) if (e.tipus === "lletra") acordsDeDoc(e.doc, vistos);
  return vistos;
}

/** Espera que s'hagin carregat totes les tipografies que fan servir les pàgines ja dibuixades. */
export async function esperaFonts(arrel = document.body) {
  const mostres = ['400 12pt "Newsreader"', 'italic 400 12pt "Newsreader"', '600 12pt "Newsreader"',
    '400 12pt "Hanken Grotesk"', '700 12pt "Hanken Grotesk"', '400 12pt "JetBrains Mono"'];
  // Cada combinació de família, gruix i estil que apareix a les pàgines.
  const usades = new Set();
  for (const node of arrel?.querySelectorAll?.(".pagina, .pagina *") || []) {
    const c = getComputedStyle(node);
    usades.add(`${c.fontStyle} ${c.fontWeight} 12pt ${c.fontFamily}`);
  }
  await Promise.all([...mostres, ...usades].map((f) => document.fonts.load(f).catch(() => null)));
  await document.fonts.ready;
}

/**
 * Pàgina d'impressió: dibuixa tot el llibret en ordre i avisa (window.paginesLlestes) quan ha acabat,
 * perquè Gotenberg esperi abans de generar el PDF.
 */
export async function dibuixaLlibret(contenidor, dades) {
  registraFonts(dades.fonts);
  registraColors(dades.colors);
  aplicaEstils(dades.estils);
  const urlImatge = (id) => dades.urlImatge.replace("__ID__", id);
  const pagines = dades.pagines.map((p) => dibuixaPagina(p, { urlImatge }));
  contenidor.replaceChildren(...pagines);
  await esperaFonts(contenidor);
  await Promise.all([...contenidor.querySelectorAll("img")].map((img) => img.decode?.().catch(() => null)));
  const perId = new Map(dades.pagines.flatMap((p) => p.elements || []).map((e) => [e.id, e]));
  window.marcsDesbordats = ajustaMarcs(contenidor, (id) => perId.get(id));
  window.paginesLlestes = true;
}

// ---------------------------------------------------------------- Transport (mateixes regles que parser.py)

const SEMITO = { C: 0, "C#": 1, Db: 1, D: 2, "D#": 3, Eb: 3, E: 4, Fb: 4, "E#": 5, F: 5, "F#": 6, Gb: 6, G: 7,
  "G#": 8, Ab: 8, A: 9, "A#": 10, Bb: 10, B: 11, Cb: 11, "B#": 0 };
const SOSTINGUDES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const BEMOLLS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
const PREFERIDES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];

function transportaNota(nota, n) {
  const i = (((SEMITO[nota] + n) % 12) + 12) % 12;
  if (nota.endsWith("#")) return SOSTINGUDES[i];
  if (nota.endsWith("b")) return BEMOLLS[i];
  return PREFERIDES[i];
}

export function transportaAcord(acord, n) {
  if (!(n % 12) || /^N/i.test(acord)) return acord;
  const m = /^([A-G](?:#|b)?)(.*?)(?:\/([A-G](?:#|b)?))?$/.exec(acord);
  if (!m || SEMITO[m[1]] === undefined) return acord;
  return transportaNota(m[1], n) + m[2] + (m[3] ? "/" + transportaNota(m[3], n) : "");
}

export function transportaDoc(doc, n) {
  if (!(n % 12) || !doc) return doc;
  const recorre = (node) => ({
    ...node,
    ...(node.type === "acord" ? { attrs: { ...node.attrs, nom: transportaAcord(node.attrs?.nom || "", n) } } : {}),
    ...(node.content ? { content: node.content.map(recorre) } : {}),
  });
  return recorre(doc);
}

export function transportaPagines(pagines, n) {
  if (!(n % 12)) return pagines;
  return pagines.map((p) => ({
    ...p,
    elements: (p.elements || []).map((e) => {
      if (e.tipus === "lletra") return { ...e, doc: transportaDoc(e.doc, n) };
      if (e.tipus === "diagrama" && e.acord) return { ...e, acord: transportaAcord(e.acord, n) };
      return e;
    }),
  }));
}
