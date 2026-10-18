// Biblioteca de cançons: vista prèvia de la cançó que hi ha sota el ratolí (amb el mateix motor de
// dibuix que l'editor i el PDF; amb ‹ › o la roda es passa de pàgina) i el formulari de cançó nova.
import { AMPLE, acordsDePagines, ajustaMarcs, cssEstils, dibuixaPagina, esperaFonts, registraFonts } from "./dist/canconer.js";

const $ = (s) => document.querySelector(s);
const PX_MM = 96 / 25.4;

// ---------------------------------------------------------------- Cançó nova

const nova = $("#nova-canco");
const obreNova = $("#obre-nova");
function mostraNova(si) {
  nova.hidden = !si;
  obreNova.setAttribute("aria-expanded", String(si));
  if (si) nova.querySelector("[name=titol]").select();
}
obreNova.addEventListener("click", () => mostraNova(nova.hidden));
$("#tanca-nova").addEventListener("click", () => mostraNova(false));
nova.addEventListener("keydown", (ev) => { if (ev.key === "Escape") mostraNova(false); });

// ---------------------------------------------------------------- Vista prèvia

const previa = $("#previa");
if (previa) {
  registraFonts(JSON.parse($("#fonts-biblioteca").textContent));
  const estils = document.createElement("style");
  document.head.append(estils);
  const cau = new Map(); // id → promesa de les dades de la cançó
  let actual = null;
  let espera = null;

  const dades = (id) => {
    if (!cau.has(id)) {
      cau.set(id, fetch(`/api/canco/${id}/previa`).then((r) => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
        return r.json();
      }));
    }
    return cau.get(id);
  };

  let pagina = 0; // pàgina de la cançó que es veu
  let total = 1; // pàgines de la cançó que es veu

  async function mostra(id, numero = 0) {
    if (id === actual && numero === pagina) return;
    if (id !== actual) numero = 0;
    actual = id;
    pagina = numero;
    document.querySelectorAll(".fila-biblioteca").forEach((f) => f.classList.toggle("actiu", f.dataset.canco === id));
    let c;
    try {
      c = await dades(id);
    } catch {
      cau.delete(id);
      return;
    }
    if (actual !== id || pagina !== numero) return; // mentrestant, el ratolí ja és a una altra cançó
    const pagines = c.contingut.pagines;
    total = pagines.length;
    const p = pagines[Math.min(numero, pagines.length - 1)];
    const numeroLlibre = 2 + numero; // com si comencés a la pàgina 2 (a l'esquerra), com a la fitxa
    const mestra = c.mestres.find((m) => m.id === p.mestra);
    estils.textContent = cssEstils(c.estils, "#previa");
    const node = dibuixaPagina({
      ...p,
      mestra: mestra ? mestra[numeroLlibre % 2 === 0 ? "parell" : "senar"] : null,
      context: { titol: c.titol, autor: c.autor, acords: acordsDePagines(pagines).join(" · "), pagina: numeroLlibre },
    }, { urlImatge: (img) => `/imatges/${img}`, grup: "previa" });
    node.style.transformOrigin = "0 0";
    node.style.transform = `scale(${previa.clientWidth / (AMPLE * PX_MM)})`;
    previa.replaceChildren(node);
    $("#previa-pagines").textContent = pagines.length > 1 ? `pàg. ${numero + 1} de ${pagines.length}` : "1 pàgina";
    $("#previa-anterior").disabled = numero === 0;
    $("#previa-seguent").disabled = numero >= pagines.length - 1;
    $("#previa-titol").textContent = c.titol;
    await esperaFonts(previa);
    if (actual !== id || pagina !== numero) return;
    const elements = new Map(p.elements.map((e) => [e.id, e]));
    ajustaMarcs(previa, (x) => elements.get(x));
  }

  // Un petit retard perquè passar per sobre de moltes files de pressa no les carregui totes.
  const programa = (id, ms) => {
    clearTimeout(espera);
    espera = setTimeout(() => mostra(id), ms);
  };
  for (const fila of document.querySelectorAll(".fila-biblioteca")) {
    fila.addEventListener("mouseenter", () => programa(fila.dataset.canco, 90));
    fila.addEventListener("focusin", () => programa(fila.dataset.canco, 0));
  }
  // Passar de pàgina: amb els botons o amb la roda sobre la vista prèvia.
  const passa = (d) => {
    const desti = pagina + d;
    if (actual && desti >= 0 && desti < total) mostra(actual, desti);
  };
  $("#previa-anterior").addEventListener("click", () => passa(-1));
  $("#previa-seguent").addEventListener("click", () => passa(1));
  let roda = 0;
  previa.addEventListener("wheel", (ev) => {
    if (total < 2) return;
    ev.preventDefault();
    roda += ev.deltaY;
    if (Math.abs(roda) < 60) return;
    passa(roda > 0 ? 1 : -1);
    roda = 0;
  }, { passive: false });

  const primera = $(".fila-biblioteca");
  if (primera) mostra(primera.dataset.canco);
}
