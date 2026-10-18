// Motor de dibuix: colors per a impremta, transport d'acords, estils i QR.
import { describe, expect, it } from "vitest";
import { cmykAHex, colorCss, cssEstils, llegeixCmyk, registraColors, svgQR, transportaAcord, transportaPagines } from "@/pagines.js";

describe("colors CMYK", () => {
  it("llegeix i valida el format", () => {
    expect(llegeixCmyk("cmyk( 0, 100 ,100,0 )")).toEqual([0, 100, 100, 0]);
    expect(llegeixCmyk("cmyk(150,0,0,0)")).toEqual([100, 0, 0, 0]);
    expect(llegeixCmyk("#ff0000")).toBeNull();
  });

  it("aproxima com colors.py (les tintes es multipliquen)", () => {
    // Els mateixos valors que dona canconer/colors.py: han de coincidir perquè els testimonis siguin únics.
    expect(cmykAHex([0, 100, 100, 0])).toBe("#e20000");
    expect(cmykAHex([0, 0, 0, 100])).toBe("#1e1c1b");
    expect(cmykAHex([100, 0, 0, 0])).toBe("#009ee0");
    expect(cmykAHex([0, 0, 0, 0])).toBe("#ffffff");
  });

  it("fa servir el testimoni de la taula del llibret si n'hi ha", () => {
    expect(colorCss("#c4321f")).toBe("#c4321f");
    expect(colorCss("cmyk(60,40,40,100)")).toBe(cmykAHex([60, 40, 40, 100]));
    registraColors({ "cmyk(60,40,40,100)": "#000001" });
    expect(colorCss("cmyk(60, 40, 40, 100)")).toBe("#000001");
  });
});

describe("transport", () => {
  it("transporta acords amb baix i manté sostinguts o bemolls", () => {
    expect(transportaAcord("G", 2)).toBe("A");
    expect(transportaAcord("D/F#", 2)).toBe("E/G#");
    expect(transportaAcord("Bb", 2)).toBe("C");
  });

  it("transporta també els diagrames d'acord de les pàgines", () => {
    const [p] = transportaPagines([{ elements: [{ tipus: "diagrama", acord: "C" }, { tipus: "text", text: "C" }] }], 2);
    expect(p.elements.map((e) => e.acord ?? e.text)).toEqual(["D", "C"]);
  });
});

describe("estils i QR", () => {
  it("limita els estils a un àmbit (diversos cançoners a la mateixa pàgina)", () => {
    const css = cssEstils({ titol: { font: "display", mida: 18, color: "cmyk(0,100,100,0)" } }, '[data-canconer="a"]');
    expect(css).toContain('[data-canconer="a"] .estil-titol{');
    expect(css).toContain(`color:${cmykAHex([0, 100, 100, 0])}`);
  });

  it("genera el QR en SVG sense connexió", () => {
    const svg = svgQR("https://youtu.be/dQw4w9WgXcQ?t=42");
    expect(svg.startsWith("<svg")).toBe(true);
    expect(svg).toContain('fill="#fff"');
  });
});
