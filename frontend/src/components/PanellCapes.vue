<!--
  Pestanya «Capes»: tots els elements de les pàgines obertes, del de davant al del fons. Passar-hi el
  ratolí els ressalta a la pàgina; clicar-los els selecciona (encara que siguin a sota d'un altre);
  el cadenat els bloqueja; ↑ ↓ els porten endavant o enrere. Els grups es mostren com una carpeta.
-->
<script setup>
import { FONTS } from "@/pagines.js";
import { ordenaCapes } from "@/capes.js";
import { useEditorStore } from "@/stores/editor.js";

const store = useEditorStore();

const ICONES = {
  text: "M4 5h12M10 5v11", lletra: "M4 5h12M4 9h12M4 13h8", imatge: "M3 4h14v12H3zM3 13l4-4 3 3 2-2 5 5",
  forma: "M4 5h12v10H4z", numero: "M7 4 5.5 16M12.5 4 11 16M4 8h11M3.5 12h11", index: "M4 5h12M4 9h12M4 13h12",
  diagrames: "M5 4v12M8 4v12M11 4v12M14 4v12M5 7h9M5 10h9", diagrama: "M5 4v12M8 4v12M11 4v12M14 4v12M5 7h9M5 10h9",
  qr: "M3 3h5v5H3zM12 3h5v5h-5zM3 12h5v5H3zM12 12h2v2h-2zM15 15h2v2h-2z",
};

const ressalta = (p, ids, si) => store.crida("ressaltaCapes", p, ids, si);
</script>

<template>
  <div class="flex flex-col">
    <p class="px-4 pt-4 text-[13px] leading-snug text-ink-500">Tots els elements, del de davant al del fons. Passa-hi el ratolí per veure on són i clica per seleccionar-los, encara que siguin a sota d'un altre. El cadenat evita que es puguin seleccionar clicant al llenç. Amb <kbd class="font-mono">⌥</kbd> + clic al llenç selecciones l'element de sota.</p>
    <div class="flex flex-col gap-4 p-4">
      <p v-if="!store.capes" class="text-[13px] text-ink-500">Obre una cançó o una pàgina per veure'n les capes.</p>
      <div v-for="(pagina, p) in store.capes || []" :key="p" class="flex flex-col gap-0.5">
        <h4 class="mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-ink-400">{{ pagina.etiqueta }}</h4>
        <p v-if="!pagina.elements.length" class="px-2 text-[12px] text-ink-400">Sense elements.</p>
        <template v-for="e in ordenaCapes(pagina.elements)" :key="e.capcalera ? `g-${e.capcalera}` : e.id">
          <button v-if="e.capcalera" type="button" class="fila-capa w-full font-medium"
                  :aria-current="String(e.membres.every((m) => m.seleccionat))"
                  @mouseenter="ressalta(p, e.membres.map((m) => m.id), true)"
                  @mouseleave="ressalta(p, e.membres.map((m) => m.id), false)"
                  @click="ressalta(p, e.membres.map((m) => m.id), false); store.crida('seleccionaCapa', p, e.membres[0].id, { afegeix: $event.shiftKey })">
            <svg class="h-4 w-4 shrink-0 text-ink-400" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M3 6h5l1.5 2H17v8H3z"/></svg>
            <span class="flex-1 text-left">Grup ({{ e.membres.length }})</span>
          </button>
          <div v-else class="fila-capa group" :class="{ 'ml-4': e.grup }" :aria-current="String(e.seleccionat)"
               @mouseenter="ressalta(p, [e.id], true)" @mouseleave="ressalta(p, [e.id], false)">
            <svg class="h-4 w-4 shrink-0 text-ink-400" viewBox="0 0 20 20" aria-hidden="true">
              <path :d="ICONES[e.tipus] || ICONES.forma" fill="none" stroke="currentColor" stroke-width="1.5"/>
            </svg>
            <button type="button" class="min-w-0 flex-1 truncate text-left" :class="{ 'text-ink-500': e.bloquejat }"
                    :style="{ fontFamily: e.font ? FONTS[e.font] || '' : '' }"
                    @click="ressalta(p, [e.id], false); store.crida('seleccionaCapa', p, e.id, { afegeix: $event.shiftKey, sol: true })">{{ e.nom }}</button>
            <button type="button" class="flex h-6 w-6 shrink-0 items-center justify-center rounded text-ink-400 hover:bg-paper-200 hover:text-ink-900"
                    :class="e.bloquejat ? 'text-vermello-600' : 'opacity-0 group-hover:opacity-100'"
                    :title="e.bloquejat ? 'Desbloqueja' : 'Bloqueja (els clics hi passen a través)'"
                    :aria-label="e.bloquejat ? 'Desbloqueja' : 'Bloqueja'" :disabled="!store.editable"
                    @click="store.crida('bloquejaCapa', p, e.id)">
              <svg class="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true">
                <path :d="e.bloquejat ? 'M5 7V5a3 3 0 0 1 6 0v2M4 7h8v6.5H4z' : 'M5 7V5a3 3 0 0 1 5.8-1M4 7h8v6.5H4z'"/>
              </svg>
            </button>
            <button type="button" class="h-6 w-5 shrink-0 rounded text-ink-400 opacity-0 hover:bg-paper-200 group-hover:opacity-100 disabled:invisible"
                    title="Porta endavant" aria-label="Porta endavant" :disabled="!store.editable || e.index === e.total - 1"
                    @click="store.crida('mouCapa', p, e.id, 1)">↑</button>
            <button type="button" class="h-6 w-5 shrink-0 rounded text-ink-400 opacity-0 hover:bg-paper-200 group-hover:opacity-100 disabled:invisible"
                    title="Envia enrere" aria-label="Envia enrere" :disabled="!store.editable || e.index === 0"
                    @click="store.crida('mouCapa', p, e.id, -1)">↓</button>
          </div>
        </template>
        <p v-if="pagina.mestra" class="px-2 pt-1 text-[11.5px] text-ink-400">+ {{ pagina.mestra }} de la pàgina mestra (s'editen a Pàgines mestres)</p>
      </div>
    </div>
  </div>
</template>
