// Preferències de l'usuari (l'estat de la interfície que es recorda): les porta la pàgina en un
// <script id="preferencies"> (les llegeix el servidor de preferencies.json) i, quan canvien, es desen
// al servidor amb PATCH /api/preferencies. Els canvis seguits (arrossegar una vora) s'ajunten.
import { defineStore } from "pinia";

const URL = "/api/preferencies";
const ESPERA = 400; // ms

function inicials() {
  try {
    return JSON.parse(document.getElementById("preferencies")?.textContent || "{}");
  } catch {
    return {};
  }
}

let pendents = {};
let temporitzador = null;

export const usePreferencies = defineStore("preferencies", {
  state: () => ({ valors: inicials() }),
  actions: {
    /** Valor d'una preferència (o el valor per defecte que es doni, si no n'hi ha). */
    llegeix(clau, perDefecte = undefined) {
      return this.valors[clau] ?? perDefecte;
    },
    /** Canvia una preferència (null: la torna al valor per defecte) i la desa d'aquí a una estona. */
    posa(clau, valor) {
      this.valors = { ...this.valors, [clau]: valor };
      pendents[clau] = valor;
      clearTimeout(temporitzador);
      temporitzador = setTimeout(() => this.desa(), ESPERA);
    },
    /** Desa ara els canvis pendents; el servidor torna els valors definitius (validats). */
    async desa() {
      clearTimeout(temporitzador);
      const canvis = pendents;
      pendents = {};
      if (!Object.keys(canvis).length) return;
      try {
        // keepalive: la petició s'acaba encara que es tanqui o es recarregui la pàgina.
        const r = await fetch(URL, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(canvis), keepalive: true });
        if (!r.ok) throw new Error(r.statusText);
        this.valors = { ...this.valors, ...(await r.json()) };
      } catch {
        // No s'ha pogut desar: es torna a provar amb el canvi següent (sense trepitjar-ne cap de més nou).
        pendents = { ...canvis, ...pendents };
      }
    },
  },
});

// En sortir de la pàgina, es desa el que encara no s'hagi desat.
window.addEventListener("pagehide", () => {
  if (Object.keys(pendents).length) usePreferencies().desa();
});
