<!--
  Barra de sota del llenç: moure el llenç (la mà), el zoom i l'ajuda («?»). Té el mateix aspecte que la
  barra d'eines de dalt.
-->
<script setup>
import { EINES_LLENC, tooltip } from "@/eines.js";
import { useEditorStore } from "@/stores/editor.js";
import AjudaEditor from "./AjudaEditor.vue";

const store = useEditorStore();
const ma = EINES_LLENC.find((e) => e.nom === "ma");
</script>

<template>
  <div class="flex flex-wrap items-center justify-end gap-x-1 gap-y-1 border-t border-paper-300 bg-paper-50 px-3 py-1.5"
       role="toolbar" aria-label="Vista del llenç">
    <button type="button" class="eina" :data-tooltip="tooltip(ma)" :aria-label="ma.titol" :aria-pressed="String(!!store.eines.ma)"
            @click="store.crida('ma')">
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="ma.icona"></svg>
    </button>
    <div class="zoom" role="group" aria-label="Zoom">
      <button type="button" aria-label="Allunya" title="Allunya (Ctrl/⌘ + roda)" @click="store.crida('zoom', 0.8)">
        <svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3.5 8h9"/></svg></button>
      <span aria-live="polite">{{ Math.round(store.zoom * 100) }} %</span>
      <button type="button" aria-label="Apropa" title="Apropa (Ctrl/⌘ + roda)" @click="store.crida('zoom', 1.25)">
        <svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M8 3.5v9M3.5 8h9"/></svg></button>
      <button type="button" title="Ajusta a la finestra" @click="store.crida('zoom', null)">Ajusta</button>
    </div>
    <span class="separador" aria-hidden="true"></span>
    <AjudaEditor />
  </div>
</template>
