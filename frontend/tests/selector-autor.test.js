// Selector d'autor (combobox): cerca, teclat, crear un autor nou i esborrar-lo.
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SelectorAutor from "@/components/SelectorAutor.vue";

const AUTORS = [{ id: "a1", nom: "Àngel Guimerà", cancons: 2 }, { id: "a2", nom: "Joan Alcover", cancons: 1 }];
beforeEach(() => {
  vi.useFakeTimers();
  globalThis.fetch = vi.fn(async (url) => {
    const q = decodeURIComponent(url.split("q=")[1] || "").normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
    return { ok: true, json: async () => AUTORS.filter((a) => a.nom.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().includes(q)) };
  });
});
afterEach(() => vi.useRealTimers());

const munta = (valor = "") => mount(SelectorAutor, { props: { modelValue: valor, id: "autor" }, attachTo: document.body });
const escriu = async (w, text) => {
  await w.find("input").setValue(text);
  await vi.runAllTimersAsync();
};

describe("SelectorAutor", () => {
  it("cerca sense accents, tria amb el teclat i emet el nom", async () => {
    const w = munta();
    await escriu(w, "guimera");
    const opcions = w.findAll('[role="option"]');
    expect(opcions.map((o) => o.text())).toEqual(["Àngel Guimerà2", "Crea «guimera»"]);
    expect(w.find("input").attributes("aria-expanded")).toBe("true");
    await w.find("input").trigger("keydown", { key: "ArrowDown" });
    expect(w.find("input").attributes("aria-activedescendant")).toBe("autor-opcio-0");
    await w.find("input").trigger("keydown", { key: "Enter" });
    expect(w.emitted("update:modelValue").at(-1)).toEqual(["Àngel Guimerà"]);
    w.unmount();
  });

  it("si no existeix, el crea; la creu el deixa sense autor; Esc torna al valor d'abans", async () => {
    const w = munta("Joan Alcover");
    await escriu(w, "Enric Morera");
    expect(w.findAll('[role="option"]').at(-1).text()).toBe("Crea «Enric Morera»");
    await w.findAll('[role="option"]').at(-1).trigger("click");
    expect(w.emitted("update:modelValue").at(-1)).toEqual(["Enric Morera"]);
    await w.setProps({ modelValue: "Enric Morera" });
    await w.find('[aria-label="Treu l\'autor"]').trigger("click");
    expect(w.emitted("update:modelValue").at(-1)).toEqual([""]);
    await w.setProps({ modelValue: "Joan Alcover" });
    await escriu(w, "quelcom");
    await w.find("input").trigger("keydown", { key: "Escape" });
    expect(w.find("input").element.value).toBe("Joan Alcover");
    w.unmount();
  });
});
