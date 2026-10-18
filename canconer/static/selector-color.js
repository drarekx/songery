// Selector de color per al disseny: CMYK exacte per a impremta (valor «cmyk(c,m,y,k)», en %) o RGB.
// Substitueix un <input> (que guarda el valor com a text): en canviar el color hi escriu el valor i
// llança «input», així el codi que ja escoltava el camp continua igual.
import { cmykAHex, colorCss, llegeixCmyk } from "./dist/canconer.js";

// Tintes habituals d'impremta. Els noms surten en passar-hi el ratolí.
const PALETA = [
  ["Negre (K 100)", "cmyk(0,0,0,100)"], ["Gris fosc (K 75)", "cmyk(0,0,0,75)"], ["Gris (K 50)", "cmyk(0,0,0,50)"],
  ["Gris clar (K 20)", "cmyk(0,0,0,20)"], ["Paper (sense tinta)", "cmyk(0,0,0,0)"],
  ["Vermell (M 100 Y 100)", "cmyk(0,100,100,0)"], ["Vermelló", "cmyk(0,85,90,10)"], ["Taronja", "cmyk(0,60,100,0)"],
  ["Groc", "cmyk(0,0,100,0)"], ["Verd", "cmyk(80,0,100,0)"], ["Cian", "cmyk(100,0,0,0)"],
  ["Blau", "cmyk(100,70,0,0)"], ["Magenta", "cmyk(0,100,0,0)"], ["Morat", "cmyk(60,90,0,0)"],
];
const CANALS = [["c", "C", "#00a0dc"], ["m", "M", "#e5007e"], ["y", "Y", "#f6d900"], ["k", "K", "#1b1a17"]];

let obert = null; // {input, popover}

function el(etiqueta, atributs = {}, ...fills) {
  const node = document.createElement(etiqueta);
  for (const [clau, valor] of Object.entries(atributs)) {
    if (clau === "classe") node.className = valor;
    else if (clau === "text") node.textContent = valor;
    else node.setAttribute(clau, valor);
  }
  node.append(...fills);
  return node;
}

/** Text curt d'un valor per al botó: «C0 M100 Y100 K0» o «#c4321f». */
export function descriuColor(valor) {
  const cmyk = llegeixCmyk(valor);
  if (cmyk) return cmyk.map((v, i) => `${"CMYK"[i]}${Math.round(v * 10) / 10}`).join(" ");
  return valor || "Cap";
}

/** Aproximació inversa (per començar a editar en CMYK un color que era RGB). */
function hexACmyk(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const k = 1 - Math.max(r, g, b);
  if (k >= 1) return [0, 0, 0, 100];
  return [...[r, g, b].map((v) => Math.round(((1 - v - k) / (1 - k)) * 100)), Math.round(k * 100)];
}

function tanca() {
  obert?.popover.remove();
  obert = null;
}
document.addEventListener("pointerdown", (ev) => {
  if (obert && !obert.popover.contains(ev.target) && !obert.boto.contains(ev.target)) tanca();
});
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && obert) { tanca(); ev.stopPropagation(); } }, true);

/**
 * Converteix un <input> en un selector de color.
 * opcions: buit (text de l'opció «sense color», o null si no n'hi ha), colors (funció que retorna els
 *          colors del document per oferir-los), perDefecte (valor que es mostra si el camp és buit)
 */
export function selectorColor(input, opcions = {}) {
  input.type = "text";
  input.hidden = true;
  input.dataset.color = "";
  const mostra = el("span", { classe: "mostra-color", "aria-hidden": "true" });
  const etiqueta = el("span", { classe: "text-color" });
  const boto = el("button", { type: "button", classe: "boto-color" }, mostra, etiqueta);
  input.after(boto);

  const pinta = () => {
    const perDefecte = typeof opcions.perDefecte === "function" ? opcions.perDefecte() : opcions.perDefecte;
    const valor = input.value || perDefecte || "";
    mostra.style.background = valor ? colorCss(valor) : "";
    mostra.classList.toggle("buit", !valor);
    etiqueta.textContent = input.value ? descriuColor(input.value) : perDefecte ? `${descriuColor(perDefecte)} (estil)` : opcions.buit || "Cap";
    boto.disabled = input.disabled;
    boto.title = llegeixCmyk(input.value) ? "Color CMYK: surt exacte al PDF per a impremta" : "Tria el color";
  };
  // Quan el codi canvia el valor o el desactiva, el botó s'actualitza.
  const proto = HTMLInputElement.prototype;
  for (const prop of ["value", "disabled"]) {
    const desc = Object.getOwnPropertyDescriptor(proto, prop);
    Object.defineProperty(input, prop, {
      configurable: true,
      get() { return desc.get.call(this); },
      set(v) { desc.set.call(this, v); pinta(); },
    });
  }
  const canvia = (valor) => {
    input.value = valor;
    input.dispatchEvent(new Event("input", { bubbles: true }));
  };
  boto.addEventListener("click", () => (obert?.input === input ? tanca() : obre(input, boto, opcions, canvia)));
  pinta();
  return { pinta };
}

function obre(input, boto, opcions, canvia) {
  tanca();
  const popover = el("div", { classe: "popover-color", role: "dialog", "aria-label": "Color" });
  const perDefecte = typeof opcions.perDefecte === "function" ? opcions.perDefecte() : opcions.perDefecte;
  const inicial = input.value || perDefecte || "";
  let cmyk = llegeixCmyk(inicial) || (inicial.startsWith("#") ? hexACmyk(inicial) : [0, 0, 0, 100]);

  const previsualitzacio = el("span", { classe: "mostra-color gran", "aria-hidden": "true" });
  const valorText = el("span", { classe: "font-mono text-[12px] text-ink-700" });
  const pintaPrevia = () => {
    previsualitzacio.style.background = cmykAHex(cmyk);
    valorText.textContent = descriuColor(`cmyk(${cmyk.join(",")})`);
  };

  // Quatre canals: barra i número.
  const files = CANALS.map(([clau, nom, color], i) => {
    const barra = el("input", { type: "range", min: "0", max: "100", step: "1", "aria-label": `${nom} (%)`, classe: "barra-canal" });
    barra.style.setProperty("--canal", color);
    const numero = el("input", { type: "number", min: "0", max: "100", step: "0.5", "aria-label": `${nom} (%)`, classe: "camp w-16 px-2 py-1 text-right font-mono text-[13px]" });
    const posa = (v, origen) => {
      cmyk[i] = Math.min(100, Math.max(0, Number(v) || 0));
      if (origen !== barra) barra.value = cmyk[i];
      if (origen !== numero) numero.value = cmyk[i];
      pintaPrevia();
      canvia(`cmyk(${cmyk.join(",")})`);
    };
    barra.value = numero.value = cmyk[i];
    barra.addEventListener("input", () => posa(barra.value, barra));
    numero.addEventListener("input", () => numero.value !== "" && posa(numero.value, numero));
    return { fila: el("label", { classe: "fila-canal" }, el("span", { text: nom, classe: "w-4 font-mono text-[12px] font-semibold" }), barra, numero, el("span", { text: "%", classe: "text-[12px] text-ink-500" })), posa };
  });
  const posaTot = (valors) => valors.forEach((v, i) => files[i].posa(v));

  const mostres = (llista) => el("div", { classe: "flex flex-wrap gap-1" }, ...llista.map(([nom, valor]) => {
    const b = el("button", { type: "button", classe: "mostra-paleta", title: `${nom} · ${descriuColor(valor)}`, "aria-label": nom });
    b.style.background = colorCss(valor);
    b.addEventListener("click", () => {
      const v = llegeixCmyk(valor);
      if (v) posaTot(v);
      else { canvia(valor); tanca(); }
    });
    return b;
  }));

  const delDocument = [...new Set((opcions.colors?.() || []).filter(Boolean))].slice(0, 14).map((v) => [descriuColor(v), v]);
  const rgb = el("input", { type: "color", classe: "h-8 w-10 cursor-pointer rounded border border-paper-300 bg-white p-0.5", "aria-label": "Color RGB" });
  rgb.value = input.value?.startsWith("#") ? input.value : cmykAHex(cmyk);
  rgb.addEventListener("input", () => canvia(rgb.value));

  popover.append(
    el("div", { classe: "flex items-center gap-2" }, previsualitzacio, valorText),
    ...files.map((f) => f.fila),
    el("p", { classe: "etiqueta mb-0 mt-1", text: "Tintes" }), mostres(PALETA),
    ...(delDocument.length ? [el("p", { classe: "etiqueta mb-0 mt-1", text: "D'aquest cançoner" }), mostres(delDocument)] : []),
    el("div", { classe: "mt-1 flex items-center justify-between gap-2 border-t border-paper-200 pt-2 text-[12px] text-ink-500" },
      el("label", { classe: "flex items-center gap-2" }, rgb, el("span", { text: "o en RGB (pantalla)" })),
      ...(opcions.buit ? [(() => {
        const b = el("button", { type: "button", classe: "btn btn-fantasma btn-petit", text: opcions.buit });
        b.addEventListener("click", () => { canvia(""); tanca(); });
        return b;
      })()] : [])),
    el("p", { classe: "text-[11px] leading-snug text-ink-500", text: "En CMYK, el color surt exacte al PDF per a impremta. A la pantalla és una aproximació." }),
  );
  pintaPrevia();
  document.body.append(popover);
  const r = boto.getBoundingClientRect();
  const left = Math.min(window.innerWidth - popover.offsetWidth - 8, Math.max(8, r.right - popover.offsetWidth));
  const top = r.bottom + 6 + popover.offsetHeight < window.innerHeight ? r.bottom + 6 : Math.max(8, r.top - popover.offsetHeight - 6);
  Object.assign(popover.style, { left: `${left}px`, top: `${top}px` });
  obert = { input, boto, popover };
  files[0].fila.querySelector("input[type=number]").focus();
}
