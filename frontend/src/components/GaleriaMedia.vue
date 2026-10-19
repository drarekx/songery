<!--
  Galeria de mèdia: les imatges de tots els cançoners, en carpetes. S'obre amb obreGaleria() (galeria.js)
  des del botó «Imatge» de l'editor, «Canvia la imatge…» i la imatge dins la lletra. Es pot pujar
  (botó, arrossegant fitxers o ⌘V), crear i reanomenar carpetes, moure-hi imatges (arrossegant-les a
  una carpeta o amb «Mou a…»), reanomenar-les i esborrar les que no es fan servir. Les cançons hi apunten
  per l'id: moure o reanomenar una imatge no canvia cap cançó.
-->
<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { avisa, confirma, pregunta } from "@/dialegs.js";
import { EXTENSIONS, esImatgeAdmesa, galeria, pujaAMedia, tancaGaleria } from "@/galeria.js";

const dialeg = ref(null);
const fitxers = ref(null);
const dades = ref({ carpetes: [], total: 0, sense_carpeta: 0, imatges: [] });
const carpeta = ref(null); // null: tota la mèdia; "": sense carpeta; id: una carpeta
const cerca = ref("");
const triades = ref([]);
const pujades = ref([]);
const arrossegantFitxers = ref(false);
const sobreCarpeta = ref(undefined);
const novaCarpeta = ref(null); // nom de la carpeta que s'està creant
const editantCarpeta = ref(null); // id de la carpeta que es reanomena
const menuMou = ref(false);
const error = ref("");

const MARCA = "application/x-canconer-media";

const nomCarpeta = computed(() => {
  if (carpeta.value === null) return "Tota la mèdia";
  if (carpeta.value === "") return "Sense carpeta";
  return dades.value.carpetes.find((c) => c.id === carpeta.value)?.nom || "Carpeta";
});
const imatgesTriades = computed(() => dades.value.imatges.filter((i) => triades.value.includes(i.id)));
const una = computed(() => (imatgesTriades.value.length === 1 ? imatgesTriades.value[0] : null));
const kb = (bytes) => (bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} kB`);
const usTxt = (i) => (i.usos.length ? `a ${i.usos.length} ${i.usos.length === 1 ? "lloc" : "llocs"}` : "sense ús");

async function api(url, metode = "GET", cos) {
  const r = await fetch(url, { method: metode, headers: cos ? { "Content-Type": "application/json" } : {}, body: cos ? JSON.stringify(cos) : undefined });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(d.error || "No s'ha pogut fer."), { dades: d });
  return d;
}

let peticio = 0;
async function carrega() {
  const n = ++peticio;
  const params = new URLSearchParams();
  if (carpeta.value !== null) params.set("carpeta", carpeta.value);
  if (cerca.value.trim()) params.set("q", cerca.value.trim());
  try {
    const d = await api(`/api/media?${params}`);
    if (n !== peticio) return;
    dades.value = d;
    triades.value = triades.value.filter((id) => d.imatges.some((i) => i.id === id));
  } catch (e) {
    error.value = e.message;
  }
}

watch(() => galeria.oberta, async (oberta) => {
  if (oberta) {
    error.value = "";
    triades.value = [];
    await carrega();
    await nextTick();
    if (!dialeg.value.open) dialeg.value.showModal();
  } else if (dialeg.value?.open) dialeg.value.close();
});
let espera = null;
watch(cerca, () => { clearTimeout(espera); espera = setTimeout(carrega, 150); });

function obreCarpeta(id) {
  carpeta.value = id;
  triades.value = [];
  menuMou.value = false;
  carrega();
}

// ---------------------------------------------------------------- Selecció

function clicImatge(ev, im) {
  if (ev.shiftKey || ev.metaKey || ev.ctrlKey) {
    triades.value = triades.value.includes(im.id) ? triades.value.filter((x) => x !== im.id) : [...triades.value, im.id];
  } else triades.value = [im.id];
  menuMou.value = false;
}

function afegeix(im = una.value) {
  if (!im || !galeria.tria) return;
  const tria = galeria.tria;
  tancaGaleria();
  tria({ id: im.id, url: im.url, nom: im.nom });
}

// ---------------------------------------------------------------- Pujar

async function puja(llista) {
  const desti = carpeta.value || null;
  const tots = [...llista];
  const bons = tots.filter(esImatgeAdmesa);
  if (bons.length < tots.length) error.value = `Només es poden pujar imatges ${EXTENSIONS.join(", ").toUpperCase()}: ${tots.length - bons.length} no s'han pujat.`;
  else error.value = "";
  const noves = [];
  pujades.value = bons.map((f) => ({ nom: f.name || "imatge.png", estat: "esperant" }));
  for (const [i, f] of bons.entries()) {
    pujades.value[i].estat = "pujant";
    try {
      noves.push((await pujaAMedia(f, desti)).id);
      pujades.value[i].estat = "fet";
    } catch (e) {
      pujades.value[i].estat = "error";
      error.value = e.message;
    }
  }
  await carrega();
  if (noves.length) triades.value = noves.slice(-1);
  setTimeout(() => { if (pujades.value.every((p) => p.estat === "fet" || p.estat === "error")) pujades.value = []; }, 1800);
}

function triaFitxers(ev) {
  puja(ev.target.files);
  ev.target.value = "";
}

const portaFitxers = (ev) => [...(ev.dataTransfer?.types || [])].includes("Files");
function dragover(ev) {
  if (!portaFitxers(ev)) return;
  ev.preventDefault();
  arrossegantFitxers.value = true;
}
function dragleave(ev) {
  if (!ev.currentTarget.contains(ev.relatedTarget)) arrossegantFitxers.value = false;
}
function drop(ev) {
  if (!portaFitxers(ev)) return;
  ev.preventDefault();
  arrossegantFitxers.value = false;
  puja(ev.dataTransfer.files);
}

function enganxa(ev) {
  if (!galeria.oberta || ev.target.closest?.("input, textarea")) return;
  const imatges = [...(ev.clipboardData?.files || [])].filter((f) => f.type.startsWith("image/"));
  if (!imatges.length) return;
  ev.preventDefault();
  ev.stopImmediatePropagation(); // que no l'enganxi també l'editor
  puja(imatges);
}

// ---------------------------------------------------------------- Carpetes

async function creaCarpeta() {
  const nom = (novaCarpeta.value || "").trim();
  novaCarpeta.value = null;
  if (!nom) return null;
  try {
    const { id } = await api("/api/media/carpetes", "POST", { nom });
    await carrega();
    return id;
  } catch (e) {
    error.value = e.message;
    return null;
  }
}

async function reanomenaCarpeta(c, nom) {
  editantCarpeta.value = null;
  if (!nom.trim() || nom.trim() === c.nom) return;
  try {
    await api(`/api/media/carpetes/${c.id}`, "PUT", { nom });
    await carrega();
  } catch (e) { error.value = e.message; }
}

async function esborraCarpeta(c) {
  if (!await confirma({ titol: `Esborrar la carpeta «${c.nom}»?`, accepta: "Esborra-la", perill: true,
    text: c.n ? `Les ${c.n} imatges que té no s'esborren: passen a «Sense carpeta».` : "És buida." })) return;
  await api(`/api/media/carpetes/${c.id}`, "DELETE");
  if (carpeta.value === c.id) carpeta.value = null;
  await carrega();
}

// ---------------------------------------------------------------- Moure, reanomenar i esborrar imatges

async function mou(ids, desti) {
  menuMou.value = false;
  if (!ids.length) return;
  try {
    await api("/api/media/imatges", "PUT", { ids, carpeta: desti || "" });
    triades.value = [];
    await carrega();
  } catch (e) { error.value = e.message; }
}

async function mouACarpetaNova() {
  menuMou.value = false;
  const nom = await pregunta({ titol: "Carpeta nova", text: "Les imatges seleccionades s'hi mouran.", valor: "", placeholder: "Nom de la carpeta", accepta: "Crea-la i mou-les" });
  if (!nom?.trim()) return;
  novaCarpeta.value = nom;
  const id = await creaCarpeta();
  if (id) await mou([...triades.value], id);
}

function arrossegaImatge(ev, im) {
  if (!triades.value.includes(im.id)) triades.value = [im.id];
  ev.dataTransfer.setData(MARCA, JSON.stringify(triades.value));
  ev.dataTransfer.effectAllowed = "move";
}
const portaImatges = (ev) => [...(ev.dataTransfer?.types || [])].includes(MARCA);
function sobre(ev, id) {
  if (!portaImatges(ev)) return;
  ev.preventDefault();
  sobreCarpeta.value = id;
}
function deixaACarpeta(ev, id) {
  if (!portaImatges(ev)) return;
  ev.preventDefault();
  sobreCarpeta.value = undefined;
  mou(JSON.parse(ev.dataTransfer.getData(MARCA) || "[]"), id);
}

async function reanomenaImatge() {
  const im = una.value;
  if (!im) return;
  const nom = await pregunta({ titol: "Reanomena la imatge", valor: im.nom, accepta: "Reanomena-la" });
  if (!nom?.trim() || nom.trim() === im.nom) return;
  try {
    await api(`/api/media/imatges/${im.id}`, "PUT", { nom });
    await carrega();
  } catch (e) { error.value = e.message; }
}

async function esborra() {
  const llista = imatgesTriades.value;
  const enUs = llista.filter((i) => i.usos.length);
  if (enUs.length) {
    const im = enUs[0];
    return avisa({ titol: enUs.length === 1 ? `«${im.nom}» es fa servir` : `${enUs.length} imatges es fan servir`,
      text: `No es pot esborrar una imatge que surt en alguna cançó o cançoner. ${im.nom}: ${im.usos.slice(0, 4).join(", ")}${im.usos.length > 4 ? "…" : ""}.` });
  }
  if (!await confirma({ titol: llista.length === 1 ? `Esborrar «${llista[0].nom}»?` : `Esborrar ${llista.length} imatges?`,
    text: "No es fan servir a cap cançó ni cançoner. No es pot desfer.", accepta: "Esborra", perill: true })) return;
  for (const im of llista) {
    try { await api(`/api/media/imatges/${im.id}`, "DELETE"); } catch (e) { error.value = e.message; }
  }
  triades.value = [];
  await carrega();
}

// ---------------------------------------------------------------- Teclat

function tecla(ev) {
  if (!galeria.oberta) return;
  if (ev.key === "Escape" && menuMou.value) {
    ev.preventDefault();
    menuMou.value = false;
  } else if (ev.key === "Enter" && una.value && galeria.tria && !ev.target.closest("input, button, textarea")) {
    ev.preventDefault();
    afegeix();
  }
}

onMounted(() => {
  document.addEventListener("paste", enganxa, true);
  document.addEventListener("keydown", tecla);
});
onBeforeUnmount(() => {
  document.removeEventListener("paste", enganxa, true);
  document.removeEventListener("keydown", tecla);
  clearTimeout(espera);
});
</script>

<template>
  <dialog ref="dialeg" class="galeria-media" aria-labelledby="titol-galeria" @close="tancaGaleria" @cancel.prevent="tancaGaleria"
          @dragover="dragover" @dragleave="dragleave" @drop="drop">
    <header class="flex flex-wrap items-center gap-3 border-b border-paper-300 bg-white px-5 py-3.5">
      <div class="min-w-0 flex-1">
        <h2 id="titol-galeria" class="font-display text-2xl font-medium tracking-tight">Mèdia</h2>
        <p class="text-[13px] text-ink-500">Les imatges són de tots els cançoners: puja-les un cop i fes-les servir on vulguis.</p>
      </div>
      <label class="flex h-9 w-56 items-center gap-2 rounded-lg border border-paper-300 bg-white px-3 text-ink-500 focus-within:border-ink-400">
        <svg class="h-4 w-4 shrink-0" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="9" cy="9" r="5.5"/><path d="m13 13 4 4"/></svg>
        <input v-model="cerca" type="search" placeholder="Cerca imatges" aria-label="Cerca imatges" class="w-full bg-transparent text-[14px] text-ink-900 outline-none">
      </label>
      <button type="button" class="btn btn-primari" @click="fitxers.click()">
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M10 14V4m0 0-4 4m4-4 4 4M4 16h12"/></svg>
        Puja imatges
      </button>
      <input ref="fitxers" type="file" multiple class="hidden" accept=".png,.jpg,.jpeg,.webp,.gif,image/png,image/jpeg,image/webp,image/gif" @change="triaFitxers">
      <button type="button" class="btn btn-fantasma btn-icona" aria-label="Tanca" @click="tancaGaleria">
        <svg class="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m4 4 8 8m0-8-8 8"/></svg>
      </button>
    </header>

    <div class="flex min-h-0 flex-1">
      <!-- Carpetes -->
      <nav aria-label="Carpetes" class="flex w-56 shrink-0 flex-col gap-0.5 overflow-y-auto border-r border-paper-300 p-3">
        <span class="px-2.5 pb-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500">Carpetes</span>
        <button type="button" class="carpeta-media" :aria-current="carpeta === null ? 'true' : undefined" @click="obreCarpeta(null)">
          <span class="flex-1 truncate">Tota la mèdia</span><span class="comptador">{{ dades.total }}</span></button>
        <button type="button" class="carpeta-media" :class="{ desti: sobreCarpeta === '' }" :aria-current="carpeta === '' ? 'true' : undefined"
                @click="obreCarpeta('')" @dragover="sobre($event, '')" @dragleave="sobreCarpeta = undefined" @drop="deixaACarpeta($event, '')">
          <span class="flex-1 truncate">Sense carpeta</span><span class="comptador">{{ dades.sense_carpeta }}</span></button>
        <template v-for="c in dades.carpetes" :key="c.id">
          <label v-if="editantCarpeta === c.id" class="carpeta-media editant">
            <span class="sr-only">Nom de la carpeta</span>
            <input class="min-w-0 flex-1 bg-transparent font-semibold outline-none" :value="c.nom" maxlength="80" autofocus
                   @keydown.enter.prevent="reanomenaCarpeta(c, $event.target.value)" @keydown.esc.prevent.stop="editantCarpeta = null"
                   @blur="reanomenaCarpeta(c, $event.target.value)">
          </label>
          <div v-else class="group relative">
            <button type="button" class="carpeta-media w-full" :class="{ desti: sobreCarpeta === c.id }" :aria-current="carpeta === c.id ? 'true' : undefined"
                    title="Doble clic per reanomenar-la" @click="obreCarpeta(c.id)" @dblclick="editantCarpeta = c.id"
                    @dragover="sobre($event, c.id)" @dragleave="sobreCarpeta = undefined" @drop="deixaACarpeta($event, c.id)">
              <svg class="h-4 w-4 shrink-0" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M3 6.5A1.5 1.5 0 0 1 4.5 5H8l1.5 2h6A1.5 1.5 0 0 1 17 8.5v6a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 3 14.5v-8Z"/></svg>
              <span class="flex-1 truncate text-left">{{ c.nom }}</span><span class="comptador group-hover:opacity-0">{{ c.n }}</span>
            </button>
            <span class="absolute right-1 top-1/2 hidden -translate-y-1/2 gap-0.5 group-focus-within:flex group-hover:flex">
              <button type="button" class="accio-carpeta" :aria-label="`Reanomena «${c.nom}»`" @click="editantCarpeta = c.id">
                <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="m4 16 1-4 8-8 3 3-8 8-4 1Z"/></svg></button>
              <button type="button" class="accio-carpeta hover:text-perill-600" :aria-label="`Esborra «${c.nom}»`" @click="esborraCarpeta(c)">
                <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M4 6h12M8 6V4h4v2M6 6l.8 11h6.4L14 6"/></svg></button>
            </span>
          </div>
        </template>
        <label v-if="novaCarpeta !== null" class="carpeta-media editant">
          <span class="sr-only">Nom de la carpeta nova</span>
          <input v-model="novaCarpeta" class="min-w-0 flex-1 bg-transparent font-semibold outline-none" placeholder="Nom de la carpeta" maxlength="80" autofocus
                 @keydown.enter.prevent="creaCarpeta" @keydown.esc.prevent.stop="novaCarpeta = null" @blur="creaCarpeta">
        </label>
        <button v-else type="button" class="mt-2 flex h-9 items-center gap-2.5 rounded-lg border border-dashed border-ink-300 px-2.5 text-[13.5px] font-medium text-ink-700 hover:border-ink-500" @click="novaCarpeta = ''">
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M10 5v10M5 10h10"/></svg>
          Carpeta nova
        </button>
        <p v-if="dades.carpetes.length" class="mt-3 px-2.5 text-[12px] leading-snug text-ink-500">Arrossega imatges a una carpeta per moure-les. Les cançons que les fan servir no canvien.</p>
      </nav>

      <!-- Imatges -->
      <div class="relative flex min-w-0 flex-1 flex-col">
        <div class="flex flex-wrap items-center gap-2 px-5 py-3 text-[14px]">
          <span class="font-semibold">{{ nomCarpeta }}</span>
          <span class="ml-auto text-[12.5px] text-ink-500">Arrossega imatges aquí o enganxa-les amb <kbd class="tecla">⌘V</kbd></span>
        </div>
        <p v-if="error" class="avis mx-5 mb-2" role="alert"><span aria-hidden="true">⚠</span><span>{{ error }}</span></p>
        <ul v-if="dades.imatges.length" class="grid flex-1 auto-rows-min grid-cols-[repeat(auto-fill,minmax(10.5rem,1fr))] gap-4 overflow-y-auto px-5 pb-5" aria-label="Imatges">
          <li v-for="im in dades.imatges" :key="im.id">
            <button type="button" class="imatge-media" :aria-pressed="String(triades.includes(im.id))" draggable="true"
                    @click="clicImatge($event, im)" @dblclick="afegeix(im)" @dragstart="arrossegaImatge($event, im)">
              <span class="relative flex aspect-[4/3] items-center justify-center overflow-hidden bg-paper-200">
                <img :src="im.url" alt="" loading="lazy" class="h-full w-full object-contain">
                <span v-if="triades.includes(im.id)" class="absolute right-2 top-2 flex h-6 w-6 items-center justify-center rounded-full bg-ink-900 text-white">
                  <svg class="h-3 w-3" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="m3.5 8.5 3 3 6-7"/></svg>
                </span>
              </span>
              <span class="flex flex-col gap-0.5 px-2.5 pb-2.5 pt-2 text-left">
                <span class="truncate text-[13px] font-medium">{{ im.nom }}</span>
                <span class="font-mono text-[11px] text-ink-500">{{ kb(im.mida) }} · {{ usTxt(im) }}</span>
              </span>
            </button>
          </li>
        </ul>
        <div v-else class="mx-5 mb-5 flex flex-1 flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-ink-300 bg-white p-8 text-center">
          <p class="font-display text-2xl font-medium">{{ cerca ? "Cap imatge coincideix" : "Aquesta carpeta és buida" }}</p>
          <p v-if="!cerca" class="max-w-sm text-[14px] leading-relaxed text-ink-500">Arrossega-hi imatges, enganxa'n una amb <kbd class="tecla">⌘V</kbd> o tria-les de l'ordinador. PNG, JPG, WEBP o GIF.</p>
          <button v-if="!cerca" type="button" class="btn" @click="fitxers.click()">Tria fitxers…</button>
        </div>

        <!-- Zona on es deixen anar els fitxers -->
        <div v-if="arrossegantFitxers" class="pointer-events-none absolute inset-4 flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-ink-900 bg-white/95 text-center">
          <span class="flex h-16 w-16 items-center justify-center rounded-full bg-ink-900 text-white">
            <svg class="h-7 w-7" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><path d="M10 14V4m0 0-4 4m4-4 4 4M4 16h12"/></svg>
          </span>
          <p class="font-display text-[28px] font-medium">Deixa-les anar a «{{ carpeta ? nomCarpeta : "Sense carpeta" }}»</p>
          <p class="max-w-sm text-[14px] text-ink-500">Només imatges PNG, JPG, WEBP o GIF.</p>
        </div>

        <!-- Pujades en curs -->
        <div v-if="pujades.length" role="status" class="absolute bottom-4 right-5 w-80 overflow-hidden rounded-xl border border-paper-300 bg-white shadow-full">
          <div class="flex items-center justify-between border-b border-paper-200 px-3.5 py-2.5 text-[13px] font-semibold">
            Pujant {{ pujades.length }} {{ pujades.length === 1 ? "imatge" : "imatges" }}
            <span class="font-mono text-[11.5px] font-normal text-ink-500">{{ pujades.filter((p) => p.estat === "fet").length }} de {{ pujades.length }}</span>
          </div>
          <div v-for="(p, i) in pujades" :key="i" class="flex items-center justify-between gap-2 px-3.5 py-2 text-[12.5px]">
            <span class="truncate">{{ p.nom }}</span>
            <span class="font-mono text-[11px]" :class="p.estat === 'error' ? 'text-perill-600' : 'text-ink-500'">{{ p.estat }}</span>
          </div>
        </div>
      </div>
    </div>

    <footer class="flex flex-wrap items-center gap-3 border-t border-paper-300 bg-white px-5 py-3">
      <span v-if="una" class="flex min-w-0 items-baseline gap-2 text-[14px]">
        <strong class="truncate font-semibold">{{ una.nom }}</strong>
        <span class="shrink-0 text-ink-500" :title="una.usos.join(', ')">· {{ usTxt(una) }}</span>
      </span>
      <span v-else-if="triades.length" class="text-[14px]"><strong class="font-semibold">{{ triades.length }} seleccionades</strong>
        <span class="text-ink-500"> · ⇧ clic per triar-ne més</span></span>
      <span v-else class="text-[14px] text-ink-500">{{ galeria.tria ? "Tria una imatge (o fes-hi doble clic)." : "Tria imatges per moure-les o esborrar-les." }}</span>
      <span class="flex-1"></span>
      <template v-if="triades.length">
        <div class="relative">
          <button type="button" class="btn" :aria-expanded="String(menuMou)" @click="menuMou = !menuMou">Mou a…</button>
          <div v-if="menuMou" role="menu" aria-label="Mou a" class="menu-mou">
            <span class="px-2.5 pb-1 pt-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-500">Mou a</span>
            <button type="button" role="menuitem" class="menu-context-item" @click="mou([...triades], '')">Sense carpeta</button>
            <button v-for="c in dades.carpetes" :key="c.id" type="button" role="menuitem" class="menu-context-item" @click="mou([...triades], c.id)">{{ c.nom }}</button>
            <div class="menu-context-separador" role="separator"></div>
            <button type="button" role="menuitem" class="menu-context-item" @click="mouACarpetaNova">Carpeta nova…</button>
          </div>
        </div>
        <button v-if="una" type="button" class="btn" @click="reanomenaImatge">Reanomena…</button>
        <button type="button" class="btn btn-perill" @click="esborra">Esborra…</button>
      </template>
      <button type="button" class="btn" @click="tancaGaleria">{{ galeria.tria ? "Cancel·la" : "Tanca" }}</button>
      <button v-if="galeria.tria" type="button" class="btn btn-primari" :disabled="!una" @click="afegeix()">{{ galeria.titol }}</button>
    </footer>
  </dialog>
</template>
