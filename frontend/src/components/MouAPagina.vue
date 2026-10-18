<!-- Passar la selecció a la pàgina anterior o a la següent (alternativa a arrossegar-la). -->
<script setup>
import { useEditorStore } from "@/stores/editor.js";

const store = useEditorStore();
</script>

<template>
  <div v-if="store.propietats.moure.visible" class="grid grid-cols-2 gap-2">
    <button type="button" class="btn btn-petit" title="Mou a la pàgina anterior (també pots arrossegar-ho)"
            :disabled="!store.propietats.moure.anterior" @click="store.crida('accio', 'a-pagina-anterior')">← Pàgina anterior</button>
    <button type="button" class="btn btn-petit" title="Mou a la pàgina següent (també pots arrossegar-ho)"
            :disabled="!store.propietats.moure.seguent" @click="store.crida('accio', 'a-pagina-seguent')">Pàgina següent →</button>
  </div>
</template>
