// Utilitats dels colors per a impremta (sense DOM): paleta de tintes, descripció i conversions.
import { llegeixCmyk } from "./pagines.js";

/** Tintes habituals d'impremta. */
export const PALETA = [
  ["Negre (K 100)", "cmyk(0,0,0,100)"], ["Gris fosc (K 75)", "cmyk(0,0,0,75)"], ["Gris (K 50)", "cmyk(0,0,0,50)"],
  ["Gris clar (K 20)", "cmyk(0,0,0,20)"], ["Paper (sense tinta)", "cmyk(0,0,0,0)"],
  ["Vermell (M 100 Y 100)", "cmyk(0,100,100,0)"], ["Vermelló", "cmyk(0,85,90,10)"], ["Taronja", "cmyk(0,60,100,0)"],
  ["Groc", "cmyk(0,0,100,0)"], ["Verd", "cmyk(80,0,100,0)"], ["Cian", "cmyk(100,0,0,0)"],
  ["Blau", "cmyk(100,70,0,0)"], ["Magenta", "cmyk(0,100,0,0)"], ["Morat", "cmyk(60,90,0,0)"],
];

export const CANALS = [
  { clau: "c", nom: "C", color: "#00a0dc" },
  { clau: "m", nom: "M", color: "#e5007e" },
  { clau: "y", nom: "Y", color: "#f6d900" },
  { clau: "k", nom: "K", color: "#1b1a17" },
];

/** Text curt d'un color: «C0 M100 Y100 K0», «#c4321f» o «Cap». */
export function descriuColor(valor) {
  const cmyk = llegeixCmyk(valor);
  if (cmyk) return cmyk.map((v, i) => `${"CMYK"[i]}${Math.round(v * 10) / 10}`).join(" ");
  return valor || "Cap";
}

/** Aproximació inversa (per començar a editar en CMYK un color que era RGB). */
export function hexACmyk(hex) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255);
  const k = 1 - Math.max(r, g, b);
  if (k >= 1) return [0, 0, 0, 100];
  return [...[r, g, b].map((v) => Math.round(((1 - v - k) / (1 - k)) * 100)), Math.round(k * 100)];
}
