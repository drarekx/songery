<!-- Avís a sobre del llenç (p. ex. una versió fixada que no es pot editar), amb les accions que proposa. -->
<script setup>
import { useEditorStore } from "@/stores/editor.js";

const store = useEditorStore();
</script>

<template>
  <div v-if="store.avis" class="mx-4 mt-3 flex items-start gap-3 rounded-md border border-sky-200 bg-sky-50 px-3 py-2.5 text-[13px] text-sky-950" role="status">
    <svg class="mt-0.5 h-4 w-4 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M5 7V5a3 3 0 0 1 6 0v2M4 7h8v6H4z"/></svg>
    <div class="min-w-0 flex-1">
      <p class="leading-snug">{{ store.avis.text }}</p>
      <div v-if="store.avis.accions?.length" class="mt-2 flex flex-wrap gap-2">
        <button v-for="a in store.avis.accions" :key="a.text" type="button" class="btn btn-petit" :class="{ 'btn-primari': a.primari }" @click="a.fes()">{{ a.text }}</button>
      </div>
    </div>
  </div>
</template>
