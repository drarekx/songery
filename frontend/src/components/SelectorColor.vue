<!--
  Selector de color del disseny: CMYK exacte per a impremta («cmyk(c,m,y,k)», en %) o RGB («#rrggbb»).
  v-model amb el valor; buit: text de l'opció «sense color» (null: no n'hi ha); perDefecte: el valor que
  es mostra quan és buit (p. ex. el color de l'estil); colors: funció que retorna els colors del document.
-->
<script setup>
import { computed, nextTick, onBeforeUnmount, ref } from "vue";
import { cmykAHex, colorCss, llegeixCmyk } from "@/pagines.js";
import { CANALS, PALETA, descriuColor, hexACmyk } from "@/colors.js";

const props = defineProps({
  modelValue: { type: String, default: "" },
  buit: { type: String, default: null },
  perDefecte: { type: String, default: undefined },
  colors: { type: Function, default: null },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["update:modelValue"]);

const obert = ref(false);
const boto = ref(null);
const popover = ref(null);
const posicio = ref({ left: "0px", top: "0px" });
const cmyk = ref([0, 0, 0, 100]);

const mostrat = computed(() => props.modelValue || props.perDefecte || "");
const etiqueta = computed(() => {
  if (props.modelValue) return descriuColor(props.modelValue);
  if (props.perDefecte) return `${descriuColor(props.perDefecte)} (estil)`;
  return props.buit || "Cap";
});
const esCmyk = computed(() => !!llegeixCmyk(props.modelValue));
const delDocument = computed(() =>
  [...new Set((props.colors?.() || []).filter(Boolean))].slice(0, 14).map((v) => [descriuColor(v), v]));
const textCmyk = computed(() => `cmyk(${cmyk.value.join(",")})`);

function canvia(valor) {
  emit("update:modelValue", valor);
}

function posaCanal(i, valor) {
  const nou = [...cmyk.value];
  nou[i] = Math.min(100, Math.max(0, Number(valor) || 0));
  cmyk.value = nou;
  canvia(textCmyk.value);
}

function tria(valor) {
  const v = llegeixCmyk(valor);
  if (v) {
    cmyk.value = v;
    canvia(textCmyk.value);
  } else {
    canvia(valor);
    tanca();
  }
}

async function obre() {
  const inicial = mostrat.value;
  cmyk.value = llegeixCmyk(inicial) || (inicial.startsWith("#") ? hexACmyk(inicial) : [0, 0, 0, 100]);
  obert.value = true;
  await nextTick();
  const r = boto.value.getBoundingClientRect();
  const p = popover.value;
  const left = Math.min(window.innerWidth - p.offsetWidth - 8, Math.max(8, r.right - p.offsetWidth));
  const top = r.bottom + 6 + p.offsetHeight < window.innerHeight ? r.bottom + 6 : Math.max(8, r.top - p.offsetHeight - 6);
  posicio.value = { left: `${left}px`, top: `${top}px` };
  p.querySelector("input[type=number]")?.focus();
  document.addEventListener("pointerdown", fora, true);
  document.addEventListener("keydown", escapa, true);
}

function tanca() {
  obert.value = false;
  document.removeEventListener("pointerdown", fora, true);
  document.removeEventListener("keydown", escapa, true);
}

function fora(ev) {
  if (!popover.value?.contains(ev.target) && !boto.value?.contains(ev.target)) tanca();
}

function escapa(ev) {
  if (ev.key === "Escape") {
    ev.stopPropagation();
    tanca();
  }
}

onBeforeUnmount(tanca);
</script>

<template>
  <button ref="boto" type="button" class="boto-color" :disabled="disabled"
          :title="esCmyk ? 'Color CMYK: surt exacte al PDF per a impremta' : 'Tria el color'"
          :aria-expanded="obert" @click="obert ? tanca() : obre()">
    <span class="mostra-color" :class="{ buit: !mostrat }" :style="{ background: mostrat ? colorCss(mostrat) : '' }" aria-hidden="true"></span>
    <span class="text-color">{{ etiqueta }}</span>
  </button>
  <Teleport to="body">
    <div v-if="obert" ref="popover" class="popover-color" role="dialog" aria-label="Color" :style="posicio">
      <div class="flex items-center gap-2">
        <span class="mostra-color gran" :style="{ background: cmykAHex(cmyk) }" aria-hidden="true"></span>
        <span class="font-mono text-[12px] text-ink-700">{{ descriuColor(textCmyk) }}</span>
      </div>
      <label v-for="(canal, i) in CANALS" :key="canal.clau" class="fila-canal">
        <span class="w-4 font-mono text-[12px] font-semibold">{{ canal.nom }}</span>
        <input type="range" min="0" max="100" step="1" class="barra-canal" :style="{ '--canal': canal.color }"
               :aria-label="`${canal.nom} (%)`" :value="cmyk[i]" @input="posaCanal(i, $event.target.value)">
        <input type="number" min="0" max="100" step="0.5" class="camp w-16 px-2 py-1 text-right font-mono text-[13px]"
               :aria-label="`${canal.nom} (%)`" :value="cmyk[i]"
               @input="$event.target.value !== '' && posaCanal(i, $event.target.value)">
        <span class="text-[12px] text-ink-500">%</span>
      </label>
      <p class="etiqueta mb-0 mt-1">Tintes</p>
      <div class="flex flex-wrap gap-1">
        <button v-for="[nom, valor] in PALETA" :key="valor" type="button" class="mostra-paleta"
                :title="`${nom} · ${descriuColor(valor)}`" :aria-label="nom" :style="{ background: colorCss(valor) }"
                @click="tria(valor)"></button>
      </div>
      <template v-if="delDocument.length">
        <p class="etiqueta mb-0 mt-1">D'aquest cançoner</p>
        <div class="flex flex-wrap gap-1">
          <button v-for="[nom, valor] in delDocument" :key="valor" type="button" class="mostra-paleta"
                  :title="nom" :aria-label="nom" :style="{ background: colorCss(valor) }" @click="tria(valor)"></button>
        </div>
      </template>
      <div class="mt-1 flex items-center justify-between gap-2 border-t border-paper-200 pt-2 text-[12px] text-ink-500">
        <label class="flex items-center gap-2">
          <input type="color" class="h-8 w-10 cursor-pointer rounded border border-paper-300 bg-white p-0.5" aria-label="Color RGB"
                 :value="modelValue?.startsWith('#') ? modelValue : cmykAHex(cmyk)" @input="canvia($event.target.value)">
          <span>o en RGB (pantalla)</span>
        </label>
        <button v-if="buit" type="button" class="btn btn-fantasma btn-petit" @click="canvia(''); tanca()">{{ buit }}</button>
      </div>
      <p class="text-[11px] leading-snug text-ink-500">En CMYK, el color surt exacte al PDF per a impremta. A la pantalla és una aproximació.</p>
    </div>
  </Teleport>
</template>
