<!--
  Barra d'eines del llenç: desfer i refer, afegir elements, les pàgines de la cançó i el zoom. Els
  botons només tenen icona; el nom (i la drecera) surt en passar-hi el ratolí.
-->
<script setup>
import { GRUPS_EINES, tooltip } from "@/eines.js";
import { useEditorStore } from "@/stores/editor.js";
import AjudaEditor from "./AjudaEditor.vue";

const store = useEditorStore();

const GRUPS = GRUPS_EINES;
</script>

<template>
  <div class="flex flex-wrap items-center gap-x-1 gap-y-1 border-b border-paper-300 bg-paper-50 px-3 py-1.5" :class="{ 'eines-inactives': store.eines.inactives }"
       role="toolbar" aria-label="Eines">
    <template v-for="(grup, g) in GRUPS" :key="g">
      <span v-if="g" class="separador" aria-hidden="true"></span>
      <span v-if="grup.etiqueta" class="hidden px-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400 xl:inline">{{ grup.etiqueta }}</span>
      <!-- mousedown.prevent: no es treu el focus del text que s'està editant -->
      <button v-for="eina in grup.eines" :key="eina.nom" type="button" class="eina" :data-eina="eina.nom"
              :data-tooltip="tooltip(eina)" :aria-label="tooltip(eina)" :disabled="grup.pagina && !store.eines.pagina"
              :aria-pressed="eina.premut ? String(store.eines.acordsObert) : undefined"
              @mousedown.prevent @click="store.crida('eina', eina.nom)">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="eina.icona"></svg>
      </button>
    </template>
    <div class="ml-auto flex items-center gap-1">
    <button type="button" class="eina" data-tooltip="Mou el llenç (o mantén premut l'espai, o arrossega amb el botó del mig)"
            aria-label="Mou el llenç" :aria-pressed="String(!!store.eines.ma)" @click="store.crida('ma')">
      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M7 10V4.5a1.2 1.2 0 0 1 2.4 0V9m0-4.5V3.3a1.2 1.2 0 0 1 2.4 0V9m0-4.2a1.2 1.2 0 0 1 2.4 0V10m0-3a1.2 1.2 0 0 1 2.4 0v4.5c0 3.4-2.4 6-5.6 6-2.2 0-3.6-1-4.7-2.7L4.3 12a1.2 1.2 0 0 1 2-1.3L7 11.6"/>
      </svg>
    </button>
    <div class="zoom" role="group" aria-label="Zoom">
      <button type="button" aria-label="Allunya" title="Allunya (Ctrl/⌘ + roda)" @click="store.crida('zoom', 0.8)">
        <svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3.5 8h9"/></svg></button>
      <span aria-live="polite">{{ Math.round(store.zoom * 100) }} %</span>
      <button type="button" aria-label="Apropa" title="Apropa (Ctrl/⌘ + roda)" @click="store.crida('zoom', 1.25)">
        <svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M8 3.5v9M3.5 8h9"/></svg></button>
      <button type="button" title="Ajusta a la finestra" @click="store.crida('zoom', null)">Ajusta</button>
    </div>
    <AjudaEditor />
    </div>
  </div>
</template>
