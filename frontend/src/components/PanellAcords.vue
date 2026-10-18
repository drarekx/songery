<!--
  Acords de la cançó oberta amb el seu diagrama, per arrossegar-los a la pàgina (o clicar-los).
  «Tots els acords» posa la fila sencera. Deixar-los anar a la pàgina ho fa editor.js (llegeix TIPUS_ACORD).
-->
<script setup>
import { TIPUS_ACORD, useEditorStore } from "@/stores/editor.js";

const store = useEditorStore();

function arrossega(ev, nom) {
  ev.dataTransfer.setData(TIPUS_ACORD, nom);
  ev.dataTransfer.effectAllowed = "copy";
}
</script>

<template>
  <p v-if="!store.canco" class="text-[13px] text-ink-500">Obre una cançó per veure'n els acords.</p>
  <div v-else class="grid grid-cols-4 gap-2">
    <button type="button" class="fitxa-acord col-span-4 py-2" draggable="true" title="Tots els acords de la cançó"
            :disabled="!store.editable" @dragstart="arrossega($event, '*')" @click="store.afegeixDiagrama('*')">
      <span class="flex flex-col items-center gap-0.5">
        <span class="text-[13px] font-semibold">Tots els acords</span>
        <span class="max-w-full truncate font-mono text-[11px] text-ink-500">{{ store.acords.length ? store.acords.join(" · ") : "La cançó encara no en té" }}</span>
      </span>
    </button>
    <button v-for="acord in store.acords" :key="acord" type="button" class="fitxa-acord" draggable="true"
            :title="`Acord ${acord}`" :disabled="!store.editable"
            @dragstart="arrossega($event, acord)" @click="store.afegeixDiagrama(acord)">
      <!-- El SVG el genera el servidor (diagrames.py) a partir del nom de l'acord, escapat. -->
      <span v-if="store.diagrames[acord]" class="block w-full" v-html="store.diagrames[acord]"></span>
      <span v-else class="block w-full py-3 text-center font-mono text-[13px]">{{ acord }}</span>
    </button>
  </div>
</template>
