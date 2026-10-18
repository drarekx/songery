// Preferències de l'usuari i la nansa per canviar l'amplada d'una columna.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import RedimensionaPanell from "@/components/RedimensionaPanell.vue";
import { usePreferencies } from "@/stores/preferencies.js";

let pinia;
beforeEach(() => {
  document.body.innerHTML = '<script id="preferencies" type="application/json">{"editor.amplePropietats": 400}</script><main id="editor"></main>';
  pinia = createPinia();
  setActivePinia(pinia);
  vi.useFakeTimers();
  globalThis.fetch = vi.fn(async (url, opcions) => ({ ok: true, json: async () => JSON.parse(opcions.body) }));
});
afterEach(() => vi.useRealTimers());

describe("usePreferencies", () => {
  it("llegeix les inicials de la pàgina i desa els canvis seguits en una sola petició", async () => {
    const p = usePreferencies();
    expect(p.llegeix("editor.amplePropietats")).toBe(400);
    expect(p.llegeix("res", 7)).toBe(7);
    p.posa("editor.amplePropietats", 410);
    p.posa("editor.amplePropietats", 420);
    expect(fetch).not.toHaveBeenCalled();
    await vi.runAllTimersAsync();
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ "editor.amplePropietats": 420 });
    expect(fetch.mock.calls[0][1].method).toBe("PATCH");
  });
});

describe("RedimensionaPanell", () => {
  const munta = (extra = {}) => mount(RedimensionaPanell, {
    props: { objectiu: "#editor", variable: "--ample", clau: "editor.amplePropietats", minim: 260, maxim: 720, perDefecte: 320, ...extra },
    global: { plugins: [pinia] }, attachTo: document.body,
  });
  const ample = () => document.getElementById("editor").style.getPropertyValue("--ample");

  it("arrossegant cap a l'esquerra la fa més ampla, amb límits, i ho desa en acabar", async () => {
    const acaba = vi.fn();
    const w = munta({ alAcabar: acaba });
    const nansa = w.find(".nansa-columna");
    await nansa.trigger("pointerdown", { button: 0, clientX: 1000 });
    expect(document.body.classList.contains("redimensionant")).toBe(true);
    await nansa.trigger("pointermove", { clientX: 900 });
    expect(ample()).toBe("500px");
    await nansa.trigger("pointermove", { clientX: 100 });
    expect(ample()).toBe("720px"); // màxim
    await nansa.trigger("pointerup", { clientX: 100 });
    expect(document.body.classList.contains("redimensionant")).toBe(false);
    expect(acaba).toHaveBeenCalled();
    expect(usePreferencies().llegeix("editor.amplePropietats")).toBe(720);
    w.unmount();
  });

  it("amb el teclat i doble clic per tornar a l'amplada per defecte", async () => {
    const w = munta();
    const nansa = w.find(".nansa-columna");
    await nansa.trigger("keydown", { key: "ArrowRight" });
    expect(ample()).toBe("384px");
    await nansa.trigger("dblclick");
    expect(ample()).toBe("320px");
    expect(usePreferencies().valors["editor.amplePropietats"]).toBeNull();
    w.unmount();
  });
});
