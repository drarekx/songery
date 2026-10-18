<!-- Botons d'acció sobre la selecció: bloquejar, davant, darrere, duplicar i esborrar. -->
<script setup>
import { useEditorStore } from "@/stores/editor.js";

defineProps({ bloquejat: { type: Boolean, default: false } });
const store = useEditorStore();

const ACCIONS = [
  { nom: "davant", titol: "Porta al davant", cami: "M3 11V3h8", requadre: "M5 5h8v8H5z" },
  { nom: "darrere", titol: "Envia al fons", cami: "M3 3h8v8H3z", ratlla: "M5 13h8V5" },
  { nom: "duplica", titol: "Duplica (⌘D)", cami: "M3 10V3h7", rect: true },
];
</script>

<template>
  <div class="flex gap-0.5">
    <button type="button" class="btn btn-fantasma btn-icona" :aria-pressed="String(bloquejat)" :disabled="!store.editable"
            title="Bloqueja: no es podrà seleccionar clicant al llenç (es desbloqueja a Capes)" aria-label="Bloqueja"
            @click="store.crida('accio', 'bloqueja')">
      <svg class="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M5 7V5a3 3 0 0 1 6 0v2M4 7h8v6.5H4z"/></svg>
    </button>
    <button v-for="a in ACCIONS" :key="a.nom" type="button" class="btn btn-fantasma btn-icona" :title="a.titol" :aria-label="a.titol"
            :disabled="!store.editable" @click="store.crida('accio', a.nom)">
      <svg class="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
        <path v-if="a.requadre" :d="a.requadre" fill="currentColor" fill-opacity=".15"/>
        <rect v-if="a.rect" x="5" y="5" width="8" height="8" rx="1"/>
        <path :d="a.cami"/>
        <path v-if="a.ratlla" :d="a.ratlla" stroke-dasharray="2 1.5"/>
      </svg>
    </button>
    <button type="button" class="btn btn-perill btn-icona" title="Esborra (Supr)" aria-label="Esborra" :disabled="!store.editable"
            @click="store.crida('accio', 'esborra')">
      <svg class="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M3 4.5h10M6.5 4.5V3h3v1.5M4.5 4.5l.7 8.5h5.6l.7-8.5"/></svg>
    </button>
  </div>
</template>
