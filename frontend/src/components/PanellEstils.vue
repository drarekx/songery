<!--
  Pestanya «Estils»: els estils de text del cançoner (Títol, Lletra, Acord… i els propis que s'hi creïn).
  Canviar-ne un actualitza totes les pàgines. La tipografia es tria amb el selector de tipografies de
  l'editor. Els estils propis es poden reanomenar i esborrar; els predefinits, no.
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

const propi = (clau) => String(clau).startsWith("propi_");

function numero(clau, prop, valor) {
  if (valor === "") return;
  store.canviaEstil(clau, prop, Number(valor));
}
</script>

<template>
  <div class="flex flex-col">
    <div class="flex items-start gap-3 px-4 pt-4">
      <p v-if="store.modeCanco" class="flex-1 text-[13px] leading-snug text-ink-500">Fora d'un cançoner, els estils són
        {{ store.dissenyDe ? `els del cançoner «${store.dissenyDe}»` : "els de per defecte" }} i aquí no es poden canviar.</p>
      <p v-else class="flex-1 text-[13px] leading-snug text-ink-500">Els estils s'apliquen a tot el cançoner. Canvia'n un i s'actualitzen totes les pàgines.</p>
      <button v-if="!store.modeCanco" type="button" class="btn btn-petit shrink-0" @click="store.crida('creaEstil', 'text')">+ Estil nou</button>
    </div>
    <ul class="flex flex-col gap-2 p-4">
      <li v-for="(e, clau) in store.estils" :key="clau" class="rounded-md border border-paper-300 bg-white">
        <details class="group">
          <summary class="flex items-center gap-3 px-3 py-2">
            <span class="w-8 shrink-0 text-center" :style="mostra(e)" aria-hidden="true">Aa</span>
            <span class="flex-1 text-[14px] font-medium">{{ e.nom }}</span>
            <span v-if="propi(clau)" class="rounded bg-paper-200 px-1.5 text-[10.5px] font-medium text-ink-500">propi</span>
            <span class="font-mono text-[11px] text-ink-400">{{ e.mida }} pt</span>
          </summary>
          <fieldset class="grid grid-cols-2 gap-3 border-t border-paper-200 p-3" :disabled="store.modeCanco">
            <label v-if="propi(clau)" class="col-span-2"><span class="etiqueta">Nom</span>
              <input class="camp py-1 text-[13px]" :value="e.nom" maxlength="60" @change="store.crida('reanomenaEstil', clau, $event.target.value)"></label>
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
            <div class="col-span-2 -mb-1 flex flex-wrap gap-1 border-t border-paper-200 pt-2">
              <button type="button" class="btn btn-fantasma btn-petit" @click="store.crida('creaEstil', clau)">Duplica</button>
              <button v-if="propi(clau)" type="button" class="btn btn-perill btn-petit" @click="store.crida('esborraEstil', clau)">Esborra…</button>
            </div>
          </fieldset>
        </details>
      </li>
    </ul>
  </div>
</template>
