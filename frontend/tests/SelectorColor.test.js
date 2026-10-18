import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import SelectorColor from "@/components/SelectorColor.vue";

const muntats = [];
afterEach(() => muntats.splice(0).forEach((w) => w.unmount()));

const munta = (props = {}) => {
  const w = mount(SelectorColor, { props, attachTo: document.body });
  muntats.push(w);
  return w;
};

describe("SelectorColor", () => {
  it("mostra el valor o el de l'estil", () => {
    expect(munta({ modelValue: "cmyk(0,100,100,0)" }).text()).toContain("C0 M100 Y100 K0");
    expect(munta({ modelValue: "", perDefecte: "cmyk(0,0,0,100)" }).text()).toContain("(estil)");
    expect(munta({ modelValue: "", buit: "Sense fons" }).text()).toContain("Sense fons");
  });

  it("canviar un canal dona el CMYK exacte", async () => {
    const w = munta({ modelValue: "cmyk(0,0,0,100)" });
    await w.find("button").trigger("click");
    const magenta = document.querySelectorAll(".popover-color input[type=number]")[1];
    magenta.value = "40";
    magenta.dispatchEvent(new Event("input"));
    expect(w.emitted("update:modelValue").at(-1)).toEqual(["cmyk(0,40,0,100)"]);
  });

  it("es pot triar una tinta de la paleta o deixar-lo buit", async () => {
    const w = munta({ modelValue: "#ff0000", buit: "Sense vora" });
    await w.find("button").trigger("click");
    document.querySelector('.popover-color [aria-label="Groc"]').click();
    expect(w.emitted("update:modelValue").at(-1)).toEqual(["cmyk(0,0,100,0)"]);
    [...document.querySelectorAll(".popover-color button")].find((b) => b.textContent === "Sense vora").click();
    expect(w.emitted("update:modelValue").at(-1)).toEqual([""]);
  });

  it("es tanca amb Escape", async () => {
    const w = munta({ modelValue: "#000000" });
    await w.find("button").trigger("click");
    expect(document.querySelector(".popover-color")).not.toBeNull();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
    await w.vm.$nextTick();
    expect(document.querySelector(".popover-color")).toBeNull();
  });
});
