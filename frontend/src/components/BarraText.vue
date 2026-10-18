<!--
  Barra de format mentre s'edita un marc de lletra: acord, marques (tònica, negreta, cursiva, cor),
  secció i nota, imatge, importar text, tallar, i la mida de la lletra de tot el marc.
  Els botons no prenen el focus (mousedown.prevent) perquè el cursor es quedi on és a la lletra.
-->
<script setup>
import { useEditorStore } from "@/stores/editor.js";

const store = useEditorStore();

const GRUPS = [
  [
    { nom: "tonica", titol: "Síl·laba tònica (⌘U)", icona: '<path d="M6 4v6a4 4 0 0 0 8 0V4M4 17h12" stroke-width="1.8"/>', marca: true },
    { nom: "bold", titol: "Negreta (⌘B)", icona: '<path d="M6 4h5a3 3 0 0 1 0 6H6zm0 6h6a3 3 0 0 1 0 6H6z" stroke-width="1.9"/>', marca: true },
    { nom: "italic", titol: "Cursiva (⌘I)", icona: '<path d="M12 4H8m4 12H8m3-12-2 12"/>', marca: true },
    { nom: "cor", titol: "Veus del cor (⇧⌘K)", icona: '<circle cx="7" cy="7" r="2.5"/><circle cx="13" cy="7" r="2.5"/><path d="M3 16a4 4 0 0 1 8 0m-2 0a4 4 0 0 1 8 0"/>', marca: true },
  ],
  [
    { nom: "seccio", titol: "Secció: Intro, Chorus… (⌥⌘1)", icona: '<path d="M4 5h12M4 10h7M4 15h9"/><path d="M14 10h3" stroke-width="2.4"/>', marca: true },
    { nom: "nota", titol: "Nota: x2, només veus… (⌥⌘2)", icona: '<path d="M5 3h7l3 3v11H5z"/><path d="M8 9h4M8 12h4"/>', marca: true },
    { nom: "imatge", titol: "Imatge dins la lletra (amb el text al voltant)", icona: '<rect x="3" y="4" width="14" height="12" rx="1.5"/><circle cx="7.5" cy="8.5" r="1.5"/><path d="m3 14 4-4 3 3 2-2 5 5"/>' },
    { nom: "enganxa", titol: "Importa text amb acords (de webs de tabs)", icona: '<path d="M7 4H5v13h10V4h-2M7 3h6v3H7z"/><path d="M8 10h4M8 13h4"/>' },
  ],
  [
    { nom: "talla", titol: "Talla aquí: passa la lletra que hi ha després del cursor a la pàgina següent", icona: '<circle cx="5" cy="6" r="2.2"/><circle cx="5" cy="14" r="2.2"/><path d="m7 7 10 7M7 13l10-7"/>' },
    { nom: "reparteix", titol: "Reparteix: passa a la pàgina següent la lletra que no hi cap, tallant per una estrofa", icona: '<rect x="2.5" y="3" width="6.5" height="14" rx="1"/><rect x="11" y="3" width="6.5" height="14" rx="1"/><path d="M4.5 7h2.5M4.5 10h2.5M13 7h2.5M13 10h1.5"/><path d="M7.5 14h5m-1.5-1.5 1.5 1.5-1.5 1.5" stroke-width="1.4"/>' },
  ],
];

const format = (nom) => store.crida("format", nom);
</script>

<template>
  <div v-if="store.edicio" class="flex flex-wrap items-center gap-x-1 gap-y-1 border-b border-vermello-200 bg-vermello-50 px-3 py-1.5" role="toolbar" aria-label="Format de la lletra">
    <span class="px-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-vermello-700">Lletra</span>
    <button type="button" class="eina" data-tooltip="Acord sobre la paraula seleccionada o al cursor (⌘K, o escriu [G])" aria-label="Afegeix un acord"
            @mousedown.prevent @click="format('acord')">
      <span class="font-mono text-[13px] font-bold text-vermello-600">G</span>
    </button>
    <template v-for="(grup, g) in GRUPS" :key="g">
      <span v-if="g" class="separador" aria-hidden="true"></span>
      <button v-for="eina in grup" :key="eina.nom" type="button" class="eina" :data-tooltip="eina.titol" :aria-label="eina.titol"
              :aria-pressed="eina.marca ? String(!!store.edicio.actius?.[eina.nom]) : undefined"
              @mousedown.prevent @click="format(eina.nom)">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="eina.icona"></svg>
      </button>
    </template>
    <span class="separador" aria-hidden="true"></span>
    <div class="flex items-center gap-1.5" title="Mida de la lletra de tota la cançó (a totes les pàgines)">
      <span class="text-[12px] font-medium text-vermello-700">Mida</span>
      <div class="inline-flex items-stretch rounded-md border border-paper-300 bg-white shadow-suau">
        <button type="button" class="w-7 rounded-l-md text-[15px] leading-none text-ink-500 hover:bg-paper-100" aria-label="Lletra més petita"
                @mousedown.prevent @click="store.crida('midaMarc', store.edicio.mida - 0.5)">−</button>
        <input type="number" step="0.5" min="5" max="40" class="w-14 border-x border-paper-300 bg-transparent text-center font-mono text-[12px] font-semibold tabular-nums outline-none"
               aria-label="Mida de la lletra (pt)" :value="store.edicio.mida" @change="store.crida('midaMarc', Number($event.target.value))">
        <button type="button" class="w-7 rounded-r-md text-[15px] leading-none text-ink-500 hover:bg-paper-100" aria-label="Lletra més gran"
                @mousedown.prevent @click="store.crida('midaMarc', store.edicio.mida + 0.5)">+</button>
      </div>
      <span class="text-[11px] text-ink-500">pt</span>
      <label class="ml-1 flex items-center gap-1.5 text-[12px] text-ink-700" title="Si no hi cap, la lletra es fa més petita automàticament">
        <input type="checkbox" class="h-3.5 w-3.5 accent-vermello-500" :checked="store.edicio.ajusta" @change="store.crida('ajustaMarc', $event.target.checked)"> Ajusta</label>
      <span class="text-[11px]" :class="store.edicio.efectiva?.alerta ? 'text-vermello-600' : 'text-ink-500'">{{ store.edicio.efectiva?.text }}</span>
    </div>
    <button type="button" class="eina eina-text ml-auto" title="Acaba d'editar (Esc)" @mousedown.prevent @click="format('surt')"><span class="text-[12px]">Fet</span></button>
  </div>
</template>
