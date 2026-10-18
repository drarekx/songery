// Punt d'entrada dels components Vue. Cada pàgina (o editor.js) munta els que necessita amb les
// funcions munta…, que comparteixen una sola instància de Pinia.
import { createPinia } from "pinia";
import { createApp, h, reactive } from "vue";
import AvisLlenc from "./components/AvisLlenc.vue";
import BarraEines from "./components/BarraEines.vue";
import BarraText from "./components/BarraText.vue";
import PanellAcords from "./components/PanellAcords.vue";
import PanellCanco from "./components/PanellCanco.vue";
import PanellCapes from "./components/PanellCapes.vue";
import PanellEstils from "./components/PanellEstils.vue";
import PanellLlista from "./components/PanellLlista.vue";
import PanellPropietats from "./components/PanellPropietats.vue";
import SelectorColor from "./components/SelectorColor.vue";
import { TIPUS_ACORD, useEditorStore } from "./stores/editor.js";

export const pinia = createPinia();
export { TIPUS_ACORD, useEditorStore };

function munta(component, desti, props = {}) {
  const app = createApp(component, props);
  app.use(pinia);
  return app.mount(desti);
}

export const muntaPanellAcords = (desti) => munta(PanellAcords, desti);
export const muntaBarraEines = (desti) => munta(BarraEines, desti);
export const muntaBarraText = (desti) => munta(BarraText, desti);
export const muntaAvisLlenc = (desti) => munta(AvisLlenc, desti);
export const muntaPanellCanco = (desti) => munta(PanellCanco, desti);
export const muntaPanellCapes = (desti) => munta(PanellCapes, desti);
export const muntaPanellEstils = (desti) => munta(PanellEstils, desti);
export const muntaPanellLlista = (desti) => munta(PanellLlista, desti);
export const muntaPanellPropietats = (desti) => munta(PanellPropietats, desti);

/**
 * Selector de color sobre un <input> existent: el camp guarda el valor (text) i rep «input» quan
 * canvia, així el codi que ja l'escoltava continua igual. Si el codi canvia el valor o el desactiva,
 * el selector s'actualitza.
 * opcions: buit (text de «sense color»), perDefecte (valor o funció), colors (funció → llista)
 */
export function muntaSelectorColor(input, opcions = {}) {
  input.type = "text";
  input.hidden = true;
  input.dataset.color = "";
  const estat = reactive({ valor: input.value, disabled: input.disabled, perDefecte: undefined });
  const llegeixPerDefecte = () => (typeof opcions.perDefecte === "function" ? opcions.perDefecte() : opcions.perDefecte);
  const proto = HTMLInputElement.prototype;
  for (const [prop, clau] of [["value", "valor"], ["disabled", "disabled"]]) {
    const desc = Object.getOwnPropertyDescriptor(proto, prop);
    Object.defineProperty(input, prop, {
      configurable: true,
      get() { return desc.get.call(this); },
      set(v) {
        desc.set.call(this, v);
        estat[clau] = desc.get.call(this);
        estat.perDefecte = llegeixPerDefecte();
      },
    });
  }
  const lloc = document.createElement("span");
  lloc.className = "contents";
  input.after(lloc);
  const app = createApp({
    render: () => h(SelectorColor, {
      modelValue: estat.valor,
      disabled: estat.disabled,
      buit: opcions.buit ?? null,
      perDefecte: estat.perDefecte ?? llegeixPerDefecte(),
      colors: opcions.colors,
      "onUpdate:modelValue": (valor) => {
        input.value = valor;
        input.dispatchEvent(new Event("input", { bubbles: true }));
      },
    }),
  });
  app.use(pinia);
  app.mount(lloc);
  return { app };
}
