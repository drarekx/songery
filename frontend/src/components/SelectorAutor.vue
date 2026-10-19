<!--
  Selector d'autor: un camp de text amb la llista dels autors que coincideixen (sense accents ni
  majúscules), i l'opció «Crea «…»» si el nom encara no existeix. Patró ARIA combobox: fletxes, Intro i
  Esc. v-model amb el nom; el servidor vincula el nom a l'autor (o el crea) en desar la cançó.
-->
<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: String, default: "" },
  disabled: { type: Boolean, default: false },
  id: { type: String, default: () => `autor-${Math.random().toString(36).slice(2, 8)}` },
  placeholder: { type: String, default: "Sense autor" },
});
const emit = defineEmits(["update:modelValue"]);

const text = ref(props.modelValue || "");
const obert = ref(false);
const actiu = ref(-1);
const resultats = ref([]);
let espera = null;
let peticio = 0;

watch(() => props.modelValue, (v) => { if (!obert.value) text.value = v || ""; });

const clau = (t) => String(t || "").normalize("NFD").replace(/\p{Diacritic}/gu, "").replace(/\s+/g, " ").trim().toLowerCase();
const opcions = computed(() => {
  const llista = resultats.value.map((a) => ({ tipus: "autor", nom: a.nom, cancons: a.cancons }));
  const net = text.value.replace(/\s+/g, " ").trim();
  if (net && !resultats.value.some((a) => clau(a.nom) === clau(net))) llista.push({ tipus: "nou", nom: net });
  return llista;
});
const idOpcio = (i) => `${props.id}-opcio-${i}`;

async function cerca() {
  const n = ++peticio;
  try {
    const r = await fetch(`/api/autors?limit=8&q=${encodeURIComponent(text.value.trim())}`);
    if (n === peticio && r.ok) resultats.value = await r.json();
  } catch { /* sense connexió: només l'opció de crear */ }
}

function escriu() {
  obert.value = true;
  actiu.value = -1;
  clearTimeout(espera);
  espera = setTimeout(cerca, 120);
}

function tria(opcio) {
  text.value = opcio ? opcio.nom : "";
  obert.value = false;
  actiu.value = -1;
  if ((props.modelValue || "") !== text.value) emit("update:modelValue", text.value);
}

function tecla(ev) {
  const n = opcions.value.length;
  if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
    ev.preventDefault();
    if (!obert.value) { obert.value = true; cerca(); return; }
    if (!n) return;
    actiu.value = ev.key === "ArrowDown" ? (actiu.value + 1) % n : (actiu.value - 1 + n) % n;
  } else if (ev.key === "Enter") {
    if (!obert.value) return;
    ev.preventDefault();
    tria(actiu.value >= 0 ? opcions.value[actiu.value] : { nom: text.value.replace(/\s+/g, " ").trim() });
  } else if (ev.key === "Escape" && obert.value) {
    ev.preventDefault();
    ev.stopPropagation();
    obert.value = false;
    text.value = props.modelValue || "";
  }
}

// En sortir del camp, el que s'hi ha escrit queda com a autor (nou o existent).
function surt() {
  setTimeout(() => {
    if (!obert.value) return;
    tria({ nom: text.value.replace(/\s+/g, " ").trim() });
  }, 150);
}

onBeforeUnmount(() => clearTimeout(espera));
</script>

<template>
  <div class="relative">
    <input :id="id" v-model="text" class="camp pr-8" type="text" role="combobox" autocomplete="off" :disabled="disabled"
           :placeholder="placeholder" :aria-expanded="String(obert && opcions.length > 0)" :aria-controls="`${id}-llista`"
           aria-autocomplete="list" :aria-activedescendant="actiu >= 0 ? idOpcio(actiu) : undefined"
           @input="escriu" @focus="escriu" @keydown="tecla" @blur="surt">
    <button v-if="text && !disabled" type="button" class="absolute right-1.5 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded text-ink-400 hover:text-ink-900"
            aria-label="Treu l'autor" tabindex="-1" @mousedown.prevent @click="tria(null)">
      <svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m4 4 8 8m0-8-8 8"/></svg>
    </button>
    <ul v-show="obert && opcions.length" :id="`${id}-llista`" role="listbox" class="selector-autor-llista" aria-label="Autors">
      <li v-for="(o, i) in opcions" :id="idOpcio(i)" :key="o.tipus + o.nom" role="option" :aria-selected="String(i === actiu)"
          class="selector-autor-opcio" @mousedown.prevent @click="tria(o)" @mouseenter="actiu = i">
        <span v-if="o.tipus === 'nou'">Crea «<strong>{{ o.nom }}</strong>»</span>
        <template v-else><span class="flex-1 truncate">{{ o.nom }}</span><span class="text-[11px] text-ink-400">{{ o.cancons }}</span></template>
      </li>
    </ul>
  </div>
</template>
