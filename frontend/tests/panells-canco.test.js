// Panells de la pestanya Cançó, Estils i Capes.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ordenaCapes } from "@/capes.js";
import PanellCanco from "@/components/PanellCanco.vue";
import PanellCapes from "@/components/PanellCapes.vue";
import PanellEstils from "@/components/PanellEstils.vue";
import { useEditorStore } from "@/stores/editor.js";

let pinia;
let store;
let ponts;
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  store = useEditorStore();
  ponts = new Proxy({}, { get: (objecte, nom) => (objecte[nom] ??= vi.fn()) });
  store.connecta(Object.fromEntries(["canviaDadesCanco", "canviaEntrada", "aplicaTransport", "treuCanco", "obreHistorial",
    "canviaEstil", "triaFont", "colorsDelDocument", "ressaltaCapes", "seleccionaCapa", "bloquejaCapa", "mouCapa"].map((n) => [n, ponts[n]])));
});
const munta = (component) => mount(component, { global: { plugins: [pinia] } });

describe("PanellCanco", () => {
  beforeEach(() => store.sincronitza({
    canco: { id: "c1", titol: "Prova", autor: "Jo" },
    entrada: { transport: 11, inclosa: true, inici: "esquerra", versio_ultima: 3 },
  }));

  it("sense cançó oberta, ho diu", () => {
    store.sincronitza({ canco: null, entrada: null });
    expect(munta(PanellCanco).text()).toContain("Selecciona una cançó");
  });

  it("canvia el títol i dona la volta al transport", async () => {
    const w = munta(PanellCanco);
    expect(w.text()).toContain("+11");
    expect(w.text()).toContain("3 versions");
    await w.find("#titol-ev").setValue("Nou títol");
    expect(ponts.canviaDadesCanco).toHaveBeenLastCalledWith("titol", "Nou títol");
    await w.find('[aria-label="Puja un semitò"]').trigger("click");
    expect(ponts.canviaEntrada).toHaveBeenLastCalledWith({ transport: 0 }); // +12 és el mateix to: torna a 0
    await w.find('[aria-label="Baixa un semitò"]').trigger("click");
    expect(ponts.canviaEntrada).toHaveBeenLastCalledWith({ transport: -1 });
    expect(w.text()).toContain("-1");
  });

  it("surt al PDF, on comença i les accions", async () => {
    const w = munta(PanellCanco);
    const caselles = w.findAll('input[type="checkbox"]').filter((c) => !c.attributes("title")); // no les dels vídeos
    await caselles[0].setValue(false);
    expect(ponts.canviaEntrada).toHaveBeenLastCalledWith({ inclosa: false });
    await caselles[1].setValue(false);
    expect(ponts.canviaEntrada).toHaveBeenLastCalledWith({ inici: "qualsevol" });
    await w.findAll("button").find((b) => b.text().includes("Aplica el transport")).trigger("click");
    await w.findAll("button").find((b) => b.text().includes("Treu del cançoner")).trigger("click");
    expect(ponts.aplicaTransport).toHaveBeenCalled();
    expect(ponts.treuCanco).toHaveBeenCalled();
  });

  it("en una versió fixada no es pot editar", () => {
    store.sincronitza({ editable: false });
    const w = munta(PanellCanco);
    expect(w.find("#titol-ev").attributes("readonly")).toBeDefined();
    expect(w.findAll("button").find((b) => b.text().includes("Aplica")).element.disabled).toBe(true);
  });
});

describe("PanellEstils", () => {
  beforeEach(() => store.sincronitza({
    estils: { titol: { nom: "Títol", font: "display", mida: 18, pes: 600, interlineat: 1.1, espaiat: 0, color: "#1b1a17", cursiva: false, majuscules: false } },
    tipografies: [{ clau: "display", nom: "Newsreader" }],
  }));

  it("mostra els estils i en canvia les propietats", async () => {
    const w = munta(PanellEstils);
    expect(w.text()).toContain("Títol");
    expect(w.text()).toContain("Newsreader");
    await w.find('input[type="number"]').setValue("20");
    expect(ponts.canviaEstil).toHaveBeenLastCalledWith("titol", "mida", 20);
    await w.find("select").setValue("700");
    expect(ponts.canviaEstil).toHaveBeenLastCalledWith("titol", "pes", 700);
    await w.find('input[type="checkbox"]').setValue(true);
    expect(ponts.canviaEstil).toHaveBeenLastCalledWith("titol", "cursiva", true);
    expect(w.text()).toContain("20 pt");
  });

  it("la tipografia es tria amb el selector de l'editor", async () => {
    const w = munta(PanellEstils);
    await w.find(".selector-font").trigger("click");
    expect(ponts.triaFont.mock.lastCall[1]).toBe("titol");
  });
});

describe("PanellCapes", () => {
  const capa = (id, extra = {}) => ({ id, tipus: "text", nom: `Capa ${id}`, grup: null, bloquejat: false, seleccionat: false, index: 0, total: 3, ...extra });

  it("els membres d'un grup van junts sota una capçalera", () => {
    const ordre = ordenaCapes([capa("a", { grup: "g" }), capa("b"), capa("c", { grup: "g" })]);
    expect(ordre.map((e) => e.capcalera ? `grup:${e.membres.length}` : e.id)).toEqual(["grup:2", "a", "c", "b"]);
  });

  it("selecciona, bloqueja i mou les capes", async () => {
    store.sincronitza({ capes: [{ etiqueta: "Pàgina 4", mestra: 1, elements: [capa("a", { index: 2 }), capa("b", { index: 1, bloquejat: true }), capa("c")] }] });
    const w = munta(PanellCapes);
    expect(w.text()).toContain("Pàgina 4");
    expect(w.text()).toContain("+ 1 de la pàgina mestra");
    await w.findAll("button").find((b) => b.text() === "Capa b").trigger("click");
    expect(ponts.seleccionaCapa).toHaveBeenLastCalledWith(0, "b", { afegeix: false, sol: true });
    await w.findAll('[aria-label="Desbloqueja"]')[0].trigger("click");
    expect(ponts.bloquejaCapa).toHaveBeenLastCalledWith(0, "b");
    const endavant = w.findAll('[aria-label="Porta endavant"]');
    expect(endavant[0].element.disabled).toBe(true); // ja és la de més davant
    await endavant[1].trigger("click");
    expect(ponts.mouCapa).toHaveBeenLastCalledWith(0, "b", 1);
    await w.find(".fila-capa").trigger("mouseenter");
    expect(ponts.ressaltaCapes).toHaveBeenLastCalledWith(0, ["a"], true);
  });

  it("sense res obert, ho diu", () => {
    expect(munta(PanellCapes).text()).toContain("Obre una cançó");
  });
});
