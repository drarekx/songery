<!--
  Pestanya «Estils»: els estils de text del cançoner (Títol, Lletra, Acord…). Canviar-ne un actualitza
  totes les pàgines. La tipografia es tria amb el selector de tipografies de l'editor.
-->
<script setup>
import { FONTS, colorCss } from "@/pagines.js";
import { useEditorStore } from "@/stores/editor.js";
import SelectorColor from "./SelectorColor.vue";

const store = useEditorStore();
const GRUIXOS = [300, 400, 500, 600, 700, 800];

const nomFont = (clau) => store.tipografies.find((f) => f.clau === clau)?.nom || clau;
const mostra = (e) => ({
  fontFamily: FONTS[e.font] || "", fontWeight: e.pes, fontStyle: e.cursiva ? "italic" : "normal",
  color: colorCss(e.color), fontSize: "18px",
});

function numero(clau, prop, valor) {
  if (valor === "") return;
  store.canviaEstil(clau, prop, Number(valor));
}
</script>

<template>
  <div class="flex flex-col">
    <p class="px-4 pt-4 text-[13px] leading-snug text-ink-500">Els estils s'apliquen a tot el cançoner. Canvia'n un i s'actualitzen totes les pàgines.</p>
    <ul class="flex flex-col gap-2 p-4">
      <li v-for="(e, clau) in store.estils" :key="clau" class="rounded-md border border-paper-300 bg-white">
        <details class="group">
          <summary class="flex items-center gap-3 px-3 py-2">
            <span class="w-8 shrink-0 text-center" :style="mostra(e)" aria-hidden="true">Aa</span>
            <span class="flex-1 text-[14px] font-medium">{{ e.nom }}</span>
            <span class="font-mono text-[11px] text-ink-400">{{ e.mida }} pt</span>
          </summary>
          <div class="grid grid-cols-2 gap-3 border-t border-paper-200 p-3">
            <div class="col-span-2">
              <span class="etiqueta">Tipografia</span>
              <button type="button" class="selector-font" @click="store.crida('triaFont', $event.currentTarget, clau)">
                <span class="nom-font" :style="{ fontFamily: FONTS[e.font] || '' }">{{ nomFont(e.font) }}</span>
              </button>
            </div>
            <label><span class="etiqueta">Mida (pt)</span>
              <input type="number" step="0.5" class="camp py-1 font-mono text-[13px]" :value="e.mida" @input="numero(clau, 'mida', $event.target.value)"></label>
            <label><span class="etiqueta">Gruix</span>
              <select class="camp py-1 text-[13px]" :value="e.pes" @change="numero(clau, 'pes', $event.target.value)">
                <option v-for="g in GRUIXOS" :key="g" :value="g">{{ g }}</option>
              </select></label>
            <label><span class="etiqueta">Interlineat</span>
              <input type="number" step="0.05" class="camp py-1 font-mono text-[13px]" :value="e.interlineat" @input="numero(clau, 'interlineat', $event.target.value)"></label>
            <label><span class="etiqueta">Espaiat</span>
              <input type="number" step="0.01" class="camp py-1 font-mono text-[13px]" :value="e.espaiat" @input="numero(clau, 'espaiat', $event.target.value)"></label>
            <div><span class="etiqueta">Color</span>
              <SelectorColor :model-value="e.color" :colors="() => store.crida('colorsDelDocument')"
                             @update:model-value="store.canviaEstil(clau, 'color', $event)" /></div>
            <div class="flex flex-col justify-end gap-1.5 pb-1">
              <label class="flex items-center gap-2 text-[13px]"><input type="checkbox" class="h-4 w-4 accent-accent-500" :checked="e.cursiva"
                     @change="store.canviaEstil(clau, 'cursiva', $event.target.checked)"> Cursiva</label>
              <label class="flex items-center gap-2 text-[13px]"><input type="checkbox" class="h-4 w-4 accent-accent-500" :checked="e.majuscules"
                     @change="store.canviaEstil(clau, 'majuscules', $event.target.checked)"> Majúscules</label>
            </div>
          </div>
        </details>
      </li>
    </ul>
  </div>
</template>
