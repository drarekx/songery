<!-- Pestanya «Disseny»: propietats de la selecció (un element o diversos) o, si no n'hi ha, de la pàgina. -->
<script setup>
import { useEditorStore } from "@/stores/editor.js";
import PropietatsElement from "./PropietatsElement.vue";
import PropietatsMulti from "./PropietatsMulti.vue";
import PropietatsPagina from "./PropietatsPagina.vue";

const store = useEditorStore();
</script>

<template>
  <PropietatsMulti v-if="store.propietats.mode === 'multi'" />
  <PropietatsElement v-else-if="store.propietats.mode === 'element'" />
  <PropietatsPagina v-else />
</template>
