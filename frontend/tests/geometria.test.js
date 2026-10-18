// Càlculs dels gestos de l'editor: moure, canviar la mida, girar, guies i selecció.
import { describe, expect, it } from "vitest";
import {
  MARGE, arrodoneix, canviaMida, cantonades, dinsRectangle, enganxa, gira, guies, midaEscalada, mou, normalitzaAngle,
  novaSeleccio, requadre,
} from "@/geometria.js";

const el = (id, x, y, w, h, extra = {}) => ({ id, x, y, w, h, rotacio: 0, ...extra });

describe("requadres", () => {
  it("sense girar, el requadre és l'element", () => {
    expect(requadre([el("a", 10, 20, 30, 40)])).toEqual({ x: 10, y: 20, w: 30, h: 40 });
  });

  it("girat 90°, el requadre es gira al voltant del centre", () => {
    const r = requadre([el("a", 10, 20, 40, 20, { rotacio: 90 })]);
    expect([r.x, r.y, r.w, r.h].map((v) => Math.round(v * 1000) / 1000)).toEqual([20, 10, 20, 40]);
    expect(cantonades(el("a", 0, 0, 10, 10))).toHaveLength(4);
  });

  it("de diversos elements, els envolta tots", () => {
    expect(requadre([el("a", 10, 10, 10, 10), el("b", 50, 30, 20, 5)])).toEqual({ x: 10, y: 10, w: 60, h: 25 });
  });
});

describe("guies i enganxar", () => {
  it("la pàgina, els marges i els altres elements (no els que es mouen)", () => {
    const g = guies([el("a", 20, 30, 10, 10), el("b", 100, 100, 10, 10)], ["b"]);
    expect(g.xs).toEqual(expect.arrayContaining([0, MARGE, 74, 135, 148, 20, 25, 30]));
    expect(g.xs).not.toContain(105);
  });

  it("enganxa a la guia més propera dins la tolerància", () => {
    expect(enganxa([12], [13, 0])).toEqual({ d: 1, linia: 13 });
    expect(enganxa([20], [13])).toBeNull();
    expect(enganxa([12.5, 50], [13, 50.4]).linia).toBe(50.4);
  });
});

describe("moure", () => {
  it("sense guies, es desplaça tal qual", () => {
    const { posicions, lx } = mou({ originals: [el("a", 10, 10, 20, 20)], requadre: { x: 10, y: 10, w: 20, h: 20 }, dx: 5.04, dy: -2 });
    expect(posicions).toEqual([{ x: 15, y: 8 }]);
    expect(lx).toEqual([]);
  });

  it("amb guies, la vora s'enganxa al marge i ho diu", () => {
    const o = el("a", 20, 50, 30, 10);
    const r = mou({ originals: [o], requadre: o, dx: -6, dy: 0, guies: { xs: [MARGE], ys: [] } });
    expect(r.posicions[0].x).toBe(MARGE); // 20 - 6 = 14, a 1 mm del marge: s'hi enganxa
    expect(r.lx).toEqual([MARGE]);
  });
});

describe("canviar la mida", () => {
  const o = el("a", 10, 10, 40, 20);

  it("per un costat, sense mantenir la proporció; mínim 2 mm", () => {
    expect(canviaMida({ originals: [o], requadre: o, nansa: "e", dx: 10, dy: 99 }).posicions[0]).toEqual({ x: 10, y: 10, w: 50, h: 20 });
    expect(canviaMida({ originals: [o], requadre: o, nansa: "w", dx: 50, dy: 0 }).posicions[0].w).toBe(2);
  });

  it("per una cantonada, només manté la proporció amb ⇧ o si és una imatge", () => {
    expect(canviaMida({ originals: [o], requadre: o, nansa: "se", dx: 20, dy: 0 }).posicions[0]).toEqual({ x: 10, y: 10, w: 60, h: 20 });
    expect(canviaMida({ originals: [o], requadre: o, nansa: "se", dx: 20, dy: 0, majuscules: true }).posicions[0]).toEqual({ x: 10, y: 10, w: 60, h: 30 });
    const n = canviaMida({ originals: [o], requadre: o, nansa: "ne", dx: 20, dy: 0, esImatge: true }).posicions[0];
    expect(n).toEqual({ x: 10, y: 0, w: 60, h: 30 }); // per dalt, la vora de baix es queda on és
  });

  it("un grup s'escala sencer i dona el factor (per a la mida de la lletra)", () => {
    const a = el("a", 0, 0, 10, 10);
    const b = el("b", 10, 10, 10, 10);
    const r = canviaMida({ originals: [a, b], requadre: requadre([a, b]), nansa: "se", dx: 20, dy: 0 });
    expect(r.proporcio).toBe(true);
    expect(r.factor).toBe(2);
    expect(r.posicions).toEqual([{ x: 0, y: 0, w: 20, h: 20 }, { x: 20, y: 20, w: 20, h: 20 }]);
    expect(midaEscalada(11, r.factor)).toBe(22);
    expect(midaEscalada(5, 0.1)).toBe(3);
  });

  it("amb guies, la vora s'hi enganxa", () => {
    const r = canviaMida({ originals: [o], requadre: o, nansa: "e", dx: 84, dy: 0, guies: { xs: [135], ys: [] } });
    expect(r.posicions[0].w).toBe(125);
    expect(r.lx).toEqual([135]);
  });
});

describe("girar", () => {
  const o = el("a", 0, 0, 20, 10); // centre (10, 5)

  it("un element pren l'angle del punter (la nansa és a dalt)", () => {
    const [r] = gira({ originals: [o], requadre: o, inici: { x: 10, y: -5 }, punt: { x: 30, y: -2 } });
    expect(r.rotacio).toBe(71); // atan2(-7, 20) + 90°
  });

  it("s'enganxa a 90° si hi és a prop, i amb ⇧ va de 15° en 15°", () => {
    const [prop] = gira({ originals: [o], requadre: o, inici: { x: 10, y: -5 }, punt: { x: 30, y: 4.2 } });
    expect(prop.rotacio).toBe(90);
    const [quinze] = gira({ originals: [o], requadre: o, inici: { x: 10, y: -5 }, punt: { x: 20, y: -5 }, majuscules: true });
    expect(quinze.rotacio % 15).toBe(0);
  });

  it("un grup gira al voltant del centre comú", () => {
    const a = el("a", 0, 0, 10, 10);
    const b = el("b", 20, 0, 10, 10); // requadre 0..30 × 0..10, centre (15, 5)
    const [ra, rb] = gira({ originals: [a, b], requadre: requadre([a, b]), inici: { x: 30, y: 5 }, punt: { x: 15, y: 20 } });
    expect([ra.x, ra.y, ra.rotacio]).toEqual([10, -10, 90]);
    expect([rb.x, rb.y, rb.rotacio]).toEqual([10, 10, 90]);
  });

  it("normalitza els angles", () => {
    expect(normalitzaAngle(270)).toBe(-90);
    expect(normalitzaAngle(180)).toBe(-180);
    expect(normalitzaAngle(-181)).toBe(179);
    expect(arrodoneix(1.234)).toBe(1.2);
  });
});

describe("selecció", () => {
  it("clicar selecciona; amb ⇧ afegeix o treu", () => {
    expect(novaSeleccio([], ["a"], "a")).toEqual({ id: "a", ids: ["a"] });
    expect(novaSeleccio(["a"], ["b"], "b", true)).toEqual({ id: "b", ids: ["a", "b"] });
    expect(novaSeleccio(["a", "b"], ["b"], "b", true)).toEqual({ id: "a", ids: ["a"] });
    expect(novaSeleccio(["a"], ["a"], "a", true)).toEqual({ id: null, ids: [] });
  });

  it("el rectangle selecciona el que toca, però no el que està bloquejat", () => {
    const els = [el("a", 0, 0, 10, 10), el("b", 50, 50, 10, 10), el("c", 5, 5, 10, 10, { bloquejat: true })];
    expect(dinsRectangle(els, { x: 8, y: 8, w: 5, h: 5 }).map((e) => e.id)).toEqual(["a"]);
  });
});
