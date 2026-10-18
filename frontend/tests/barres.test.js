// Barres del llenç: eines, format de la lletra i avisos.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AvisLlenc from "@/components/AvisLlenc.vue";
import BarraEines from "@/components/BarraEines.vue";
import BarraText from "@/components/BarraText.vue";
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
});
const munta = (component) => mount(component, { global: { plugins: [pinia] } });

describe("BarraEines", () => {
  it("només icones, amb el nom a l'etiqueta, i crida l'eina", async () => {
    const w = munta(BarraEines);
    const text = w.find('[data-eina="nou-text"]');
    expect(text.text()).toBe("");
    expect(text.attributes("data-tooltip")).toBe("Text");
    await text.trigger("click");
    expect(ponts.eina).toHaveBeenLastCalledWith("nou-text");
  });

  it("les eines de pàgina només amb una cançó editable; el panell d'acords es veu premut", async () => {
    const w = munta(BarraEines);
    expect(w.find('[data-eina="pagina-nova"]').element.disabled).toBe(true);
    store.sincronitza({ eines: { inactives: false, pagina: true, acordsObert: true } });
    await w.vm.$nextTick();
    expect(w.find('[data-eina="pagina-nova"]').element.disabled).toBe(false);
    expect(w.find('[data-eina="acords"]').attributes("aria-pressed")).toBe("true");
    store.sincronitza({ eines: { inactives: true, pagina: false, acordsObert: false } });
    await w.vm.$nextTick();
    expect(w.find('[role="toolbar"]').classes()).toContain("eines-inactives");
  });

  it("zoom", async () => {
    store.sincronitza({ zoom: 1.25 });
    const w = munta(BarraEines);
    expect(w.text()).toContain("125 %");
    await w.find('[aria-label="Apropa"]').trigger("click");
    expect(ponts.zoom).toHaveBeenLastCalledWith(1.25);
    await w.findAll("button").find((b) => b.text() === "Ajusta").trigger("click");
    expect(ponts.zoom).toHaveBeenLastCalledWith(null);
  });
});

describe("BarraText", () => {
  it("només es veu mentre s'edita una lletra", async () => {
    const w = munta(BarraText);
    expect(w.find('[role="toolbar"]').exists()).toBe(false);
    store.sincronitza({ edicio: { actius: { bold: true }, mida: 11.5, ajusta: true, efectiva: { text: "→ 9.8 pt perquè hi càpiga", alerta: false } } });
    await w.vm.$nextTick();
    expect(w.find('[aria-label="Negreta (⌘B)"]').attributes("aria-pressed")).toBe("true");
    expect(w.find('[aria-label="Cursiva (⌘I)"]').attributes("aria-pressed")).toBe("false");
    expect(w.text()).toContain("9.8 pt");
  });

  it("format, mida i ajust", async () => {
    store.sincronitza({ edicio: { actius: {}, mida: 11, ajusta: true, efectiva: null } });
    const w = munta(BarraText);
    await w.find('[aria-label="Afegeix un acord"]').trigger("click");
    expect(ponts.format).toHaveBeenLastCalledWith("acord");
    await w.find('[aria-label="Lletra més gran"]').trigger("click");
    expect(ponts.midaMarc).toHaveBeenLastCalledWith(11.5);
    await w.find('input[type="number"]').setValue("14");
    expect(ponts.midaMarc).toHaveBeenLastCalledWith(14);
    await w.find('input[type="checkbox"]').setValue(false);
    expect(ponts.ajustaMarc).toHaveBeenLastCalledWith(false);
    await w.findAll("button").find((b) => b.text() === "Fet").trigger("click");
    expect(ponts.format).toHaveBeenLastCalledWith("surt");
  });
});

describe("AvisLlenc", () => {
  it("mostra l'avís i fa les accions", async () => {
    const fes = vi.fn();
    store.sincronitza({ avis: { text: "Versió fixada.", accions: [{ text: "Edita la cançó", primari: true, fes }] } });
    const w = munta(AvisLlenc);
    expect(w.text()).toContain("Versió fixada.");
    await w.find("button").trigger("click");
    expect(fes).toHaveBeenCalled();
    store.sincronitza({ avis: null });
    await w.vm.$nextTick();
    expect(w.text()).toBe("");
  });
});

describe("BarraEines: la mà", () => {
  it("el botó de la mà es pot deixar premut", async () => {
    const w = munta(BarraEines);
    const boto = w.find('[aria-label="Mou el llenç"]');
    expect(boto.attributes("aria-pressed")).toBe("false");
    await boto.trigger("click");
    expect(ponts.ma).toHaveBeenCalled();
    store.sincronitza({ eines: { ...store.eines, ma: true } });
    await w.vm.$nextTick();
    expect(boto.attributes("aria-pressed")).toBe("true");
  });
});
