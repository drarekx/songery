<!--
  Pestanya «Cançó» de l'editor: títol i autor, transport, si surt al PDF i on comença (en aquest
  cançoner), vídeos, historial i treure-la del cançoner.
-->
<script setup>
import { computed } from "vue";
import { useEditorStore } from "@/stores/editor.js";
import PanellVideos from "./PanellVideos.vue";

const store = useEditorStore();
const transportText = computed(() => (store.transport > 0 ? `+${store.transport}` : String(store.transport)));
const etiquetaVersio = computed(() => {
  const e = store.entrada;
  if (!e) return "";
  if (e.versio_id) return `v${e.versio_numero} fixada`;
  return e.versio_ultima ? `${e.versio_ultima} versions` : "";
});
</script>

<template>
  <p v-if="!store.entrada || !store.canco" class="text-[13px] text-ink-500">Selecciona una cançó o una pàgina lliure a la llista.</p>
  <div v-else class="flex flex-col gap-4">
    <label><span class="etiqueta">Títol</span>
      <input id="titol-ev" class="camp font-display text-lg" :value="store.canco.titol" :readonly="!store.editable"
             @input="store.canviaDadesCanco('titol', $event.target.value)"></label>
    <label><span class="etiqueta">Autor</span>
      <input class="camp" :value="store.canco.autor" :readonly="!store.editable"
             @input="store.canviaDadesCanco('autor', $event.target.value)"></label>

    <div class="flex items-center justify-between gap-2">
      <span class="text-[13px] font-semibold text-ink-700" title="S'aplica en aquest cançoner, sense canviar la cançó">Transport</span>
      <div class="inline-flex items-stretch rounded-md border border-paper-300 bg-white shadow-suau">
        <button type="button" class="w-8 rounded-l-md text-lg leading-none text-ink-500 hover:bg-paper-100" aria-label="Baixa un semitò" @click="store.mouTransport(-1)">−</button>
        <output class="flex w-10 items-center justify-center border-x border-paper-300 font-mono text-[13px] font-semibold tabular-nums">{{ transportText }}</output>
        <button type="button" class="w-8 rounded-r-md text-lg leading-none text-ink-500 hover:bg-paper-100" aria-label="Puja un semitò" @click="store.mouTransport(1)">+</button>
      </div>
    </div>
    <button type="button" class="btn btn-petit" :disabled="!store.transport || !store.editable" @click="store.crida('aplicaTransport')">Aplica el transport a la cançó</button>

    <label class="flex items-center justify-between gap-3 text-[14px]">Surt al PDF
      <span class="interruptor"><input class="peer sr-only" type="checkbox" :checked="store.entrada.inclosa"
             @change="store.canviaEntrada({ inclosa: $event.target.checked })"><span></span></span></label>
    <label class="flex items-center justify-between gap-3 text-[14px]">Comença sempre a l'esquerra
      <span class="interruptor"><input class="peer sr-only" type="checkbox" :checked="store.entrada.inici !== 'qualsevol'"
             @change="store.canviaEntrada({ inici: $event.target.checked ? 'esquerra' : 'qualsevol' })"><span></span></span></label>
    <p class="-mt-2 text-[12px] leading-snug text-ink-500">Desactiva-ho per posar-la just després de l'anterior (per exemple, dues cançons curtes a la mateixa doble pàgina).</p>

    <PanellVideos class="border-t border-paper-300 pt-4" />

    <button type="button" class="btn btn-petit" @click="store.crida('obreHistorial')">
      <svg class="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M2.5 8a5.5 5.5 0 1 0 1.6-3.9M2.5 2.5v2.5H5M8 5v3l2 1.5"/></svg>
      Versions i historial <span class="font-mono text-[11px] text-ink-400">{{ etiquetaVersio }}</span>
    </button>
    <button type="button" class="btn btn-perill btn-petit" @click="store.crida('treuCanco')">Treu del cançoner</button>
  </div>
</template>
