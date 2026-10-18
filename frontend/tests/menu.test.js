// Menú del botó dret.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import MenuContext from "@/components/MenuContext.vue";
import PanellLlista from "@/components/PanellLlista.vue";
import { useEditorStore } from "@/stores/editor.js";

let pinia;
let store;
const muntats = [];
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  store = useEditorStore();
});
afterEach(() => muntats.splice(0).forEach((w) => w.unmount()));
const munta = (component) => {
  const w = mount(component, { global: { plugins: [pinia] }, attachTo: document.body });
  muntats.push(w);
  return w;
};
const menu = () => document.querySelector(".menu-context");
const opcio = (text) => [...menu().querySelectorAll("button")].find((b) => b.textContent.includes(text));

describe("MenuContext", () => {
  it("mostra les opcions, les seccions i les dreceres, i fa l'acció triada", async () => {
    munta(MenuContext);
    const copia = vi.fn();
    store.obreMenu(100, 80, [
      { seccio: "2 elements" }, { text: "Copia", drecera: "⌘C", fes: copia }, { separador: true },
      { text: "Esborra", perill: true, fes: vi.fn() }, { text: "Enganxa", desactivat: true, fes: vi.fn() },
      { text: "Bloqueja", marcat: true, fes: vi.fn() },
    ]);
    await new Promise((r) => setTimeout(r));
    expect(menu().textContent).toContain("2 elements");
    expect(menu().textContent).toContain("⌘C");
    expect(opcio("Esborra").classList).toContain("perill");
    expect(opcio("Enganxa").disabled).toBe(true);
    expect(opcio("Bloqueja").getAttribute("aria-checked")).toBe("true");
    opcio("Copia").click();
    expect(copia).toHaveBeenCalled();
    expect(store.menu).toBeNull();
  });

  it("amb el teclat: fletxes i Intro, i Esc el tanca", async () => {
    munta(MenuContext);
    const a = vi.fn();
    const b = vi.fn();
    store.obreMenu(10, 10, [{ text: "A", fes: a }, { text: "Desactivada", desactivat: true }, { text: "B", fes: b }]);
    await new Promise((r) => setTimeout(r));
    const tecla = (key) => document.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
    tecla("ArrowDown");
    tecla("ArrowDown"); // se salta la desactivada
    tecla("Enter");
    expect(b).toHaveBeenCalled();
    expect(a).not.toHaveBeenCalled();
    store.obreMenu(10, 10, [{ text: "A", fes: a }]);
    tecla("Escape");
    expect(store.menu).toBeNull();
  });

  it("es tanca clicant fora", async () => {
    munta(MenuContext);
    store.obreMenu(10, 10, [{ text: "A", fes: vi.fn() }]);
    await new Promise((r) => setTimeout(r));
    document.body.dispatchEvent(new Event("pointerdown", { bubbles: true }));
    expect(store.menu).toBeNull();
  });
});

describe("menú de la llista de cançons", () => {
  it("el botó dret d'una cançó ofereix les seves opcions", async () => {
    const ponts = {};
    store.ponts = new Proxy(ponts, { get: (o, nom) => (o[nom] ??= vi.fn()) });
    store.sincronitza({ llista: { obert: null, total: 8, cancons: [
      { id: "a", titol: "Primera", tipus: "canco", inclosa: true, inici: "esquerra", usos: 1, pagines: [4] },
      { id: "b", titol: "Segona", tipus: "canco", inclosa: false, inici: "qualsevol", usos: 1, pagines: [] },
    ] } });
    munta(MenuContext);
    const w = munta(PanellLlista);
    await w.find('[data-id="b"]').trigger("contextmenu", { clientX: 20, clientY: 30 });
    await new Promise((r) => setTimeout(r));
    expect(menu().textContent).toContain("Segona");
    expect(opcio("Surt al PDF").getAttribute("aria-checked")).toBe("false");
    expect(opcio("Mou avall").disabled).toBe(true);
    opcio("Surt al PDF").click();
    expect(ponts.canviaEntrada).toHaveBeenLastCalledWith("b", { inclosa: true });
  });
});
