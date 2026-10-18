<!--
  Vídeos de YouTube de la cançó oberta: afegir-ne (l'adreça la valida el servidor, que també en busca el
  títol), canviar-ne el títol, marcar-los per a l'índex de QR, reordenar-los, treure'ls i mirar-los.
-->
<script setup>
import { onBeforeUnmount, ref } from "vue";
import { confirma } from "@/dialegs.js";
import { useEditorStore } from "@/stores/editor.js";

const store = useEditorStore();
const url = ref("");
const error = ref("");
const afegint = ref(false);
const dialeg = ref(null);
const reproduint = ref(null);

const urlCurta = (v) => `https://youtu.be/${v.video}${v.inici ? `?t=${v.inici}` : ""}`;
const minuts = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

function canvia(id, canvis) {
  store.canviaVideos(store.videos.map((v) => (v.id === id ? { ...v, ...canvis } : v)));
}

function mou(i, desplacament) {
  const nova = [...store.videos];
  [nova[i], nova[i + desplacament]] = [nova[i + desplacament], nova[i]];
  store.canviaVideos(nova);
}

async function treu(v) {
  if (await confirma({ titol: `Treure «${v.titol || urlCurta(v)}»?`, text: "Els QR que hi apunten quedaran buits.", accepta: "Treu-lo", perill: true })) {
    store.canviaVideos(store.videos.filter((x) => x.id !== v.id));
  }
}

async function afegeix() {
  error.value = "";
  afegint.value = true;
  try {
    const r = await fetch(store.urls.video, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ url: url.value }),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.error || "No s'ha pogut afegir el vídeo.");
    if (store.videos.some((x) => x.video === d.video.video && x.inici === d.video.inici)) throw new Error("Aquest vídeo ja hi és.");
    store.canviaVideos([...store.videos, d.video]);
    url.value = "";
  } catch (e) {
    error.value = e.message;
  } finally {
    afegint.value = false;
  }
}

function mira(v) {
  bloquejat.value = false;
  reproduint.value = v;
  dialeg.value.showModal();
}

// Alguns vídeos (sovint música amb drets) no es poden veure fora de YouTube: el reproductor ho diu
// amb un missatge (onError 101 o 150) i aleshores s'ofereix obrir-lo a YouTube.
const bloquejat = ref(false);
const reproductor = ref(null);
const urlReproductor = (v) => `https://www.youtube-nocookie.com/embed/${v.video}?autoplay=1&enablejsapi=1`
  + `&origin=${encodeURIComponent(location.origin)}${v.inici ? `&start=${v.inici}` : ""}`;
const urlYouTube = (v) => `https://www.youtube.com/watch?v=${v.video}${v.inici ? `&t=${v.inici}s` : ""}`;

function escolta() {
  reproductor.value?.contentWindow?.postMessage(JSON.stringify({ event: "listening", id: "videos", channel: "widget" }), "*");
}

function missatge(ev) {
  if (!reproductor.value || ev.source !== reproductor.value.contentWindow) return;
  let d;
  try { d = typeof ev.data === "string" ? JSON.parse(ev.data) : ev.data; } catch { return; }
  if (d?.event === "onError" && [100, 101, 150].includes(Number(d.info))) bloquejat.value = true;
}
window.addEventListener("message", missatge);
onBeforeUnmount(() => window.removeEventListener("message", missatge));

</script>

<template>
  <div class="flex flex-col gap-2">
    <h4 class="text-[13px] font-semibold text-ink-700">Vídeos de YouTube</h4>
    <form v-if="store.editable" class="flex gap-1.5" @submit.prevent="afegeix">
      <input v-model="url" class="camp min-w-0 py-1.5 text-[13px]" placeholder="Enganxa un enllaç de YouTube"
             autocomplete="off" aria-label="Enllaç de YouTube">
      <button class="btn btn-petit shrink-0" :disabled="afegint">Afegeix</button>
    </form>
    <p v-if="error" class="text-[12px] leading-snug text-perill-700" role="alert">{{ error }}</p>
    <ul class="flex flex-col gap-2">
      <li v-for="(v, i) in store.videos" :key="v.id" class="flex gap-2 rounded-md border border-paper-300 bg-white p-1.5">
        <button type="button" class="relative h-12 w-20 shrink-0 overflow-hidden rounded bg-ink-900" title="Mira el vídeo" @click="mira(v)">
          <img :src="`https://i.ytimg.com/vi/${v.video}/mqdefault.jpg`" alt="" loading="lazy" class="h-full w-full object-cover"
               @error="$event.target.remove()">
          <span class="absolute inset-0 flex items-center justify-center text-white drop-shadow" aria-hidden="true">▶</span>
        </button>
        <div class="flex min-w-0 flex-1 flex-col gap-1">
          <input class="camp px-2 py-1 text-[13px]" :value="v.titol" placeholder="Títol del vídeo" aria-label="Títol del vídeo"
                 :readonly="!store.editable" @change="canvia(v.id, { titol: $event.target.value })">
          <div class="flex items-center gap-1 text-[12px] text-ink-500">
            <label class="flex flex-1 items-center gap-1">
              <input type="checkbox" class="h-3.5 w-3.5 accent-accent-500" title="Surt a l'índex de vídeos"
                     :checked="v.inclou_qr" :disabled="!store.editable" @change="canvia(v.id, { inclou_qr: $event.target.checked })">
              <span>A l'índex<template v-if="v.inici"> · des de {{ minuts(v.inici) }}</template></span>
            </label>
            <template v-if="store.editable">
              <button type="button" class="btn btn-fantasma h-6 min-h-0 w-6 px-0 text-[12px]" title="Puja" :disabled="i === 0" @click="mou(i, -1)">↑</button>
              <button type="button" class="btn btn-fantasma h-6 min-h-0 w-6 px-0 text-[12px]" title="Baixa" :disabled="i === store.videos.length - 1" @click="mou(i, 1)">↓</button>
              <button type="button" class="btn btn-perill h-6 min-h-0 w-6 px-0 text-[12px]" title="Treu el vídeo" @click="treu(v)">✕</button>
            </template>
          </div>
        </div>
      </li>
    </ul>
    <p class="text-[12px] leading-snug text-ink-500">Afegeix un element <strong>QR</strong> a la pàgina per posar-ne el codi. Els marcats «a l'índex» surten a l'índex de vídeos, si l'actives a Imprimir.</p>

    <dialog ref="dialeg" class="w-[min(56rem,94vw)] rounded-xl border border-paper-300 bg-ink-900 p-0 text-white shadow-full backdrop:bg-ink-900/60"
            @close="reproduint = null">
      <div class="flex items-center justify-between gap-3 px-4 py-2">
        <h2 class="min-w-0 flex-1 truncate text-[14px] font-medium">{{ reproduint?.titol || (reproduint && urlCurta(reproduint)) }}</h2>
        <a v-if="reproduint" :href="urlYouTube(reproduint)" target="_blank" rel="noopener"
           class="shrink-0 text-[13px] text-white/80 underline underline-offset-4 hover:text-white">Obre a YouTube</a>
        <button type="button" class="btn btn-fantasma btn-icona text-white" aria-label="Tanca" @click="dialeg.close()">
          <svg class="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="m4 4 8 8m0-8-8 8"/></svg>
        </button>
      </div>
      <div class="relative aspect-video w-full bg-black">
        <iframe v-if="reproduint" ref="reproductor" class="h-full w-full" title="Vídeo de YouTube" :src="urlReproductor(reproduint)"
                allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen @load="escolta"></iframe>
        <div v-if="reproduint && bloquejat" class="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-ink-900 p-8 text-center" role="alert">
          <p class="max-w-md text-[15px] leading-snug">El propietari d'aquest vídeo no permet veure'l fora de YouTube (passa sovint amb música amb drets).
            El codi QR funciona igual: obre el vídeo a YouTube.</p>
          <a :href="urlYouTube(reproduint)" target="_blank" rel="noopener" class="btn bg-white text-ink-900 hover:bg-paper-200">Mira'l a YouTube</a>
        </div>
      </div>
    </dialog>
  </div>
</template>
