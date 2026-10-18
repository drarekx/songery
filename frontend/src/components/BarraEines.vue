<!--
  Barra d'eines del llenç: desfer i refer, afegir elements, les pàgines de la cançó i el zoom. Els
  botons només tenen icona; el nom (i la drecera) surt en passar-hi el ratolí.
-->
<script setup>
import { useEditorStore } from "@/stores/editor.js";

const store = useEditorStore();

const GRUPS = [
  { eines: [
    { nom: "desfes", titol: "Desfés (⌘Z)", icona: '<path d="M7 5 3 9l4 4M3 9h9a4 4 0 0 1 0 8h-1"/>' },
    { nom: "refes", titol: "Refés (⇧⌘Z)", icona: '<path d="m13 5 4 4-4 4M17 9H8a4 4 0 0 0 0 8h1"/>' },
  ] },
  { etiqueta: "Afegeix", eines: [
    { nom: "nou-lletra", titol: "Marc de lletra amb acords", icona: '<rect x="3" y="3" width="14" height="14" rx="1"/><path d="M6 8h8M6 11h8M6 14h5"/><path d="M6 5.5h1.5" stroke="#c4321f" stroke-width="2"/>' },
    { nom: "nou-text", titol: "Text", icona: '<path d="M4 5h12M10 5v11M8 16h4"/>' },
    { nom: "nou-imatge", titol: "Imatge", icona: '<rect x="3" y="4" width="14" height="12" rx="1.5"/><circle cx="7.5" cy="8.5" r="1.5"/><path d="m3 14 4-4 3 3 2-2 5 5"/>' },
    { nom: "nou-forma", titol: "Rectangle", icona: '<rect x="3.5" y="5" width="13" height="10" rx="1"/>' },
    { nom: "nou-elipse", titol: "El·lipse", icona: '<ellipse cx="10" cy="10" rx="7" ry="5.5"/>' },
    { nom: "nou-numero", titol: "Número de pàgina", icona: '<path d="M6 4 4.5 16M11.5 4 10 16M3.5 8h11M3 12h11"/>' },
    { nom: "acords", titol: "Diagrames d'acords: arrossega'ls a la pàgina", premut: true, icona: '<rect x="4" y="3" width="12" height="14" rx="1"/><path d="M7 3v14M10 3v14M13 3v14M4 7h12M4 11h12"/><circle cx="10" cy="9" r="1.3" fill="currentColor"/><circle cx="13" cy="13" r="1.3" fill="currentColor"/>' },
    { nom: "nou-qr", titol: "Codi QR d'un vídeo de la cançó", icona: '<path d="M3 3h5v5H3zM12 3h5v5h-5zM3 12h5v5H3z"/><path d="M12 12h2v2h-2zM15 15h2v2h-2zM12 16h1M16 12h1" stroke-width="1.8"/>' },
    { nom: "importa-text", titol: "Importa text amb acords (de webs de tabs) al marc de lletra", icona: '<path d="M7 4H5v13h10V4h-2M7 3h6v3H7z"/><path d="M8 10h4M8 13h4"/>' },
  ] },
  { etiqueta: "Pàgina", pagina: true, eines: [
    { nom: "pagina-nova", titol: "Afegeix una pàgina a la cançó", icona: '<path d="M5 3h7l3 3v11H5z"/><path d="M10 9v5M7.5 11.5h5"/>' },
    { nom: "pagina-duplica", titol: "Duplica la pàgina", icona: '<rect x="6" y="6" width="10" height="11" rx="1"/><path d="M4 13V3h8"/>' },
    { nom: "pagina-esquerra", titol: "Mou la pàgina enrere", icona: '<path d="m12 5-5 5 5 5"/>' },
    { nom: "pagina-dreta", titol: "Mou la pàgina endavant", icona: '<path d="m8 5 5 5-5 5"/>' },
    { nom: "pagina-esborra", titol: "Esborra la pàgina", icona: '<path d="M4 6h12M8 6V4h4v2M6 6l.8 11h6.4L14 6"/>' },
  ] },
];
</script>

<template>
  <div class="flex flex-wrap items-center gap-x-1 gap-y-1 border-b border-paper-300 bg-paper-50 px-3 py-1.5" :class="{ 'eines-inactives': store.eines.inactives }"
       role="toolbar" aria-label="Eines">
    <template v-for="(grup, g) in GRUPS" :key="g">
      <span v-if="g" class="separador" aria-hidden="true"></span>
      <span v-if="grup.etiqueta" class="hidden px-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400 xl:inline">{{ grup.etiqueta }}</span>
      <!-- mousedown.prevent: no es treu el focus del text que s'està editant -->
      <button v-for="eina in grup.eines" :key="eina.nom" type="button" class="eina" :data-eina="eina.nom"
              :data-tooltip="eina.titol" :aria-label="eina.titol" :disabled="grup.pagina && !store.eines.pagina"
              :aria-pressed="eina.premut ? String(store.eines.acordsObert) : undefined"
              @mousedown.prevent @click="store.crida('eina', eina.nom)">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="eina.icona"></svg>
      </button>
    </template>
    <div class="zoom ml-auto" role="group" aria-label="Zoom">
      <button type="button" aria-label="Allunya" title="Allunya (Ctrl/⌘ + roda)" @click="store.crida('zoom', 0.8)">
        <svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3.5 8h9"/></svg></button>
      <span aria-live="polite">{{ Math.round(store.zoom * 100) }} %</span>
      <button type="button" aria-label="Apropa" title="Apropa (Ctrl/⌘ + roda)" @click="store.crida('zoom', 1.25)">
        <svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M8 3.5v9M3.5 8h9"/></svg></button>
      <button type="button" title="Ajusta a la finestra" @click="store.crida('zoom', null)">Ajusta</button>
    </div>
  </div>
</template>
