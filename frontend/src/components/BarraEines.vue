<!--
  Barra d'eines del llenç: desfer i refer, afegir elements i les pàgines de la cançó (moure el llenç,
  el zoom i l'ajuda són a la barra de sota, BarraInferior.vue). Els
  botons només tenen icona; el nom (i la drecera) surt en passar-hi el ratolí.
-->
<script setup>
import { GRUPS_EINES, tooltip } from "@/eines.js";
import { useEditorStore } from "@/stores/editor.js";

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
  </div>
</template>
