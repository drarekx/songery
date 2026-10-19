<!--
  Barra de format mentre s'edita un marc de lletra: acord, marques (tònica, negreta, cursiva, cor),
  secció i nota, imatge, importar text, tallar, i la mida: la del text seleccionat o, si no n'hi ha, la
  de tota la lletra.
  Els botons no prenen el focus (mousedown.prevent) perquè el cursor es quedi on és a la lletra.
-->
<script setup>
import { computed } from "vue";
import { GRUPS_LLETRA, tooltip } from "@/eines.js";
import { useEditorStore } from "@/stores/editor.js";

const store = useEditorStore();

const GRUPS = GRUPS_LLETRA;

const format = (nom) => store.crida("format", nom);

// Amb text seleccionat, la mida és la d'aquell text; si no, la de tota la lletra de la cançó.
const midaActual = computed(() => (store.edicio.seleccionat ? store.edicio.midaSeleccio : store.edicio.mida));
const canviaMida = (punts) => store.crida(store.edicio.seleccionat ? "midaSeleccio" : "midaMarc", punts);
</script>

<template>
  <div v-if="store.edicio" class="flex flex-wrap items-center gap-x-1 gap-y-1 border-b border-accent-200 bg-accent-50 px-3 py-1.5" role="toolbar" aria-label="Format de la lletra">
    <span class="px-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-accent-700">Lletra</span>
    <button type="button" class="eina" data-tooltip="Acord sobre la paraula seleccionada o al cursor (⌘K, o escriu [G])" aria-label="Afegeix un acord"
            @mousedown.prevent @click="format('acord')">
      <span class="font-mono text-[13px] font-bold text-accent-600">G</span>
    </button>
    <template v-for="(grup, g) in GRUPS" :key="g">
      <span v-if="g" class="separador" aria-hidden="true"></span>
      <button v-for="eina in grup" :key="eina.nom" type="button" class="eina" :data-tooltip="tooltip(eina)" :aria-label="tooltip(eina)"
              :aria-pressed="eina.marca ? String(!!store.edicio.actius?.[eina.nom]) : undefined"
              @mousedown.prevent @click="format(eina.nom)">
        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" v-html="eina.icona"></svg>
      </button>
    </template>
    <span class="separador" aria-hidden="true"></span>
    <div class="flex items-center gap-1.5" :title="store.edicio.seleccionat ? 'Mida del text seleccionat' : 'Mida de la lletra de tota la cançó (a totes les pàgines)'">
      <span class="text-[12px] font-medium text-accent-700">{{ store.edicio.seleccionat ? "Mida del text seleccionat" : "Mida" }}</span>
      <div class="inline-flex items-stretch rounded-md border border-paper-300 bg-white shadow-suau">
        <button type="button" class="w-7 rounded-l-md text-[15px] leading-none text-ink-500 hover:bg-paper-100"
                :aria-label="store.edicio.seleccionat ? 'Text seleccionat més petit' : 'Lletra més petita'"
                @mousedown.prevent @click="canviaMida(midaActual - 0.5)">−</button>
        <input type="number" step="0.5" min="3" max="60" class="w-14 border-x border-paper-300 bg-transparent text-center font-mono text-[12px] font-semibold tabular-nums outline-none"
               :aria-label="store.edicio.seleccionat ? 'Mida del text seleccionat (pt)' : 'Mida de la lletra (pt)'" :value="midaActual"
               @change="canviaMida(Number($event.target.value))">
        <button type="button" class="w-7 rounded-r-md text-[15px] leading-none text-ink-500 hover:bg-paper-100"
                :aria-label="store.edicio.seleccionat ? 'Text seleccionat més gran' : 'Lletra més gran'"
                @mousedown.prevent @click="canviaMida(midaActual + 0.5)">+</button>
      </div>
      <span class="text-[11px] text-ink-500">pt</span>
      <label class="ml-1 flex items-center gap-1.5 text-[12px] text-ink-700" title="Si no hi cap, la lletra es fa més petita automàticament">
        <input type="checkbox" class="h-3.5 w-3.5 accent-accent-500" :checked="store.edicio.ajusta" @change="store.crida('ajustaMarc', $event.target.checked)"> Ajusta</label>
      <span class="text-[11px]" :class="store.edicio.efectiva?.alerta ? 'text-perill-600' : 'text-ink-500'">{{ store.edicio.efectiva?.text }}</span>
    </div>
    <button type="button" class="eina eina-text ml-auto" title="Acaba d'editar (Esc)" @mousedown.prevent @click="format('surt')"><span class="text-[12px]">Fet</span></button>
  </div>
</template>
