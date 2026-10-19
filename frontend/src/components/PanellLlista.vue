<!--
  Columna de l'esquerra de l'editor: tot el llibret, les pàgines especials, les cançons i pàgines
  lliures (amb «surt al PDF», l'ordre i on surten) i les pàgines mestres.
-->
<script setup>
import { computed, ref } from "vue";
import { useEditorStore } from "@/stores/editor.js";

const store = useEditorStore();
const ESPECIALS = [["portada", "Portada"], ["index", "Índex"], ["acords", "Pàgina d'acords"], ["acords_dos", "Pàgina d'acords (guitarra i ukulele)"], ["index_qr", "Índex de vídeos (QR)"], ["contraportada", "Contraportada"]];

// Mentre s'arrossega una cançó, l'ordre provisional és aquí; en deixar-la, es desa.
const ordreProvisional = ref(null);
const arrossegada = ref(null);
const llistaEl = ref(null);
const cancons = computed(() => {
  if (!ordreProvisional.value) return store.llista.cancons;
  return ordreProvisional.value.map((id) => store.llista.cancons.find((c) => c.id === id)).filter(Boolean);
});
// Cerca per títol o autor (sense tenir en compte accents ni majúscules). Mentre es filtra no es pot
// reordenar arrossegant, perquè l'ordre que es veu no és el de tot el cançoner.
const filtre = ref("");
const normalitza = (text) => String(text || "").normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
const filtrant = computed(() => !!filtre.value.trim());
const visibles = computed(() => {
  const q = normalitza(filtre.value.trim());
  return q ? cancons.value.filter((c) => normalitza(`${c.titol} ${c.autor || ""}`).includes(q)) : cancons.value;
});
const index = (c) => store.llista.cancons.findIndex((x) => x.id === c.id);
function teclaCerca(ev) {
  if (ev.key === "Escape") filtre.value = "";
  else if (ev.key === "Enter" && visibles.value.length) obre("canco", visibles.value[0].id);
}

const compte = computed(() => {
  const totes = store.llista.cancons;
  return totes.length ? `${totes.filter((c) => c.inclosa).length}/${totes.length}` : "";
});

const actiu = (clau) => store.llista.obert === clau;
// La portada i la contraportada hi són sempre; l'índex, la pàgina d'acords i l'índex de vídeos, només si
// estan activats (a Opcions o a Imprimir). Desactivar-los no n'esborra el disseny.
const especials = computed(() => ESPECIALS.filter(([nom]) => store.llista.especials?.[nom] !== false));
const pagines = (c) => (c.pagines.length > 1 ? `pàg. ${c.pagines[0]}–${c.pagines.at(-1)}` : `pàg. ${c.pagines[0]}`);
const obre = (tipus, id) => store.crida("obre", tipus === "llibre" ? { tipus } : { tipus, id });

/** Menú del botó dret d'una cançó o pàgina lliure. */
function menuCanco(ev, c, i) {
  const n = store.llista.cancons.length;
  const obreIFes = async (accio) => { await obre("canco", c.id); store.crida(accio); };
  store.obreMenu(ev.clientX, ev.clientY, [
    { seccio: c.titol || "Sense títol" },
    { text: "Obre", fes: () => obre("canco", c.id) },
    { separador: true },
    { text: "Surt al PDF", marcat: c.inclosa, fes: () => store.crida("canviaEntrada", c.id, { inclosa: !c.inclosa }) },
    ...(c.tipus === "pagina" ? [] : [{ text: "Comença sempre a l'esquerra", marcat: c.inici !== "qualsevol",
      fes: () => store.crida("canviaEntrada", c.id, { inici: c.inici === "qualsevol" ? "esquerra" : "qualsevol" }) }]),
    { separador: true },
    { text: "Mou amunt", desactivat: i === 0, fes: () => store.crida("mouEntrada", c.id, -1) },
    { text: "Mou avall", desactivat: i === n - 1, fes: () => store.crida("mouEntrada", c.id, 1) },
    { text: "Versions i historial…", fes: () => obreIFes("obreHistorial") },
    { separador: true },
    { text: "Treu del cançoner…", fes: () => obreIFes("treuCanco") },
    { text: c.usos > 1 ? "Elimina (també és en altres cançoners)" : "Elimina la cançó…", perill: true, desactivat: c.usos > 1,
      fes: () => store.crida("eliminaCanco", c.id) },
  ]);
}

/** Menú del botó dret d'una pàgina mestra. */
function menuMestra(ev, m) {
  const obreIFes = async (accio) => { await obre("mestra", m.id); store.crida(accio); };
  store.obreMenu(ev.clientX, ev.clientY, [
    { seccio: m.nom },
    { text: "Obre", fes: () => obre("mestra", m.id) },
    { text: "Duplica", fes: () => obreIFes("duplicaMestra") },
    ...(m.id === "estandard" ? [] : [{ separador: true }, { text: "Esborra…", perill: true, fes: () => obreIFes("esborraMestra") }]),
  ]);
}

function comencaArrossegar(ev, c) {
  arrossegada.value = c.id;
  ordreProvisional.value = store.llista.cancons.map((x) => x.id);
  ev.currentTarget.setPointerCapture?.(ev.pointerId);
  ev.preventDefault();
}

function arrossega(ev) {
  if (!arrossegada.value) return;
  const files = [...llistaEl.value.children].filter((li) => li.dataset.id !== arrossegada.value);
  const seguent = files.find((li) => ev.clientY < li.getBoundingClientRect().top + li.offsetHeight / 2);
  const ordre = ordreProvisional.value.filter((id) => id !== arrossegada.value);
  ordre.splice(seguent ? ordre.indexOf(seguent.dataset.id) : ordre.length, 0, arrossegada.value);
  ordreProvisional.value = ordre;
}

function deixa() {
  if (!arrossegada.value) return;
  const ordre = ordreProvisional.value;
  arrossegada.value = null;
  ordreProvisional.value = null;
  if (ordre.join() !== store.llista.cancons.map((c) => c.id).join()) store.crida("desaOrdre", ordre);
}
</script>

<template>
  <!-- Fora d'un cançoner (editant una cançó des de la biblioteca), només la cançó i d'on ve el disseny. -->
  <div v-if="store.modeCanco" class="flex flex-col gap-3 px-4 pt-4 text-[13px] leading-snug text-ink-700">
    <h2 class="titol-seccio-llista p-0">Cançó</h2>
    <p class="font-display text-[17px] font-medium text-ink-900">{{ store.llista.cancons[0]?.titol || "Sense títol" }}</p>
    <p class="text-ink-500">L'edites fora de cap cançoner: els canvis es desen a la cançó i els veuen tots els cançoners que la fan servir.</p>
    <p class="text-ink-500">Disseny: {{ store.dissenyDe ? `el del cançoner «${store.dissenyDe}»` : "el de per defecte" }} (aquí no es pot canviar).</p>
    <a :href="`/biblioteca/${store.llista.cancons[0]?.id}`" class="btn btn-petit justify-start">Fitxa i versions de la cançó</a>
  </div>
  <div v-else class="flex flex-col">
    <div class="px-2 pt-3">
      <button type="button" class="item-llista w-full" :aria-current="String(actiu('llibre'))" @click="obre('llibre')">
        <svg class="h-4 w-4 shrink-0 text-ink-400" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M2 3h5v10H2zM9 3h5v10H9z"/></svg>
        <span class="flex-1 text-left">Tot el llibret</span>
        <span v-if="store.llista.total" class="font-mono text-[11px] text-ink-400">{{ store.llista.total }} pàg.</span>
      </button>
    </div>
    <h2 class="titol-seccio-llista">Pàgines del llibret</h2>
    <div class="flex flex-col gap-0.5 px-2">
      <button v-for="[nom, text] in especials" :key="nom" type="button" class="item-llista" :aria-current="String(actiu(`especial:${nom}`))" @click="obre('especial', nom)">
        <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-ink-300" aria-hidden="true"></span><span class="flex-1 text-left">{{ text }}</span>
      </button>
    </div>

    <div class="flex items-center justify-between px-4 pt-5">
      <h2 class="titol-seccio-llista p-0">Cançons i pàgines <span class="ml-1 font-mono normal-case tracking-normal text-ink-300">{{ compte }}</span></h2>
    </div>
    <div v-if="store.llista.cancons.length > 5" class="px-3 pt-2">
      <label class="sr-only" for="cerca-llista">Cerca una cançó</label>
      <input id="cerca-llista" v-model="filtre" type="search" class="camp py-1 text-[13px]" placeholder="Cerca per títol o autor…"
             autocomplete="off" @keydown="teclaCerca">
    </div>
    <p v-if="filtrant && !visibles.length" class="px-4 py-2 text-[12.5px] text-ink-500">Cap cançó coincideix amb «{{ filtre.trim() }}».</p>
    <ol ref="llistaEl" class="llista-ev flex flex-col gap-0.5 px-2 pt-1" @pointermove="arrossega" @pointerup="deixa" @pointercancel="deixa">
      <li v-for="c in visibles" :key="c.id" :data-id="c.id" @contextmenu.prevent="menuCanco($event, c, index(c))"
          class="group relative flex items-center rounded-md transition"
          :class="[actiu(`canco:${c.id}`) ? 'bg-white shadow-suau ring-1 ring-paper-300' : 'hover:bg-paper-200/70', { 'opacity-60': !c.inclosa, arrossegant: arrossegada === c.id }]">
        <span v-if="actiu(`canco:${c.id}`)" class="absolute inset-y-2 left-0 w-0.5 rounded-full bg-accent-500" aria-hidden="true"></span>
        <span v-if="!filtrant" class="nansa flex w-4 shrink-0 cursor-grab touch-none select-none items-center justify-center self-stretch text-ink-300 opacity-0 transition group-hover:opacity-100 max-lg:opacity-100"
              title="Arrossega per reordenar" aria-hidden="true" @pointerdown="comencaArrossegar($event, c)">⠿</span>
        <span v-else class="w-2 shrink-0" aria-hidden="true"></span>
        <input type="checkbox" class="h-3.5 w-3.5 shrink-0 cursor-pointer accent-accent-500" title="Surt al PDF" :aria-label="`«${c.titol || 'Sense títol'}» surt al PDF`"
               :checked="c.inclosa" @change="store.crida('canviaEntrada', c.id, { inclosa: $event.target.checked })">
        <button type="button" class="flex min-w-0 flex-1 items-center gap-2 py-1.5 pl-2 pr-1 text-left" @click="obre('canco', c.id)">
          <span class="flex min-w-0 flex-1 flex-col">
            <span class="truncate text-[13.5px]" :class="[actiu(`canco:${c.id}`) ? 'font-semibold text-ink-900' : 'font-medium text-ink-700', { italic: c.tipus === 'pagina' }]">
              {{ c.tipus === "pagina" ? "▫ " : "" }}{{ c.titol || "Sense títol" }}</span>
            <span class="flex items-center gap-1.5 text-[11px] text-ink-400">
              <span v-if="c.pagines.length">{{ pagines(c) }}</span>
              <span v-else-if="!c.inclosa">fora del PDF</span>
              <span v-if="c.inici === 'qualsevol' && c.tipus !== 'pagina'" title="Comença on toqui">↦</span>
              <span v-if="c.versio_numero" class="rounded bg-sky-100 px-1 font-mono text-[10px] text-sky-900" title="Versió fixada">v{{ c.versio_numero }}{{ c.desfasada ? " ↑" : "" }}</span>
              <span v-if="c.usos > 1" title="És en més d'un cançoner">{{ c.usos }}×</span>
              <span v-if="c.buida" class="rounded bg-amber-100 px-1 text-[10px] font-medium text-amber-900"
                    title="Aquesta pàgina lliure no té res: al PDF surt en blanc">buida</span>
            </span>
          </span>
        </button>
        <span v-if="!filtrant" class="flex shrink-0 flex-col opacity-0 transition focus-within:opacity-100 group-hover:opacity-100 max-lg:opacity-100">
          <button v-for="[d, cami, titol] in [[-1, 'M4 10l4-4 4 4', 'Mou amunt'], [1, 'M4 6l4 4 4-4', 'Mou avall']]" :key="d" type="button"
                  class="flex h-4 w-5 items-center justify-center rounded text-ink-400 hover:bg-paper-300 hover:text-ink-900 disabled:invisible"
                  :title="titol" :aria-label="titol" :disabled="(d < 0 && index(c) === 0) || (d > 0 && index(c) === cancons.length - 1)"
                  @click="store.crida('mouEntrada', c.id, d)">
            <svg class="h-3 w-3" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path :d="cami"/></svg>
          </button>
        </span>
      </li>
    </ol>
    <div class="grid grid-cols-3 gap-1.5 px-3 pb-2 pt-2">
      <button type="button" class="btn btn-primari btn-petit px-1" title="Cançó nova" @click="store.crida('creaEntrada', 'canco')">+ Cançó</button>
      <button type="button" class="btn btn-petit px-1" title="Pàgina lliure: dedicatòria, il·lustració…" @click="store.crida('creaEntrada', 'pagina')">+ Pàgina</button>
      <button type="button" class="btn btn-petit px-1" title="Enganxa una cançó amb acords o afegeix-ne de la biblioteca" @click="store.crida('obreImporta')">Importa</button>
    </div>

    <div class="flex items-center justify-between px-4 pt-4">
      <h2 class="titol-seccio-llista p-0">Pàgines mestres</h2>
      <div class="flex gap-0.5">
        <button type="button" class="btn btn-fantasma btn-icona h-6 min-h-0 w-6" title="Copia mestres d'un altre cançoner" aria-label="Copia mestres d'un altre cançoner" @click="store.crida('copiaMestres')">
          <svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="5" y="5" width="8.5" height="8.5" rx="1.5"/><path d="M10.5 5V3.5A1.5 1.5 0 0 0 9 2H3.5A1.5 1.5 0 0 0 2 3.5V9a1.5 1.5 0 0 0 1.5 1.5H5"/></svg>
        </button>
        <button type="button" class="btn btn-fantasma btn-icona h-6 min-h-0 w-6" title="Nova pàgina mestra" aria-label="Nova pàgina mestra" @click="store.crida('novaMestra')">+</button>
      </div>
    </div>
    <ul class="flex flex-col gap-0.5 px-2 pb-4 pt-1">
      <li v-for="m in store.mestres" :key="m.id" @contextmenu.prevent="menuMestra($event, m)">
        <button type="button" class="item-llista w-full" :aria-current="String(actiu(`mestra:${m.id}`))" @click="obre('mestra', m.id)">
          <span class="flex h-4 w-4 shrink-0 items-center justify-center rounded bg-paper-300 font-mono text-[9px] font-bold text-ink-700" aria-hidden="true">M</span>
          <span class="flex-1 truncate text-left">{{ m.nom }}</span>
        </button>
      </li>
    </ul>
  </div>
</template>
