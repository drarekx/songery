<!--
  Propietats quan no hi ha res seleccionat: la pàgina (mestra, costat de la mestra i fons), o la
  pàgina mestra que s'edita (nom, duplicar, esborrar), i l'ajuda de l'editor.
-->
<script setup>
import { computed } from "vue";
import { useEditorStore } from "@/stores/editor.js";
import SelectorColor from "./SelectorColor.vue";

const store = useEditorStore();
const pagina = computed(() => store.propietats.pagina);
const tipus = computed(() => pagina.value?.tipus);
const titol = computed(() => ({ llibre: "Tot el llibret", mestra: "Pàgina mestra" })[tipus.value] || "Pàgina");
const colors = () => store.crida("colorsDelDocument");

/** «{titol}»: les variables dels textos (es fa amb una funció perquè «}}» tancaria la interpolació). */
const variable = (v) => "{" + v + "}";
const VARIABLES = ["titol", "autor", "acords", "pagina", "subtitol", "any"];
const DRECERES = [
  ["←↑→↓", "mou 0,5 mm (⇧ 5 mm)"], ["⌥ arrossega", "sense guies"], ["⇧ nansa", "manté la proporció"],
  ["⌘C ⌘V ⌘D", "copia, enganxa, duplica"], ["⇧ clic", "afegeix a la selecció"], ["arrossega", "en una zona buida, selecciona"],
  ["⌘A", "selecciona tota la pàgina"], ["⌘G ⇧⌘G", "agrupa, desagrupa"], ["Supr", "esborra l'element"],
];

const canviaPagina = (canvis) => store.crida("canviaPagina", canvis);
</script>

<template>
  <div class="flex flex-col gap-4 p-4">
    <h3 class="font-display text-lg font-medium">{{ titol }}</h3>
    <template v-if="pagina && tipus !== 'llibre'">
      <template v-if="tipus !== 'mestra'">
        <label><span class="etiqueta">Pàgina mestra</span>
          <select class="camp py-1.5 text-[14px]" :value="pagina.mestra || ''" :disabled="!store.editable"
                  @change="canviaPagina({ mestra: $event.target.value || null })">
            <option value="">Cap (pàgina neta)</option>
            <option v-for="m in store.mestres" :key="m.id" :value="m.id">{{ m.nom }}</option>
          </select></label>
        <label v-if="pagina.mestra"><span class="etiqueta">Costat de la mestra</span>
          <select class="camp py-1.5 text-[14px]" :value="pagina.costat || ''" :disabled="!store.editable"
                  @change="canviaPagina({ costat: $event.target.value || null })">
            <option value="">Segons on caigui la pàgina</option>
            <option value="esquerra">Sempre el de l'esquerra</option>
            <option value="dreta">Sempre el de la dreta</option>
          </select></label>
        <div class="flex items-center justify-between gap-3 text-[14px]">Color de fons
          <SelectorColor :model-value="pagina.fons || '#ffffff'" :colors="colors" :disabled="!store.editable"
                         @update:model-value="canviaPagina({ fons: $event })" /></div>
      </template>
      <div v-else class="rounded-md bg-paper-200/60 p-3 text-[13px] leading-snug text-ink-700">
        <label class="mb-2 block"><span class="etiqueta">Nom de la mestra</span>
          <input class="camp py-1.5 text-[14px]" :value="pagina.nomMestra" @input="store.crida('canviaNomMestra', $event.target.value)"></label>
        El que posis aquí surt a totes les pàgines que fan servir aquesta mestra: a l'esquerra, les parells; a la dreta, les senars.
        <div class="-ml-2 mt-2 flex flex-wrap gap-1">
          <button type="button" class="btn btn-fantasma btn-petit" @click="store.crida('duplicaMestra')">Duplica</button>
          <button v-if="pagina.mestraEsborrable" type="button" class="btn btn-perill btn-petit" @click="store.crida('esborraMestra')">Esborra aquesta mestra</button>
        </div>
      </div>
      <button type="button" class="btn btn-petit" @click="store.crida('desaABiblioteca', 'pagina')">Desa els elements de la pàgina a la biblioteca</button>
    </template>
    <p class="text-[13px] leading-snug text-ink-500">Doble clic en un marc de lletra o en un text per escriure-hi. Als textos pots fer servir
      <template v-for="(v, i) in VARIABLES" :key="v">{{ i ? " " : "" }}<code class="font-mono text-ink-900">{{ variable(v) }}</code></template>.</p>
    <dl class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 border-t border-paper-300 pt-3 text-[12px] text-ink-500">
      <template v-for="[tecla, text] in DRECERES" :key="tecla">
        <dt class="font-mono text-ink-700">{{ tecla }}</dt><dd>{{ text }}</dd>
      </template>
    </dl>
  </div>
</template>
