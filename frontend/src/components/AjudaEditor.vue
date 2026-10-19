<!--
  Ajuda de l'editor: el botó «?» de la barra d'eines obre un panell petit, ancorat al botó, amb què fa
  cada eina i les dreceres. Tot surt de frontend/src/eines.js (el mateix que fan servir les barres), així
  que una eina nova hi apareix sola. Es tanca amb Esc, clicant fora o amb la creu; la tecla «?» l'obre.
-->
<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { DRECERES, EINES_LLENC, GRUPS_EINES, GRUPS_LLETRA, TEXT_SELECCIONAT } from "@/eines.js";

const obert = ref(false);
const boto = ref(null);
const panell = ref(null);
const posicio = ref({});

async function obre() {
  obert.value = true;
  await nextTick();
  const r = boto.value.getBoundingClientRect();
  const ample = Math.min(448, window.innerWidth - 32);
  posicio.value = { top: `${r.bottom + 6}px`, left: `${Math.max(16, Math.min(r.right - ample, window.innerWidth - ample - 16))}px`, width: `${ample}px` };
  panell.value?.focus();
}

function tanca(tornaFocus = true) {
  if (!obert.value) return;
  obert.value = false;
  if (tornaFocus) boto.value?.focus();
}

const commuta = () => (obert.value ? tanca() : obre());

const escrivint = (el) => !!el?.closest?.("input, textarea, select, [contenteditable='true'], [contenteditable='plaintext-only'], dialog[open]");

function tecla(ev) {
  if (ev.key === "Escape" && obert.value) {
    ev.preventDefault();
    ev.stopPropagation();
    tanca();
  } else if (ev.key === "?" && !ev.metaKey && !ev.ctrlKey && !escrivint(ev.target)) {
    ev.preventDefault();
    commuta();
  }
}

function fora(ev) {
  if (obert.value && !panell.value?.contains(ev.target) && !boto.value?.contains(ev.target)) tanca(false);
}

onMounted(() => {
  document.addEventListener("keydown", tecla, true);
  document.addEventListener("pointerdown", fora, true);
});
onBeforeUnmount(() => {
  document.removeEventListener("keydown", tecla, true);
  document.removeEventListener("pointerdown", fora, true);
});

const seccions = [
  ...GRUPS_EINES.map((g) => ({ titol: g.titol, eines: g.eines })),
  { titol: "Moure't pel llenç", eines: EINES_LLENC },
  { titol: "Mentre escrius la lletra", eines: GRUPS_LLETRA.flat() },
  { titol: "Amb text seleccionat", eines: TEXT_SELECCIONAT },
];
</script>

<template>
  <button ref="boto" type="button" class="eina" aria-label="Ajuda" data-tooltip="Ajuda (?)" :aria-expanded="String(obert)"
          aria-controls="ajuda-editor" @click="commuta">
    <span class="text-[15px] font-semibold leading-none">?</span>
  </button>
  <Teleport to="body">
    <section v-if="obert" id="ajuda-editor" ref="panell" class="ajuda-editor" :style="posicio" role="dialog" aria-label="Ajuda de l'editor" tabindex="-1">
      <header class="flex items-center justify-between gap-3 border-b border-paper-200 px-4 py-2.5">
        <h2 class="font-display text-lg font-medium">Ajuda de l'editor</h2>
        <button type="button" class="eina" aria-label="Tanca l'ajuda" @click="tanca()">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m4 4 8 8m0-8-8 8"/></svg>
        </button>
      </header>
      <div class="flex flex-col gap-4 overflow-y-auto px-4 py-3">
        <section v-for="s in seccions" :key="s.titol">
          <h3 class="mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400">{{ s.titol }}</h3>
          <ul class="flex flex-col">
            <li v-for="e in s.eines" :key="e.titol" class="flex gap-3 py-1.5">
              <span class="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded border border-paper-300 text-ink-700" aria-hidden="true">
                <svg v-if="e.icona" class="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" v-html="e.icona"></svg>
              </span>
              <span class="min-w-0 flex-1">
                <span class="flex flex-wrap items-baseline justify-between gap-x-2">
                  <span class="text-[13.5px] font-medium text-ink-900">{{ e.titol.split(":")[0] }}</span>
                  <kbd v-if="e.drecera" class="font-sans text-[11.5px] text-ink-400">{{ e.drecera }}</kbd>
                </span>
                <span class="block text-[12.5px] leading-snug text-ink-500">{{ e.descripcio }}</span>
              </span>
            </li>
          </ul>
        </section>
        <section>
          <h3 class="mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400">Dreceres</h3>
          <dl class="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[12.5px]">
            <template v-for="[d, text] in DRECERES" :key="d">
              <dt class="font-mono text-ink-700">{{ d }}</dt><dd class="text-ink-500">{{ text }}</dd>
            </template>
          </dl>
        </section>
      </div>
    </section>
  </Teleport>
</template>
