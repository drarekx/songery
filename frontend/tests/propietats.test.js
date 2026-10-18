// Panell de propietats: pàgina, element i selecció múltiple.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PanellPropietats from "@/components/PanellPropietats.vue";
import { useEditorStore } from "@/stores/editor.js";

let pinia;
let store;
let ponts;
const muntats = [];
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  store = useEditorStore();
  ponts = {};
  // Qualsevol pont que es cridi existeix (un vi.fn() nou), així es pot comprovar amb què s'ha cridat.
  store.ponts = new Proxy(ponts, { get: (o, nom) => (o[nom] ??= vi.fn()) });
  store.sincronitza({
    estils: { text: { nom: "Text", font: "sans", color: "cmyk(0,0,0,100)" }, titol: { nom: "Títol", font: "display" } },
    tipografies: [{ clau: "sans", nom: "Hanken Grotesk" }, { clau: "display", nom: "Newsreader" }],
    mestres: [{ id: "estandard", nom: "Estàndard" }, { id: "x", nom: "Banda" }],
  });
});
afterEach(() => muntats.splice(0).forEach((w) => w.unmount()));
const munta = () => {
  const w = mount(PanellPropietats, { global: { plugins: [pinia] }, attachTo: document.body });
  muntats.push(w);
  return w;
};
const element = (extra) => store.sincronitza({
  propietats: { mode: "element", element: { id: "e1", x: 10, y: 20, w: 50, h: 10, rotacio: 0, opacitat: 1, ...extra }, multi: null, pagina: null, moure: { visible: true, anterior: false, seguent: true } },
});

describe("pàgina", () => {
  it("canvia la mestra, el costat i el fons", async () => {
    store.sincronitza({ propietats: { mode: "pagina", pagina: { tipus: "canco", mestra: "x", costat: null, fons: "#ffffff" }, moure: {} } });
    const w = munta();
    const [mestra, costat] = w.findAll("select");
    await mestra.setValue("estandard");
    expect(ponts.canviaPagina).toHaveBeenLastCalledWith({ mestra: "estandard" });
    await costat.setValue("dreta");
    expect(ponts.canviaPagina).toHaveBeenLastCalledWith({ costat: "dreta" });
    expect(w.text()).toContain("⌘A"); // l'ajuda de les dreceres
  });

  it("una pàgina mestra es pot reanomenar, duplicar i esborrar", async () => {
    store.sincronitza({ propietats: { mode: "pagina", pagina: { tipus: "mestra", nomMestra: "Banda", mestraEsborrable: true }, moure: {} } });
    const w = munta();
    expect(w.text()).toContain("Pàgina mestra");
    await w.find("input").setValue("Banda vermella");
    expect(ponts.canviaNomMestra).toHaveBeenLastCalledWith("Banda vermella");
    await w.findAll("button").find((b) => b.text().includes("Esborra")).trigger("click");
    expect(ponts.esborraMestra).toHaveBeenCalled();
  });
});

describe("element", () => {
  it("un text: contingut, variables, estil, format i alineació", async () => {
    element({ tipus: "text", text: "Hola", estil: "text", alineacio: "left" });
    const w = munta();
    expect(w.text()).toContain("Text");
    const area = w.find("textarea");
    await area.setValue("Hola món");
    expect(ponts.canviaPropietats).toHaveBeenLastCalledWith({ text: "Hola món" });
    area.element.setSelectionRange(4, 4); // la variable va on hi ha el cursor
    await w.findAll("button").find((b) => b.text() === "{titol}").trigger("click");
    expect(ponts.canviaPropietats).toHaveBeenLastCalledWith({ text: "Hola{titol} món" });
    await w.find("select").setValue("titol");
    expect(ponts.canviaPropietats).toHaveBeenLastCalledWith({ estil: "titol" });
    await w.find('input[placeholder="estil"]').setValue("14");
    expect(ponts.canviaPropietats).toHaveBeenLastCalledWith({ format: { mida: 14 } });
    await w.findAll("button").find((b) => b.text() === "Centre").trigger("click");
    expect(ponts.canviaPropietats).toHaveBeenLastCalledWith({ alineacio: "center" });
    expect(w.text()).toContain("De l'estil");
  });

  it("la posició es mou sense tornar a dibuixar; girar i centrar", async () => {
    element({ tipus: "forma", fons: "#c4321f" });
    const w = munta();
    const x = w.findAll('input[type="number"]').find((c) => c.element.closest("label")?.textContent.includes("X (mm)"));
    await x.setValue("33");
    expect(ponts.canviaPosicio).toHaveBeenLastCalledWith("x", 33);
    await w.find('[aria-label="Gira 90° a la dreta"]').trigger("click");
    expect(ponts.gira).toHaveBeenLastCalledWith(90);
    await w.findAll("button").find((b) => b.text() === "Centra en vertical").trigger("click");
    expect(ponts.centra).toHaveBeenLastCalledWith("y");
    await w.findAll("button").find((b) => b.text().includes("Pàgina següent")).trigger("click");
    expect(ponts.accio).toHaveBeenLastCalledWith("a-pagina-seguent");
    expect(w.findAll("button").find((b) => b.text().includes("Pàgina anterior")).element.disabled).toBe(true);
  });

  it("un marc de lletra mostra la informació i avisa si no hi cap", () => {
    element({ tipus: "lletra", estil: "text", infoMarc: { alerta: true, text: "La lletra no hi cap." } });
    const w = munta();
    const avis = w.findAll("p").find((p) => p.text() === "La lletra no hi cap.");
    expect(avis.classes()).toContain("text-perill-700");
  });

  it("un QR massa petit avisa", () => {
    store.sincronitza({ videos: [{ id: "v1", video: "dQw4w9WgXcQ", titol: "Vídeo" }] });
    element({ tipus: "qr", w: 10, h: 10, peu: false, video: "v1" });
    expect(munta().text()).toContain("fes-lo de 15 mm o més");
  });

  it("en una versió fixada no es pot tocar", () => {
    store.sincronitza({ editable: false });
    element({ tipus: "forma" });
    const w = munta();
    expect(w.findAll('input[type="number"]').every((c) => c.element.disabled)).toBe(true);
  });
});

describe("selecció múltiple", () => {
  it("agrupa, alinea i desa a la biblioteca", async () => {
    store.sincronitza({ propietats: { mode: "multi", multi: { n: 3, grup: false, algunGrup: false }, moure: { visible: false } } });
    const w = munta();
    expect(w.text()).toContain("3 elements seleccionats");
    await w.findAll("button").find((b) => b.text() === "Agrupa").trigger("click");
    expect(ponts.accio).toHaveBeenLastCalledWith("agrupa");
    await w.find('[aria-label="Al mig"]').trigger("click");
    expect(ponts.alinea).toHaveBeenLastCalledWith("mig");
    expect(w.findAll("button").some((b) => b.text() === "Desagrupa")).toBe(false);
  });
});
