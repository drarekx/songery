<!-- Propietats de diversos elements seleccionats o d'un grup: agrupar, alinear, moure de pàgina. -->
<script setup>
import { computed } from "vue";
import { useEditorStore } from "@/stores/editor.js";
import AccionsElement from "./AccionsElement.vue";
import MouAPagina from "./MouAPagina.vue";

const store = useEditorStore();
const multi = computed(() => store.propietats.multi);

const ALINEACIONS = [
  ["esquerra", "A l'esquerra", "M3 2v12M5 5h8M5 10h5"], ["centre", "Al centre", "M8 2v12M4 5h8M5.5 10h5"],
  ["dreta", "A la dreta", "M13 2v12M3 5h8M6 10h5"], ["dalt", "A dalt", "M2 3h12M5 5v8M10 5v5"],
  ["mig", "Al mig", "M2 8h12M5 4v8M10 5.5v5"], ["baix", "A baix", "M2 13h12M5 3v8M10 6v5"],
];
</script>

<template>
  <div v-if="multi" class="flex flex-col gap-4 p-4">
    <div class="flex items-center justify-between gap-2">
      <h3 class="font-display text-lg font-medium">{{ multi.grup ? `Grup (${multi.n} elements)` : `${multi.n} elements seleccionats` }}</h3>
      <AccionsElement />
    </div>
    <p class="text-[13px] leading-snug text-ink-500">{{ multi.grup ? "Es mou, s'escala i es gira com un sol element." : "Agrupa'ls perquè es moguin sempre junts." }}</p>
    <div class="grid grid-cols-2 gap-2">
      <button v-if="!multi.grup" type="button" class="btn btn-primari btn-petit" title="⌘G" :disabled="!store.editable" @click="store.crida('accio', 'agrupa')">Agrupa</button>
      <button v-if="multi.algunGrup" type="button" class="btn btn-petit" title="⇧⌘G" :disabled="!store.editable" @click="store.crida('accio', 'desagrupa')">Desagrupa</button>
    </div>
    <label v-if="multi.ambEstil"><span class="etiqueta">Estil {{ multi.ambEstil < multi.n ? `(dels ${multi.ambEstil} textos)` : "" }}</span>
      <select class="camp py-1.5 text-[14px]" :value="multi.estil" :disabled="!store.editable" @change="store.crida('posaEstil', $event.target.value)">
        <option v-if="!multi.estil" value="" disabled>Estils diferents</option>
        <option v-for="(s, clau) in store.estils" :key="clau" :value="clau">{{ s.nom }}</option>
      </select></label>
    <div>
      <span class="etiqueta">Alinea</span>
      <div class="grid grid-cols-6 gap-1">
        <button v-for="[clau, titol, cami] in ALINEACIONS" :key="clau" type="button" class="btn btn-icona h-8 w-full"
                :title="titol" :aria-label="titol" :disabled="!store.editable" @click="store.crida('alinea', clau)">
          <svg class="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path :d="cami"/></svg>
        </button>
      </div>
    </div>
    <p class="text-[12px] leading-snug text-ink-500">Arrossega per moure-ho tot junt. Les nanses de les cantonades ho escalen tot, també la mida de la lletra. Doble clic en un element del grup per tocar-lo sol.</p>
    <MouAPagina />
    <button type="button" class="btn btn-fantasma btn-petit" @click="store.crida('desaABiblioteca', 'multi')">Desa la selecció a la biblioteca</button>
  </div>
</template>
