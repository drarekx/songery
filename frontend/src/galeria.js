// Galeria de mèdia (GaleriaMedia.vue): editor.js l'obre amb obreGaleria({ tria }) i, quan s'hi tria una
// imatge, rep {id, url, nom} a «tria». Sense «tria», només serveix per ordenar la mèdia.
import { reactive } from "vue";

export const galeria = reactive({ oberta: false, tria: null, titol: "" });

export function obreGaleria({ tria = null, titol = "Afegeix a la pàgina" } = {}) {
  galeria.tria = tria;
  galeria.titol = titol;
  galeria.oberta = true;
}

export function tancaGaleria() {
  galeria.oberta = false;
  galeria.tria = null;
}

/** Puja un fitxer a la mèdia (a una carpeta o sense). Torna {id, url} o llança un Error amb el missatge. */
export async function pujaAMedia(fitxer, carpeta = null) {
  const formulari = new FormData();
  formulari.append("imatge", fitxer, fitxer.name || "imatge.png");
  if (carpeta) formulari.append("carpeta", carpeta);
  const r = await fetch("/api/imatges", { method: "POST", body: formulari });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || "No s'ha pogut pujar la imatge.");
  return d;
}

export const EXTENSIONS = ["png", "jpg", "jpeg", "webp", "gif"];
export const esImatgeAdmesa = (fitxer) => EXTENSIONS.includes(String(fitxer.name || "").split(".").pop().toLowerCase())
  || (!/\./.test(fitxer.name || "") && /^image\/(png|jpeg|webp|gif)$/.test(fitxer.type));
