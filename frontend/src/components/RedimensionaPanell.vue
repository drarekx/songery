<!--
  Nansa per canviar l'amplada d'una columna arrossegant-la (o amb les fletxes del teclat). L'amplada
  és una variable CSS de l'element `objectiu` i es recorda a les preferències de l'usuari (`clau`).
  Doble clic: torna a l'amplada per defecte. La nansa va a la vora esquerra de la columna.
-->
<script setup>
import { onBeforeUnmount, ref } from "vue";
import { usePreferencies } from "@/stores/preferencies.js";

const props = defineProps({
  objectiu: { type: String, required: true }, // selector de l'element amb la variable
  variable: { type: String, required: true }, // p. ex. "--ample-propietats"
  clau: { type: String, required: true }, // preferència on es desa
  minim: { type: Number, default: 260 },
  maxim: { type: Number, default: 720 },
  perDefecte: { type: Number, default: 320 },
  alAcabar: { type: Function, default: null }, // en deixar d'arrossegar (p. ex. redibuixar)
  /** On és la columna respecte de la nansa: "dreta" (la nansa és a la seva vora esquerra) o
   *  "esquerra" (a la seva vora dreta: arrossegant cap a la dreta, es fa més ampla). */
  columna: { type: String, default: "dreta" },
});

const preferencies = usePreferencies();
const ample = ref(preferencies.llegeix(props.clau, props.perDefecte));
const arrossegant = ref(false);
let inici = null;

const limita = (v) => Math.round(Math.min(props.maxim, Math.max(props.minim, v)));
const element = () => document.querySelector(props.objectiu);

function aplica(v) {
  ample.value = limita(v);
  element()?.style.setProperty(props.variable, `${ample.value}px`);
}

function desa() {
  preferencies.posa(props.clau, ample.value);
  props.alAcabar?.();
}

function baixa(ev) {
  if (ev.button !== 0) return;
  ev.preventDefault();
  inici = { x: ev.clientX, ample: ample.value };
  arrossegant.value = true;
  document.body.classList.add("redimensionant");
  ev.target.setPointerCapture?.(ev.pointerId);
}

function mou(ev) {
  if (!inici) return;
  const dx = ev.clientX - inici.x;
  aplica(inici.ample + (props.columna === "dreta" ? -dx : dx)); // cap a fora de la columna, més ampla
}

function deixa() {
  if (!inici) return;
  inici = null;
  arrossegant.value = false;
  document.body.classList.remove("redimensionant");
  desa();
}

function teclat(ev) {
  const pas = (ev.shiftKey ? 64 : 16) * (props.columna === "dreta" ? 1 : -1);
  if (ev.key === "ArrowLeft") aplica(ample.value + pas);
  else if (ev.key === "ArrowRight") aplica(ample.value - pas);
  else if (ev.key === "Home") aplica(props.maxim);
  else if (ev.key === "End") aplica(props.minim);
  else return;
  ev.preventDefault();
  desa();
}

function restableix() {
  aplica(props.perDefecte);
  preferencies.posa(props.clau, null);
  props.alAcabar?.();
}

onBeforeUnmount(() => document.body.classList.remove("redimensionant"));
</script>

<template>
  <div class="nansa-columna" :class="{ actiu: arrossegant }" role="separator" aria-orientation="vertical"
       aria-label="Amplada de la columna" :aria-valuenow="ample" :aria-valuemin="minim" :aria-valuemax="maxim" tabindex="0"
       title="Arrossega per canviar l'amplada (doble clic: amplada per defecte)"
       @pointerdown="baixa" @pointermove="mou" @pointerup="deixa" @pointercancel="deixa" @dblclick="restableix" @keydown="teclat"></div>
</template>
