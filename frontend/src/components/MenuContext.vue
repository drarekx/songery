<!--
  Menú del botó dret. El contingut l'obre qui el necessita amb store.obreMenu(x, y, items):
  items: {text, fes(), drecera, perill, desactivat, marcat} | {text, submenu: [items]} | {seccio: "títol"} |
  {separador: true}.
  Es fa servir amb el ratolí o amb el teclat (fletxes, Intro, Esc; → i ← entren i surten dels submenús)
  i es tanca clicant fora.
-->
<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useEditorStore } from "@/stores/editor.js";

const store = useEditorStore();
const menu = ref(null);
const sub = ref(null);
const posicio = ref({ left: "0px", top: "0px" });
const posicioSub = ref({ left: "0px", top: "0px" });
const actiu = ref(-1);
const obert = ref(-1); // índex de l'element amb el submenú obert
const actiuSub = ref(-1);
let espera = null;

const numera = (items) => (items || []).map((item, i) => ({ ...item, i }));
const opcions = computed(() => numera(store.menu?.items));
const opcionsSub = computed(() => numera(store.menu?.items?.[obert.value]?.submenu));
const triables = (llista) => llista.filter((o) => o.text && !o.desactivat).map((o) => o.i);

function tanca() {
  clearTimeout(espera);
  obert.value = -1;
  store.tancaMenu();
}

function tria(item) {
  if (!item.text || item.desactivat) return;
  if (item.submenu) return obreSub(item.i, true);
  tanca();
  item.fes?.();
}

/** Obre el submenú de l'element i, al costat de l'element (o a l'altra banda si no hi cap). */
async function obreSub(i, focus = false) {
  clearTimeout(espera);
  if (obert.value !== i) {
    obert.value = i;
    actiuSub.value = -1;
    const boto = menu.value?.querySelector(`[data-index="${i}"]`);
    if (!boto) return;
    const r = boto.getBoundingClientRect();
    posicioSub.value = { left: `${r.right + 2}px`, top: `${r.top - 4}px` };
    await nextTick();
    const s = sub.value.getBoundingClientRect();
    const left = r.right + 2 + s.width > window.innerWidth - 8 ? Math.max(8, r.left - s.width - 2) : r.right + 2;
    const top = r.top - 4 + s.height > window.innerHeight - 8 ? Math.max(8, window.innerHeight - s.height - 8) : r.top - 4;
    posicioSub.value = { left: `${left}px`, top: `${top}px` };
  }
  if (focus) {
    await nextTick();
    actiuSub.value = triables(opcionsSub.value)[0] ?? -1;
    sub.value?.querySelector(`[data-index="${actiuSub.value}"]`)?.focus();
  }
}

/** En passar el ratolí per un element del menú principal: obre el seu submenú o tanca l'obert. */
function entra(item) {
  actiu.value = item.i;
  clearTimeout(espera);
  if (item.submenu && !item.desactivat) espera = setTimeout(() => obreSub(item.i), 120);
  else if (obert.value >= 0) espera = setTimeout(() => { obert.value = -1; }, 200);
}

/** El ratolí ja és al submenú: que no es tanqui. */
const quieta = () => clearTimeout(espera);

function mou(ev, llista, valor, contenidor) {
  ev.preventDefault();
  const pos = llista.indexOf(valor.value);
  const seguent = ev.key === "ArrowDown" ? (pos + 1) % llista.length : (pos - 1 + llista.length) % llista.length;
  valor.value = llista[pos === -1 && ev.key === "ArrowUp" ? llista.length - 1 : seguent];
  contenidor?.querySelector(`[data-index="${valor.value}"]`)?.focus();
}

function teclat(ev) {
  if (!store.menu) return;
  const dinsSub = obert.value >= 0 && actiuSub.value >= 0;
  if (ev.key === "Escape" || (ev.key === "ArrowLeft" && dinsSub)) {
    ev.preventDefault();
    ev.stopPropagation();
    if (dinsSub) {
      obert.value = -1;
      return menu.value?.querySelector(`[data-index="${actiu.value}"]`)?.focus();
    }
    return tanca();
  }
  if (dinsSub) {
    if (ev.key === "ArrowDown" || ev.key === "ArrowUp") mou(ev, triables(opcionsSub.value), actiuSub, sub.value);
    else if (ev.key === "Enter") { ev.preventDefault(); tria(opcionsSub.value[actiuSub.value]); }
    return;
  }
  if (ev.key === "ArrowDown" || ev.key === "ArrowUp") mou(ev, triables(opcions.value), actiu, menu.value);
  else if ((ev.key === "Enter" || ev.key === "ArrowRight") && actiu.value >= 0) {
    const item = opcions.value[actiu.value];
    if (ev.key === "ArrowRight" && !item?.submenu) return;
    ev.preventDefault();
    tria(item);
  }
}

function fora(ev) {
  if (store.menu && !menu.value?.contains(ev.target) && !sub.value?.contains(ev.target)) tanca();
}

watch(() => store.menu, async (nou) => {
  actiu.value = -1;
  obert.value = -1;
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
  clearTimeout(espera);
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
        <button v-else type="button" class="menu-context-item" :class="{ perill: item.perill, 'sub-obert': item.submenu && obert === item.i }"
                role="menuitem" :data-index="item.i" :disabled="item.desactivat"
                :aria-haspopup="item.submenu ? 'menu' : undefined" :aria-expanded="item.submenu ? String(obert === item.i) : undefined"
                :aria-checked="item.marcat === undefined ? undefined : String(item.marcat)"
                @mouseenter="entra(item)" @click="tria(item)">
          <span class="menu-context-marca" aria-hidden="true">{{ item.marcat ? "✓" : "" }}</span>
          <span class="flex-1 truncate text-left">{{ item.text }}</span>
          <kbd v-if="item.drecera" class="menu-context-drecera">{{ item.drecera }}</kbd>
          <svg v-if="item.submenu" class="menu-context-fletxa" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m6 3.5 4.5 4.5L6 12.5"/></svg>
        </button>
      </template>
    </div>
    <div v-if="store.menu && obert >= 0" ref="sub" class="menu-context" role="menu" tabindex="-1" :style="posicioSub"
         @contextmenu.prevent @mouseenter="quieta">
      <template v-for="item in opcionsSub" :key="item.i">
        <div v-if="item.separador" class="menu-context-separador" role="separator"></div>
        <div v-else-if="item.seccio" class="menu-context-seccio">{{ item.seccio }}</div>
        <button v-else type="button" class="menu-context-item" :class="{ perill: item.perill }" role="menuitem"
                :data-index="item.i" :disabled="item.desactivat" :aria-checked="item.marcat === undefined ? undefined : String(item.marcat)"
                @mouseenter="actiuSub = item.i" @click="tria(item)">
          <span class="menu-context-marca" aria-hidden="true">{{ item.marcat ? "✓" : "" }}</span>
          <span class="flex-1 truncate text-left">{{ item.text }}</span>
          <kbd v-if="item.drecera" class="menu-context-drecera">{{ item.drecera }}</kbd>
        </button>
      </template>
    </div>
  </Teleport>
</template>
