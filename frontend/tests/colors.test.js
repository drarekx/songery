import { describe, expect, it } from "vitest";
import { PALETA, descriuColor, hexACmyk } from "@/colors.js";

describe("utilitats de color", () => {
  it("descriu els colors", () => {
    expect(descriuColor("cmyk(0,100,100,0)")).toBe("C0 M100 Y100 K0");
    expect(descriuColor("cmyk(12.5,0,80,3)")).toBe("C12.5 M0 Y80 K3");
    expect(descriuColor("#c4321f")).toBe("#c4321f");
    expect(descriuColor("")).toBe("Cap");
  });

  it("converteix RGB a un CMYK de partida", () => {
    expect(hexACmyk("#000000")).toEqual([0, 0, 0, 100]);
    expect(hexACmyk("#ffffff")).toEqual([0, 0, 0, 0]);
    expect(hexACmyk("#ff0000")).toEqual([0, 100, 100, 0]);
  });

  it("la paleta són tintes CMYK vàlides", () => {
    expect(PALETA.every(([, v]) => /^cmyk\(/.test(v))).toBe(true);
  });
});
