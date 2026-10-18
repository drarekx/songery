<!--
  Menú del botó dret. El contingut l'obre qui el necessita amb store.obreMenu(x, y, items):
  items: {text, fes(), drecera, perill, desactivat, marcat} | {seccio: "títol"} | {separador: true}.
  Es fa servir amb el ratolí o amb el teclat (fletxes, Intro, Esc) i es tanca clicant fora.
-->
<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useEditorStore } from "@/stores/editor.js";

const store = useEditorStore();
const menu = ref(null);
const posicio = ref({ left: "0px", top: "0px" });
const actiu = ref(-1);
const opcions = computed(() => (store.menu?.items || []).map((item, i) => ({ ...item, i })));
const triables = computed(() => opcions.value.filter((o) => o.text && !o.desactivat).map((o) => o.i));

function tanca() {
  store.tancaMenu();
}

function tria(item) {
  if (!item.text || item.desactivat) return;
  tanca();
  item.fes?.();
}

function teclat(ev) {
  if (!store.menu) return;
  if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); return tanca(); }
  const llista = triables.value;
  if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
    ev.preventDefault();
    const pos = llista.indexOf(actiu.value);
    const seguent = ev.key === "ArrowDown" ? (pos + 1) % llista.length : (pos - 1 + llista.length) % llista.length;
    actiu.value = llista[pos === -1 && ev.key === "ArrowUp" ? llista.length - 1 : seguent];
    menu.value?.querySelector(`[data-index="${actiu.value}"]`)?.focus();
  } else if (ev.key === "Enter" && actiu.value >= 0) {
    ev.preventDefault();
    tria(store.menu.items[actiu.value]);
  }
}

function fora(ev) {
  if (store.menu && !menu.value?.contains(ev.target)) tanca();
}

watch(() => store.menu, async (nou) => {
  actiu.value = -1;
  if (!nou) return;
  posicio.value = { left: `${nou.x}px`, top: `${nou.y}px` };
  await nextTick();
  // Que no surti de la finestra: si no hi cap, es posa a l'altra banda del punter.
  const r = menu.value.getBoundingClientRect();
  const left = nou.x + r.width > window.innerWidth - 8 ? Math.max(8, nou.x - r.width) : nou.x;
  const top = nou.y + r.height > window.innerHeight - 8 ? Math.max(8, window.innerHeight - r.height - 8) : nou.y;
  posicio.value = { left: `${left}px`, top: `${top}px` };
  menu.value.focus();
});

document.addEventListener("pointerdown", fora, true);
document.addEventListener("keydown", teclat, true);
window.addEventListener("blur", tanca);
window.addEventListener("resize", tanca);
document.addEventListener("scroll", tanca, true);
onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", fora, true);
  document.removeEventListener("keydown", teclat, true);
  window.removeEventListener("blur", tanca);
  window.removeEventListener("resize", tanca);
  document.removeEventListener("scroll", tanca, true);
});
</script>

<template>
  <Teleport to="body">
    <div v-if="store.menu" ref="menu" class="menu-context" role="menu" tabindex="-1" :style="posicio" @contextmenu.prevent>
      <template v-for="item in opcions" :key="item.i">
        <div v-if="item.separador" class="menu-context-separador" role="separator"></div>
        <div v-else-if="item.seccio" class="menu-context-seccio">{{ item.seccio }}</div>
        <button v-else type="button" class="menu-context-item" :class="{ perill: item.perill }" role="menuitem"
                :data-index="item.i" :disabled="item.desactivat" :aria-checked="item.marcat === undefined ? undefined : String(item.marcat)"
                @mouseenter="actiu = item.i" @click="tria(item)">
          <span class="menu-context-marca" aria-hidden="true">{{ item.marcat ? "✓" : "" }}</span>
          <span class="flex-1 truncate text-left">{{ item.text }}</span>
          <kbd v-if="item.drecera" class="menu-context-drecera">{{ item.drecera }}</kbd>
        </button>
      </template>
    </div>
  </Teleport>
</template>
