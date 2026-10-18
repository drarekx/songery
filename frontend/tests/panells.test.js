// Panells de l'editor que llegeixen l'estat de Pinia: acords i vídeos.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PanellAcords from "@/components/PanellAcords.vue";
import PanellVideos from "@/components/PanellVideos.vue";
import { TIPUS_ACORD, useEditorStore } from "@/stores/editor.js";

vi.mock("@/dialegs.js", () => ({ confirma: vi.fn(async () => true) }));

let pinia;
let store;
beforeEach(() => {
  pinia = createPinia();
  setActivePinia(pinia);
  store = useEditorStore();
});
const munta = (component) => mount(component, { global: { plugins: [pinia] } });

describe("PanellAcords", () => {
  it("sense cançó oberta, ho diu", () => {
    expect(munta(PanellAcords).text()).toContain("Obre una cançó");
  });

  it("mostra els acords i en clicar-los els afegeix", async () => {
    const afegeix = vi.fn();
    store.connecta({ afegeixDiagrama: afegeix });
    store.sincronitza({ canco: { id: "c1", titol: "Prova" }, acords: ["G", "D"], diagrames: { G: "<svg class='g'></svg>" } });
    const w = munta(PanellAcords);
    expect(w.text()).toContain("G · D");
    expect(w.find("svg.g").exists()).toBe(true);
    const botons = w.findAll("button");
    expect(botons).toHaveLength(3); // tots + G + D
    await botons[2].trigger("click");
    await botons[0].trigger("click");
    expect(afegeix.mock.calls).toEqual([["D"], ["*"]]);
  });

  it("en arrossegar-lo, porta el nom de l'acord", async () => {
    store.sincronitza({ canco: { id: "c1" }, acords: ["Em"] });
    const w = munta(PanellAcords);
    const dades = {};
    await w.findAll("button")[1].trigger("dragstart", { dataTransfer: { setData: (t, v) => (dades[t] = v) } });
    expect(dades[TIPUS_ACORD]).toBe("Em");
  });

  it("en una versió fixada no es pot afegir", () => {
    store.sincronitza({ canco: { id: "c1" }, acords: ["G"], editable: false });
    expect(munta(PanellAcords).findAll("button").every((b) => b.element.disabled)).toBe(true);
  });
});

describe("PanellVideos", () => {
  const video = (id, titol) => ({ id, video: "dQw4w9WgXcQ", inici: 0, titol, canal: "", inclou_qr: true });

  it("reordena, canvia i treu vídeos", async () => {
    const canvia = vi.fn();
    store.connecta({ canviaVideos: canvia });
    store.sincronitza({ videos: [video("a", "Primer"), video("b", "Segon")] });
    const w = munta(PanellVideos);
    await w.find('[title="Baixa"]').trigger("click");
    expect(canvia.mock.lastCall[0].map((v) => v.id)).toEqual(["b", "a"]);
    await w.findAll('input[type="checkbox"]')[0].setValue(false);
    expect(canvia.mock.lastCall[0][0].inclou_qr).toBe(false);
    await w.findAll('[title="Treu el vídeo"]')[0].trigger("click");
    await vi.waitFor(() => expect(canvia.mock.lastCall[0]).toHaveLength(1));
  });

  it("afegeix un vídeo amb el títol del servidor i mostra els errors", async () => {
    store.sincronitza({ urls: { video: "/api/video" } });
    globalThis.fetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ video: video("n", "Nou") }) })
      .mockResolvedValueOnce({ ok: false, json: async () => ({ error: "Aquesta adreça no és d'un vídeo de YouTube" }) });
    const w = munta(PanellVideos);
    await w.find("input").setValue("https://youtu.be/dQw4w9WgXcQ");
    await w.find("form").trigger("submit");
    await vi.waitFor(() => expect(store.videos).toHaveLength(1));
    await w.find("input").setValue("https://vimeo.com/1");
    await w.find("form").trigger("submit");
    await vi.waitFor(() => expect(w.find('[role="alert"]').text()).toContain("YouTube"));
  });

  it("en una versió fixada només es poden mirar", () => {
    store.sincronitza({ editable: false, videos: [video("a", "Primer")] });
    const w = munta(PanellVideos);
    expect(w.find("form").exists()).toBe(false);
    expect(w.find('[title="Treu el vídeo"]').exists()).toBe(false);
  });
});
