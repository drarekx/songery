// Càlculs dels gestos de l'editor (moure, canviar la mida, girar i seleccionar), sense DOM ni estat:
// reben els elements tal com eren en començar el gest i on és el punter, i diuen on han de quedar.
// Totes les mesures són en mil·límetres sobre la pàgina A5 (148 × 210 mm).
import { ALT, AMPLE } from "./pagines.js";

/** Marge habitual de les pàgines (les guies s'hi enganxen). */
export const MARGE = 13;
/** Distància (mm) a què una vora s'enganxa a una guia. */
export const TOLERANCIA = 1.6;

/** Arrodoneix a dècimes de mil·límetre (com es desen les posicions). */
export const arrodoneix = (v) => Math.round(v * 10) / 10;

/** Cantonades d'un element, tenint en compte la rotació (al voltant del centre). */
export function cantonades(e) {
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

/** Requadre (sense girar) que envolta uns elements, tenint en compte la rotació de cadascun. */
export function requadre(elements) {
  const punts = elements.flatMap(cantonades);
  const xs = punts.map((q) => q[0]);
  const ys = punts.map((q) => q[1]);
  const x = Math.min(...xs);
  const y = Math.min(...ys);
  return { x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y };
}

/** Línies on s'enganxen els elements: vores, marges i centre de la pàgina, i vores i centres dels
 *  altres elements (els que es mouen, exclosos). */
export function guies(elements, exclou = []) {
  const xs = [0, MARGE, AMPLE / 2, AMPLE - MARGE, AMPLE];
  const ys = [0, MARGE, ALT / 2, ALT - MARGE, ALT];
  for (const e of elements) {
    if (exclou.includes(e.id)) continue;
    xs.push(e.x, e.x + e.w / 2, e.x + e.w);
    ys.push(e.y, e.y + e.h / 2, e.y + e.h);
  }
  return { xs, ys };
}

/** La guia més propera a algun dels valors, si és a menys de la tolerància: {d (desplaçament), linia}. */
export function enganxa(valors, candidates, tolerancia = TOLERANCIA) {
  let millor = null;
  for (const v of valors) for (const c of candidates) {
    const d = c - v;
    if (Math.abs(d) <= tolerancia && (!millor || Math.abs(d) < Math.abs(millor.d))) millor = { d, linia: c };
  }
  return millor;
}

/**
 * Moure: els originals es desplacen (dx, dy); amb guies, el requadre s'enganxa per la vora o pel centre.
 * Retorna {posicions: [{x, y}] (en l'ordre dels originals), lx, ly (guies que s'han fet servir)}.
 */
export function mou({ originals, requadre: b, dx, dy, guies: g = null }) {
  let mx = dx;
  let my = dy;
  const lx = [];
  const ly = [];
  if (g) {
    const gx = enganxa([b.x + dx, b.x + dx + b.w / 2, b.x + dx + b.w], g.xs);
    const gy = enganxa([b.y + dy, b.y + dy + b.h / 2, b.y + dy + b.h], g.ys);
    if (gx) { mx += gx.d; lx.push(gx.linia); }
    if (gy) { my += gy.d; ly.push(gy.linia); }
  }
  return { posicions: originals.map((o) => ({ x: arrodoneix(o.x + mx), y: arrodoneix(o.y + my) })), lx, ly };
}

/**
 * Canviar la mida amb una nansa (n, ne, e, se, s, sw, w, nw). Amb un sol element, el canvi és sobre
 * l'element; amb diversos, sobre el requadre comú i tots s'escalen. Les cantonades mantenen la
 * proporció si es prem ⇧, si és una imatge o si és un grup.
 * Retorna {posicions: [{x, y, w, h}], proporcio, factor (escala horitzontal del grup), lx, ly}.
 */
export function canviaMida({ originals, requadre: b, nansa: n, dx, dy, majuscules = false, esImatge = false, guies: g = null }) {
  const sol = originals.length === 1;
  const o0 = sol ? originals[0] : b;
  let { x, y, w, h } = o0;
  const lx = [];
  const ly = [];
  if (n.includes("e")) w = o0.w + dx;
  if (n.includes("s")) h = o0.h + dy;
  if (n.includes("w")) { w = o0.w - dx; x = o0.x + dx; }
  if (n.includes("n")) { h = o0.h - dy; y = o0.y + dy; }
  const cantonada = n.length === 2;
  const proporcio = cantonada && (majuscules || !sol || esImatge);
  if (proporcio) {
    h = w * (o0.h / o0.w);
    if (n.includes("n")) y = o0.y + o0.h - h;
  } else if (g) {
    if (n.includes("e")) { const t = enganxa([x + w], g.xs); if (t) { w += t.d; lx.push(t.linia); } }
    if (n.includes("w")) { const t = enganxa([x], g.xs); if (t) { x += t.d; w -= t.d; lx.push(t.linia); } }
    if (n.includes("s")) { const t = enganxa([y + h], g.ys); if (t) { h += t.d; ly.push(t.linia); } }
    if (n.includes("n")) { const t = enganxa([y], g.ys); if (t) { y += t.d; h -= t.d; ly.push(t.linia); } }
  }
  w = Math.max(2, w);
  h = Math.max(2, h);
  if (sol) {
    return { posicions: [{ x: arrodoneix(x), y: arrodoneix(y), w: arrodoneix(w), h: arrodoneix(h) }], proporcio, factor: w / o0.w, lx, ly };
  }
  const sx = w / b.w;
  const sy = h / b.h;
  const posicions = originals.map((o) => ({
    x: arrodoneix(x + (o.x - b.x) * sx), y: arrodoneix(y + (o.y - b.y) * sy),
    w: arrodoneix(Math.max(1, o.w * sx)), h: arrodoneix(Math.max(1, o.h * sy)),
  }));
  return { posicions, proporcio, factor: sx, lx, ly };
}

/** Angle normalitzat a (-180, 180]. */
export const normalitzaAngle = (graus) => ((Math.round(graus) % 360) + 540) % 360 - 180;

/**
 * Girar amb la nansa de rotació, al voltant del centre del requadre. Un sol element pren l'angle del
 * punter (la nansa és a dalt) i s'enganxa a 0/90/180° si hi és a prop; diversos giren tots el que ha
 * girat el punter. Amb ⇧, de 15° en 15°.
 * Retorna [{x, y, rotacio}] en l'ordre dels originals.
 */
export function gira({ originals, requadre: b, inici, punt, majuscules = false }) {
  const cx = b.x + b.w / 2;
  const cy = b.y + b.h / 2;
  const angle = (p) => (Math.atan2(p.y - cy, p.x - cx) * 180) / Math.PI;
  const sol = originals.length === 1;
  let delta = sol ? angle(punt) + 90 - (originals[0].rotacio || 0) : angle(punt) - angle(inici);
  const final = (o) => normalitzaAngle((o.rotacio || 0) + delta);
  if (majuscules) delta = Math.round(delta / 15) * 15;
  else if (sol) {
    const g = final(originals[0]);
    if (Math.abs(g - Math.round(g / 90) * 90) <= 3) delta += Math.round(g / 90) * 90 - g;
  }
  const rad = (delta * Math.PI) / 180;
  return originals.map((o) => {
    const ox = o.x + o.w / 2 - cx;
    const oy = o.y + o.h / 2 - cy;
    return {
      x: arrodoneix(cx + ox * Math.cos(rad) - oy * Math.sin(rad) - o.w / 2),
      y: arrodoneix(cy + ox * Math.sin(rad) + oy * Math.cos(rad) - o.h / 2),
      rotacio: final(o),
    };
  });
}

/** Mida de lletra d'un element escalat (en escalar un grup, els textos també canvien de mida). */
export const midaEscalada = (mida, factor) => Math.max(3, Math.round(mida * factor * 10) / 10);

/**
 * Selecció en clicar un element: nous són els ids que se seleccionen (l'element o el seu grup).
 * Amb afegeix (⇧ + clic): si ja hi eren tots, es treuen; si no, s'afegeixen.
 * Retorna {id (l'element principal), ids}.
 */
export function novaSeleccio(actuals, nous, id, afegeix = false) {
  if (!afegeix || !actuals.length) return { id, ids: nous };
  const ja = nous.every((x) => actuals.includes(x));
  const ids = ja ? actuals.filter((x) => !nous.includes(x)) : [...new Set([...actuals, ...nous])];
  return { id: ids.includes(id) ? id : (ids[0] ?? null), ids };
}

/** Elements que toquen un rectangle (selecció arrossegant en una zona buida); els bloquejats no. */
export function dinsRectangle(elements, r) {
  return elements.filter((e) => {
    if (e.bloquejat) return false;
    const q = requadre([e]);
    return q.x < r.x + r.w && q.x + q.w > r.x && q.y < r.y + r.h && q.y + q.h > r.y;
  });
}
