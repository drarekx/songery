<!--
  Propietats de l'element seleccionat: les del seu tipus (lletra, text, imatge, forma, QR, diagrames…),
  l'estil i el format propi, la posició i la mida, i les accions.
-->
<script setup>
import { computed, ref } from "vue";
import { FONTS, QR_MINIM } from "@/pagines.js";
import { useEditorStore } from "@/stores/editor.js";
import AccionsElement from "./AccionsElement.vue";
import MouAPagina from "./MouAPagina.vue";
import SelectorColor from "./SelectorColor.vue";

const store = useEditorStore();
const e = computed(() => store.propietats.element);
const es = (...tipus) => tipus.includes(e.value?.tipus);
const colors = () => store.crida("colorsDelDocument");
const textarea = ref(null);

const NOMS = {
  diagrama: "Diagrama d'acord", text: "Text", lletra: "Marc de lletra", imatge: "Imatge", forma: "Forma", numero: "Número de pàgina",
  index: "Índex", diagrames: "Diagrames d'acords", qr: "Codi QR", index_qr: "Índex de vídeos",
};
/** «{titol}»: les variables dels textos (es fa amb una funció perquè «}}» tancaria la interpolació). */
const variable = (v) => "{" + v + "}";
const VARIABLES = ["titol", "autor", "acords", "pagina", "subtitol", "any", "contraportada"];
const ALINEACIONS = [["left", "Esquerra"], ["center", "Centre"], ["right", "Dreta"], ["justify", "Justificat"]];
const GRUIXOS = [300, 400, 500, 600, 700, 800];
const POSICIO = [["x", "X (mm)", 0.5], ["y", "Y (mm)", 0.5], ["w", "Amplada (mm)", 0.5], ["h", "Alçada (mm)", 0.5]];

const format = computed(() => e.value?.format || {});
const estil = computed(() => store.estils[e.value?.estil] || {});
const nomFont = computed(() => {
  const propia = store.tipografies.find((f) => f.clau === format.value.font);
  if (propia) return propia.nom;
  return `De l'estil (${store.tipografies.find((f) => f.clau === estil.value.font)?.nom || "—"})`;
});
const avisQr = computed(() => {
  if (!es("qr")) return "";
  if (!store.videos.length) return "Afegeix un vídeo a la pestanya Cançó.";
  const costat = Math.min(e.value.w, e.value.h - (e.value.peu ? 4.5 : 0));
  return costat < QR_MINIM ? `El codi fa ${costat.toFixed(1)} mm. Per escanejar-lo bé, fes-lo de ${QR_MINIM} mm o més.` : "";
});

function numero(prop, valor) {
  if (valor === "") return;
  const n = Number(valor);
  if (["x", "y", "w", "h", "rotacio", "opacitat"].includes(prop)) store.canviaPosicio(prop, n);
  else store.canviaPropietats({ [prop]: n });
}

function insereixVariable(v) {
  const camp = textarea.value;
  camp.setRangeText(`{${v}}`, camp.selectionStart, camp.selectionEnd, "end");
  store.canviaPropietats({ text: camp.value });
  camp.focus();
}
</script>

<template>
  <div v-if="e" class="flex flex-col gap-4 p-4">
    <div class="flex items-center justify-between gap-2">
      <h3 class="font-display text-lg font-medium">{{ NOMS[e.tipus] || "Element" }}</h3>
      <AccionsElement :bloquejat="!!e.bloquejat" />
    </div>

    <div v-if="e.grup" class="flex items-center justify-between gap-2 rounded-md bg-sky-50 px-3 py-2 text-[13px] text-sky-950">
      <span>Forma part d'un grup.</span>
      <button type="button" class="btn btn-petit" @click="store.crida('seleccionaGrup')">Selecciona el grup</button>
    </div>

    <!-- Marc de lletra -->
    <div v-if="es('lletra')" class="flex flex-col gap-3">
      <p class="rounded-md px-3 py-2 text-[13px] leading-snug"
         :class="e.infoMarc?.alerta ? 'bg-vermello-50 text-vermello-700' : 'bg-paper-200/60 text-ink-700'">{{ e.infoMarc?.text }}</p>
      <button type="button" class="btn btn-primari btn-petit" :disabled="!store.editable" @click="store.crida('editaLletra')">Edita la lletra</button>
      <label class="flex items-center justify-between gap-3 text-[14px]">Ajusta la mida perquè hi càpiga
        <span class="interruptor"><input class="peer sr-only" type="checkbox" :checked="e.ajusta !== false" :disabled="!store.editable"
               @change="store.canviaPropietats({ ajusta: $event.target.checked })"><span></span></span></label>
      <div class="grid grid-cols-2 gap-3">
        <label><span class="etiqueta">Columnes</span>
          <input type="number" step="1" min="1" max="4" class="camp py-1.5 font-mono text-[13px]" :value="e.columnes" :disabled="!store.editable" @input="numero('columnes', $event.target.value)"></label>
        <label><span class="etiqueta">Separació (mm)</span>
          <input type="number" step="0.5" min="0" max="40" class="camp py-1.5 font-mono text-[13px]" :value="e.separacio" :disabled="!store.editable" @input="numero('separacio', $event.target.value)"></label>
      </div>
    </div>

    <!-- Text -->
    <div v-if="es('text')" class="flex flex-col gap-3">
      <label><span class="etiqueta">Text</span>
        <textarea ref="textarea" rows="3" class="camp text-[14px]" :value="e.text" :disabled="!store.editable"
                  @input="store.canviaPropietats({ text: $event.target.value })"></textarea></label>
      <div class="flex flex-wrap gap-1">
        <button v-for="v in VARIABLES" :key="v" type="button" class="xip hover:bg-paper-300" :disabled="!store.editable" @click="insereixVariable(v)">{{ variable(v) }}</button>
      </div>
    </div>

    <!-- Estil i format propi -->
    <div v-if="es('text', 'numero', 'index', 'lletra')" class="flex flex-col gap-3">
      <label><span class="etiqueta">Estil</span>
        <select class="camp py-1.5 text-[14px]" :value="e.estil" :disabled="!store.editable" @change="store.canviaPropietats({ estil: $event.target.value })">
          <option v-for="(s, clau) in store.estils" :key="clau" :value="clau">{{ s.nom }}</option>
        </select></label>
      <details class="group rounded-md border border-paper-300 bg-white">
        <summary class="flex items-center justify-between px-3 py-2 text-[13px] font-medium">Canvia només aquest element
          <svg class="h-3.5 w-3.5 text-ink-400 transition group-open:rotate-180" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m4 6 4 4 4-4"/></svg></summary>
        <div class="grid grid-cols-2 gap-3 border-t border-paper-200 p-3">
          <div class="col-span-2"><span class="etiqueta">Tipografia</span>
            <button type="button" class="selector-font" data-selector-font="element" :disabled="!store.editable"
                    @click="store.crida('triaFontElement', $event.currentTarget)">
              <span class="nom-font" :style="{ fontFamily: FONTS[format.font || estil.font] || '' }">{{ nomFont }}</span>
              <svg class="h-3.5 w-3.5 shrink-0 text-ink-400" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m4 6 4 4 4-4"/></svg>
            </button></div>
          <label><span class="etiqueta">Mida (pt)</span>
            <input type="number" step="0.5" min="3" class="camp py-1.5 text-[13px]" placeholder="estil" :value="format.mida ?? ''"
                   @input="store.canviaFormat('mida', $event.target.value === '' ? '' : Number($event.target.value))"></label>
          <label><span class="etiqueta">Gruix</span>
            <select class="camp py-1.5 text-[14px]" :value="format.pes ?? ''" @change="store.canviaFormat('pes', $event.target.value === '' ? '' : Number($event.target.value))">
              <option value="">(estil)</option>
              <option v-for="g in GRUIXOS" :key="g" :value="g">{{ g }}</option>
            </select></label>
          <label><span class="etiqueta">Interlineat</span>
            <input type="number" step="0.05" class="camp py-1.5 text-[13px]" placeholder="estil" :value="format.interlineat ?? ''"
                   @input="store.canviaFormat('interlineat', $event.target.value === '' ? '' : Number($event.target.value))"></label>
          <label><span class="etiqueta">Espaiat</span>
            <input type="number" step="0.01" class="camp py-1.5 text-[13px]" placeholder="estil" :value="format.espaiat ?? ''"
                   @input="store.canviaFormat('espaiat', $event.target.value === '' ? '' : Number($event.target.value))"></label>
          <label class="flex items-center gap-2 text-[13px]"><input type="checkbox" class="h-4 w-4 accent-vermello-500" :checked="!!format.cursiva"
                 @change="store.canviaFormat('cursiva', $event.target.checked)"> Cursiva</label>
          <div class="flex flex-col gap-1 text-[13px]"><span class="etiqueta mb-0">Color</span>
            <SelectorColor :model-value="format.color || ''" :per-defecte="estil.color" buit="Color de l'estil" :colors="colors"
                           @update:model-value="store.canviaFormat('color', $event)" /></div>
          <button type="button" class="btn btn-fantasma btn-petit col-span-2" @click="store.canviaPropietats({ format: {} })">Torna a l'estil</button>
        </div>
      </details>
      <div v-if="es('text', 'numero', 'index')" class="segmentat w-full" role="group" aria-label="Alineació">
        <button v-for="[v, t] in ALINEACIONS" :key="v" type="button" class="flex-1" :aria-pressed="String((e.alineacio || 'left') === v)"
                :disabled="!store.editable" @click="store.canviaPropietats({ alineacio: v })">{{ t }}</button>
      </div>
    </div>

    <!-- Imatge -->
    <div v-if="es('imatge')" class="flex flex-col gap-3">
      <div class="segmentat w-full" role="group" aria-label="Ajust">
        <button v-for="[v, t] in [['cover', 'Omple'], ['contain', 'Sencera']]" :key="v" type="button" class="flex-1"
                :aria-pressed="String((e.ajust || 'cover') === v)" :disabled="!store.editable" @click="store.canviaPropietats({ ajust: v })">{{ t }}</button>
      </div>
      <label><span class="etiqueta">Cantonades (mm)</span>
        <input type="number" step="0.5" min="0" class="camp py-1.5 font-mono text-[13px]" :value="e.radi" :disabled="!store.editable" @input="numero('radi', $event.target.value)"></label>
      <button type="button" class="btn btn-petit" :disabled="!store.editable" @click="store.crida('canviaImatge')">Canvia la imatge…</button>
    </div>

    <!-- Diagrames d'acords -->
    <div v-if="es('diagrama')" class="flex flex-col gap-3">
      <label><span class="etiqueta">Acord</span>
        <input class="camp py-1.5 font-mono text-[14px]" maxlength="16" autocomplete="off" :value="e.acord" :disabled="!store.editable"
               @input="store.canviaPropietats({ acord: $event.target.value })"></label>
      <p class="text-[12px] leading-snug text-ink-500">Si la cançó es transporta en aquest cançoner, el diagrama també.</p>
    </div>
    <label v-if="es('diagrames')"><span class="etiqueta">Amplada de cada diagrama (mm)</span>
      <input type="number" step="1" min="8" max="60" class="camp py-1.5 font-mono text-[13px]" :value="e.mida" :disabled="!store.editable" @input="numero('mida', $event.target.value)"></label>

    <!-- Codi QR -->
    <div v-if="es('qr')" class="flex flex-col gap-3">
      <label><span class="etiqueta">Vídeo</span>
        <select class="camp py-1.5 text-[14px]" :value="e.video || store.videos[0]?.id || ''" :disabled="!store.editable" @change="store.canviaPropietats({ video: $event.target.value })">
          <option v-if="!store.videos.length" value="">La cançó no té cap vídeo</option>
          <option v-for="(v, i) in store.videos" :key="v.id" :value="v.id">{{ v.titol || `Vídeo ${i + 1}` }}</option>
        </select></label>
      <label class="flex items-center justify-between gap-3 text-[14px]">Títol del vídeo a sota
        <span class="interruptor"><input class="peer sr-only" type="checkbox" :checked="!!e.peu" :disabled="!store.editable"
               @change="store.canviaPropietats({ peu: $event.target.checked })"><span></span></span></label>
      <div class="flex items-center justify-between gap-2 text-[14px]">Color
        <SelectorColor :model-value="e.color || ''" :colors="colors" :disabled="!store.editable" @update:model-value="store.canviaPropietats({ color: $event })" /></div>
      <p v-if="avisQr" class="rounded-md bg-amber-50 px-3 py-2 text-[13px] leading-snug text-amber-900">{{ avisQr }}</p>
    </div>

    <!-- Forma -->
    <div v-if="es('forma')" class="grid grid-cols-2 gap-3">
      <div class="flex flex-col gap-1 text-[14px]"><span class="etiqueta mb-0">Fons</span>
        <SelectorColor :model-value="e.fons || ''" buit="Sense fons" :colors="colors" :disabled="!store.editable" @update:model-value="store.canviaPropietats({ fons: $event })" /></div>
      <div class="flex flex-col gap-1 text-[14px]"><span class="etiqueta mb-0">Vora</span>
        <SelectorColor :model-value="e.vora || ''" buit="Sense vora" :colors="colors" :disabled="!store.editable" @update:model-value="store.canviaPropietats({ vora: $event })" /></div>
      <label><span class="etiqueta">Gruix vora (mm)</span>
        <input type="number" step="0.25" min="0" class="camp py-1.5 font-mono text-[13px]" :value="e.gruix" :disabled="!store.editable" @input="numero('gruix', $event.target.value)"></label>
      <label><span class="etiqueta">Cantonades (mm)</span>
        <input type="number" step="0.5" min="0" class="camp py-1.5 font-mono text-[13px]" :value="e.radi" :disabled="!store.editable" @input="numero('radi', $event.target.value)"></label>
    </div>

    <!-- Posició i mida -->
    <fieldset class="grid grid-cols-2 gap-3 border-t border-paper-300 pt-4">
      <legend class="sr-only">Posició i mida</legend>
      <label v-for="[prop, etiqueta, pas] in POSICIO" :key="prop"><span class="etiqueta">{{ etiqueta }}</span>
        <input type="number" :step="pas" :min="prop === 'w' || prop === 'h' ? 1 : undefined" class="camp py-1.5 font-mono text-[13px]"
               :value="e[prop]" :disabled="!store.editable" @input="numero(prop, $event.target.value)"></label>
      <div><span class="etiqueta">Rotació (°)</span>
        <div class="flex gap-1">
          <input type="number" step="1" class="camp min-w-0 py-1.5 font-mono text-[13px]" :value="e.rotacio" :disabled="!store.editable" aria-label="Rotació (°)"
                 @input="numero('rotacio', $event.target.value)">
          <button type="button" class="btn btn-icona shrink-0" title="Gira 90° a l'esquerra" aria-label="Gira 90° a l'esquerra" :disabled="!store.editable" @click="store.crida('gira', -90)">
            <svg class="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M3 7a5 5 0 1 1 1.5 4.5M3 3v4h4"/></svg></button>
          <button type="button" class="btn btn-icona shrink-0" title="Gira 90° a la dreta" aria-label="Gira 90° a la dreta" :disabled="!store.editable" @click="store.crida('gira', 90)">
            <svg class="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M13 7a5 5 0 1 0-1.5 4.5M13 3v4H9"/></svg></button>
        </div></div>
      <label><span class="etiqueta">Opacitat</span>
        <input type="range" min="0" max="1" step="0.05" class="mt-3 w-full accent-vermello-500" :value="e.opacitat ?? 1" :disabled="!store.editable"
               @input="numero('opacitat', $event.target.value)"></label>
    </fieldset>
    <div class="grid grid-cols-2 gap-2">
      <button type="button" class="btn btn-petit" :disabled="!store.editable" @click="store.crida('centra', 'x')">Centra en horitzontal</button>
      <button type="button" class="btn btn-petit" :disabled="!store.editable" @click="store.crida('centra', 'y')">Centra en vertical</button>
    </div>
    <MouAPagina />
    <button type="button" class="btn btn-fantasma btn-petit" @click="store.crida('desaABiblioteca', 'element')">Desa l'element a la biblioteca</button>
  </div>
</template>
