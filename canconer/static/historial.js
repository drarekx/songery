// Fitxa d'una cançó a la biblioteca: vista prèvia de l'esborrany i de cada versió (amb el mateix
// motor de dibuix que l'editor i el PDF), notes de les versions i restauració.
import { avisa, confirma } from "./dist/dialegs.js";
import { acordsDePagines, ajustaMarcs, aplicaEstils, dibuixaPagina, esperaFonts, registraFonts } from "./dist/canconer.js";

const dades = JSON.parse(document.getElementById("dades-historial").textContent);
const urls = dades.urls;
const $ = (s) => document.querySelector(s);
const PX_MM = 96 / 25.4;
const ESCALA = 0.55;

registraFonts(dades.fonts);
aplicaEstils(dades.estils);

let seleccionada = null; // id de la versió que es mostra (null = esborrany)

async function api(url, metode = "GET", cos) {
  const r = await fetch(url, { method: metode, headers: cos ? { "Content-Type": "application/json" } : {}, body: cos ? JSON.stringify(cos) : undefined });
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

function mestraDe(id, numero) {
  const m = dades.mestres.find((x) => x.id === id);
  return m ? m[numero % 2 === 0 ? "parell" : "senar"] : null;
}

/** Dibuixa les pàgines (com si la cançó comencés a la pàgina 2, a l'esquerra). */
async function mostra(contingut, titol, autor) {
  const vista = $("#vista");
  const acords = acordsDePagines(contingut.pagines);
  const caixes = contingut.pagines.map((p, i) => {
    const numero = 2 + i;
    const caixa = document.createElement("div");
    caixa.className = "pagina-editor";
    caixa.style.width = `${148 * PX_MM * ESCALA}px`;
    caixa.style.height = `${210 * PX_MM * ESCALA}px`;
    const pagina = dibuixaPagina({
      ...p,
      mestra: mestraDe(p.mestra, numero),
      context: { titol, autor, acords: acords.join(" · "), pagina: numero },
    }, { urlImatge: (id) => urls.imatge + id, grup: "vista" });
    pagina.style.transform = `scale(${ESCALA})`;
    pagina.style.transformOrigin = "0 0";
    caixa.append(pagina);
    return caixa;
  });
  vista.replaceChildren(...caixes);
  await esperaFonts(vista);
  const perId = new Map(contingut.pagines.flatMap((p) => p.elements).map((e) => [e.id, e]));
  ajustaMarcs(vista, (id) => perId.get(id));
}

async function selecciona(idVersio) {
  seleccionada = idVersio || null;
  document.querySelectorAll("[data-versio]").forEach((b) => b.setAttribute("aria-current", String((b.dataset.versio || null) === seleccionada)));
  $("#accions-esborrany").classList.toggle("hidden", !!seleccionada);
  $("#accions-esborrany").classList.toggle("flex", !seleccionada);
  $("#accions-versio").classList.toggle("hidden", !seleccionada);
  $("#accions-versio").classList.toggle("flex", !!seleccionada);
  if (!seleccionada) {
    const c = await api(urls.canco);
    $("#titol-vista").textContent = "Esborrany actual";
    return mostra(c.contingut, c.titol, c.autor);
  }
  const v = await api(urls.versio + seleccionada);
  $("#titol-vista").textContent = `Versió ${v.numero}${v.nota ? ` · ${v.nota}` : ""}`;
  $("#nota-versio").value = v.nota || "";
  return mostra(v.contingut, v.titol, v.autor);
}

document.querySelectorAll("[data-versio]").forEach((b) => b.addEventListener("click", () => selecciona(b.dataset.versio)));

$("#desa-nota").addEventListener("click", async () => {
  const { nota } = await api(`${urls.versio}${seleccionada}/nota`, "PUT", { nota: $("#nota-versio").value });
  const fila = document.querySelector(`[data-fila-versio="${seleccionada}"] .nota-versio`);
  if (fila && nota) fila.textContent = nota;
  const numero = document.querySelector(`[data-versio="${seleccionada}"]`).dataset.numero;
  $("#titol-vista").textContent = `Versió ${numero}${nota ? ` · ${nota}` : ""}`;
});

$("#restaura").addEventListener("click", async () => {
  const numero = document.querySelector(`[data-versio="${seleccionada}"]`).dataset.numero;
  const segueixen = dades.usos.filter((u) => !u.versio_id).map((u) => u.titol);
  const avis = segueixen.length ? `\n\nCanviarà a: ${segueixen.join(", ")} (segueixen l'esborrany).` : "";
  if (!await confirma({ titol: `Tornar a la versió ${numero}?`, text: `L'esborrany tornarà a ser com aquesta versió. L'estat actual es desarà abans com una versió nova.${avis}`, accepta: "Restaura-la" })) return;
  await api(urls.restaura, "POST", { versio_id: seleccionada });
  location.reload();
});

$("#desa-versio").addEventListener("click", async () => {
  const r = await api(urls.versions, "POST", { nota: $("#nota-nova").value });
  if (!r.versio) await avisa({ titol: "No hi ha res de nou", text: "L'esborrany és igual que l'última versió: no s'ha creat cap versió nova." });
  location.reload();
});

selecciona(null);
