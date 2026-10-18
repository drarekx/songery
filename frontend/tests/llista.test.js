// Columna de l'esquerra: llibret, pàgines especials, cançons (ordre, surt al PDF) i mestres.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PanellLlista from "@/components/PanellLlista.vue";
import { useEditorStore } from "@/stores/editor.js";

let pinia;
let store;
let ponts;
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  store = useEditorStore();
  ponts = {};
  store.ponts = new Proxy(ponts, { get: (o, nom) => (o[nom] ??= vi.fn()) });
  const canco = (id, extra) => ({ id, titol: `Cançó ${id}`, tipus: "canco", inclosa: true, inici: "esquerra", usos: 1, versio_numero: null, desfasada: false, pagines: [], ...extra });
  store.sincronitza({
    mestres: [{ id: "estandard", nom: "Estàndard" }],
    llista: {
      obert: "canco:b", total: 12,
      cancons: [canco("a", { pagines: [4, 5] }), canco("b", { pagines: [6], versio_numero: 2, desfasada: true, usos: 3 }),
        canco("c", { inclosa: false, tipus: "pagina", titol: "Dedicatòria" })],
    },
  });
});
const munta = () => mount(PanellLlista, { global: { plugins: [pinia] }, attachTo: document.body });

describe("PanellLlista", () => {
  it("mostra les cançons amb on surten i el que tenen d'especial", () => {
    const w = munta();
    expect(w.text()).toContain("12 pàg.");
    expect(w.text()).toContain("2/3"); // dues de tres surten al PDF
    expect(w.text()).toContain("pàg. 4–5");
    expect(w.text()).toContain("v2 ↑");
    expect(w.text()).toContain("3×");
    expect(w.text()).toContain("fora del PDF");
    expect(w.text()).toContain("▫ Dedicatòria");
    expect(w.find('[data-id="b"]').classes()).toContain("bg-white"); // l'oberta
    w.unmount();
  });

  it("obre el que es clica", async () => {
    const w = munta();
    await w.findAll("button").find((b) => b.text().includes("Tot el llibret")).trigger("click");
    expect(ponts.obre).toHaveBeenLastCalledWith({ tipus: "llibre" });
    await w.findAll("button").find((b) => b.text() === "Portada").trigger("click");
    expect(ponts.obre).toHaveBeenLastCalledWith({ tipus: "especial", id: "portada" });
    await w.find('[data-id="a"] button').trigger("click");
    expect(ponts.obre).toHaveBeenLastCalledWith({ tipus: "canco", id: "a" });
    await w.findAll("button").find((b) => b.text().includes("Estàndard")).trigger("click");
    expect(ponts.obre).toHaveBeenLastCalledWith({ tipus: "mestra", id: "estandard" });
    w.unmount();
  });

  it("surt al PDF, moure i crear", async () => {
    const w = munta();
    await w.find('[data-id="a"] input').setValue(false);
    expect(ponts.canviaEntrada).toHaveBeenLastCalledWith("a", { inclosa: false });
    await w.find('[data-id="a"] [aria-label="Mou avall"]').trigger("click");
    expect(ponts.mouEntrada).toHaveBeenLastCalledWith("a", 1);
    expect(w.find('[data-id="a"] [aria-label="Mou amunt"]').element.disabled).toBe(true);
    await w.findAll("button").find((b) => b.text() === "+ Cançó").trigger("click");
    expect(ponts.creaEntrada).toHaveBeenLastCalledWith("canco");
    await w.find('[aria-label="Nova pàgina mestra"]').trigger("click");
    expect(ponts.novaMestra).toHaveBeenCalled();
    w.unmount();
  });

  it("reordena arrossegant i desa l'ordre en deixar-la", async () => {
    const w = munta();
    // Posicions de les files (happy-dom no fa disseny).
    w.findAll("li[data-id]").forEach((li, i) => {
      li.element.getBoundingClientRect = () => ({ top: i * 40, height: 40 });
      Object.defineProperty(li.element, "offsetHeight", { value: 40 });
    });
    await w.find('[data-id="a"] .nansa').trigger("pointerdown", { pointerId: 1 });
    await w.find("ol").trigger("pointermove", { clientY: 1000 }); // a sota de tot
    expect(w.findAll("li[data-id]").map((li) => li.attributes("data-id"))).toEqual(["b", "c", "a"]);
    await w.find("ol").trigger("pointerup");
    expect(ponts.desaOrdre).toHaveBeenLastCalledWith(["b", "c", "a"]);
    w.unmount();
  });

  it("canviar el títol a la pestanya Cançó el canvia a la llista", () => {
    store.sincronitza({ canco: { id: "b", titol: "Cançó b", autor: "" } });
    store.canviaDadesCanco("titol", "Títol nou");
    expect(store.llista.cancons.find((c) => c.id === "b").titol).toBe("Títol nou");
  });
});
