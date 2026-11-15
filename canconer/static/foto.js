// «Des d'una foto»: crea una cançó a partir de la foto d'una partitura o d'un full de cançoner.
// La IA (el proveïdor i el model de /ia) en llegeix el títol, l'autor, la lletra amb acords i on és el
// pentagrama; aquí es revisa, es retalla el pentagrama de la foto i es puja com a imatge de la mèdia.
// El fan servir l'editor i la biblioteca:
//
//   const canco = await cancoDeFoto();   // null si es cancel·la
//   → { titol, autor, text, partitures: [{ src, proporcio }] }   (el que esperen les API de cançó nova)

const COSTAT_MAXIM = 2000; // px del costat llarg de la foto que s'envia a la IA
const AMPLE_MAXIM_RETALL = 2400; // px d'ample del retall de partitura que es desa
const TIPUS = ["image/jpeg", "image/png", "image/webp"];

function el(etiqueta, { classe, text, atributs } = {}, ...fills) {
  const node = document.createElement(etiqueta);
  if (classe) node.className = classe;
  if (text !== undefined) node.textContent = text;
  for (const [k, v] of Object.entries(atributs || {})) node.setAttribute(k, v);
  node.append(...fills);
  return node;
}

/** Dibuixa un tros de la foto (fraccions 0–1) en un llenç i en torna el JPEG. */
async function jpeg(foto, { x = 0, y = 0, ample = 1, alt = 1 }, { costat = Infinity, ampleMaxim = Infinity }, qualitat) {
  const sx = Math.round(x * foto.width), sy = Math.round(y * foto.height);
  const sw = Math.max(1, Math.round(ample * foto.width)), sh = Math.max(1, Math.round(alt * foto.height));
  const escala = Math.min(1, costat / Math.max(sw, sh), ampleMaxim / sw);
  const llenc = el("canvas");
  llenc.width = Math.max(1, Math.round(sw * escala));
  llenc.height = Math.max(1, Math.round(sh * escala));
  const ctx = llenc.getContext("2d");
  ctx.fillStyle = "#fff"; // les PNG transparents, sobre blanc
  ctx.fillRect(0, 0, llenc.width, llenc.height);
  ctx.drawImage(foto, sx, sy, sw, sh, 0, 0, llenc.width, llenc.height);
  const blob = await new Promise((resol) => llenc.toBlob(resol, "image/jpeg", qualitat));
  return { blob, proporcio: llenc.height / llenc.width };
}

async function resposta(r) {
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(d.error || `Error ${r.status}`), { codi: r.status });
  return d;
}

export function cancoDeFoto({ urlLlegeix = "/api/ia/canco-de-foto", urlImatges = "/api/imatges", urlConfiguracio = "/ia" } = {}) {
  return new Promise((resol) => {
    const dialeg = el("dialog", { classe: "w-[min(60rem,96vw)] rounded-xl border border-paper-300 bg-paper-50 p-0 text-ink shadow-full backdrop:bg-ink-900/30",
      atributs: { "aria-labelledby": "titol-foto" } });
    const tanca = el("button", { classe: "btn btn-fantasma btn-icona", text: "✕", atributs: { type: "button", "aria-label": "Tanca" } });
    const cos = el("div", { classe: "px-5 py-5" });
    dialeg.append(
      el("div", { classe: "flex items-center justify-between gap-3 border-b border-paper-300 px-5 py-3" },
        el("h2", { classe: "font-display text-xl font-medium", text: "Cançó des d'una foto", atributs: { id: "titol-foto" } }), tanca),
      cos);
    document.body.append(dialeg);

    let resultat = null;
    let foto = null; // ImageBitmap de la foto original
    let urlPrevia = null;
    let peticio = null; // AbortController de la lectura en curs
    tanca.addEventListener("click", () => dialeg.close());
    dialeg.addEventListener("close", () => {
      peticio?.abort();
      if (urlPrevia) URL.revokeObjectURL(urlPrevia);
      foto?.close?.();
      dialeg.remove();
      resol(resultat);
    }, { once: true });

    // ---------- 1. Triar la foto
    function pasTria(error = null) {
      const camp = el("input", { classe: "sr-only", atributs: { type: "file", accept: TIPUS.join(","), "aria-label": "Foto de la cançó" } });
      const boto = el("button", { classe: "btn btn-primari", text: "Tria una foto…", atributs: { type: "button" } });
      const zona = el("div", { classe: "flex flex-col items-center gap-3 rounded-lg border-2 border-dashed border-paper-300 bg-white px-6 py-12 text-center" },
        el("p", { classe: "max-w-md text-[14px] leading-snug text-ink-700", text: "Fes una foto a la partitura o al full del cançoner (ben il·luminada i de cara) i arrossega-la aquí." }),
        boto, camp,
        el("p", { classe: "text-[12px] text-ink-500", text: "JPG, PNG o WEBP. La foto s'envia al proveïdor d'IA que has configurat." }));
      const avis = error ? el("p", { classe: "avis mb-4", atributs: { role: "alert" } }, el("span", { text: "⚠", atributs: { "aria-hidden": "true" } }), el("span", { text: error.message })) : "";
      if (error?.codi === 409) {
        avis.lastChild.append(" ", el("a", { classe: "font-semibold underline", text: "Configura-la", atributs: { href: urlConfiguracio } }));
      }
      cos.replaceChildren(avis, zona);
      boto.addEventListener("click", () => camp.click());
      camp.addEventListener("change", () => camp.files[0] && llegeix(camp.files[0]));
      zona.addEventListener("dragover", (ev) => { ev.preventDefault(); zona.classList.add("border-accent-500"); });
      zona.addEventListener("dragleave", () => zona.classList.remove("border-accent-500"));
      zona.addEventListener("drop", (ev) => {
        ev.preventDefault();
        const fitxer = [...ev.dataTransfer.files].find((f) => f.type.startsWith("image/"));
        if (fitxer) llegeix(fitxer);
      });
      boto.focus();
    }

    // ---------- 2. La IA la llegeix
    async function llegeix(fitxer) {
      cos.replaceChildren(el("div", { classe: "flex flex-col items-center gap-3 px-6 py-16 text-center", atributs: { role: "status" } },
        el("span", { classe: "h-6 w-6 animate-spin rounded-full border-2 border-paper-300 border-t-accent-500", atributs: { "aria-hidden": "true" } }),
        el("p", { classe: "text-[14px] font-medium", text: "Llegint la foto…" }),
        el("p", { classe: "text-[13px] text-ink-500", text: "Pot trigar un minut si la cançó és llarga." })));
      try {
        try {
          foto?.close?.();
          foto = await createImageBitmap(fitxer);
        } catch {
          throw new Error("Aquest fitxer no es pot obrir com a imatge. Ha de ser JPG, PNG o WEBP (les HEIC de l'iPhone, exporta-les en JPG).");
        }
        const { blob } = await jpeg(foto, {}, { costat: COSTAT_MAXIM }, 0.88);
        if (urlPrevia) URL.revokeObjectURL(urlPrevia);
        urlPrevia = URL.createObjectURL(blob);
        const dades = new FormData();
        dades.append("foto", blob, "foto.jpg");
        peticio = new AbortController();
        const canco = await resposta(await fetch(urlLlegeix, { method: "POST", body: dades, signal: peticio.signal,
          headers: { "X-Requested-With": "canconers" } }));
        pasRevisa(canco, fitxer.name);
      } catch (e) {
        if (e.name !== "AbortError") pasTria(e);
      }
    }

    // ---------- 3. Revisar i crear
    function pasRevisa(canco, nomFitxer) {
      let retalls = canco.partitures.map((r) => ({ ...r }));
      const titol = el("input", { classe: "camp font-display text-lg", atributs: { maxlength: 200, placeholder: "Títol de la cançó" } });
      titol.value = canco.titol;
      const autor = el("input", { classe: "camp", atributs: { maxlength: 200, placeholder: "Opcional" } });
      autor.value = canco.autor;
      const text = el("textarea", { classe: "camp min-h-[16rem] flex-1 font-mono text-[13px] leading-snug", atributs: { wrap: "off", spellcheck: "false", rows: 14 } });
      text.value = canco.text;
      const inclou = el("input", { classe: "h-4 w-4", atributs: { type: "checkbox" } });
      inclou.checked = retalls.length > 0;

      // La foto, amb els retalls a sobre. Arrossegant-hi es dibuixa un retall nou (substitueix els que hi ha).
      const marc = el("div", { classe: "relative inline-block max-w-full cursor-crosshair touch-none select-none overflow-hidden rounded-md border border-paper-300 bg-white" },
        el("img", { classe: "pointer-events-none block max-h-[52vh] max-w-full", atributs: { src: urlPrevia, alt: "La foto", draggable: "false" } }));
      const pintaRetalls = () => {
        marc.querySelectorAll("[data-retall]").forEach((n) => n.remove());
        if (!inclou.checked) return;
        for (const r of retalls) {
          const caixa = el("div", { classe: "pointer-events-none absolute border-2 border-accent-500 bg-accent-500/10", atributs: { "data-retall": "" } });
          Object.assign(caixa.style, { left: `${r.x * 100}%`, top: `${r.y * 100}%`, width: `${r.ample * 100}%`, height: `${r.alt * 100}%` });
          marc.append(caixa);
        }
      };
      const punt = (ev) => {
        const m = marc.getBoundingClientRect();
        return [Math.min(1, Math.max(0, (ev.clientX - m.left) / m.width)), Math.min(1, Math.max(0, (ev.clientY - m.top) / m.height))];
      };
      marc.addEventListener("pointerdown", (ev) => {
        const [x0, y0] = punt(ev);
        const abans = retalls;
        marc.setPointerCapture(ev.pointerId);
        const mou = (e) => {
          const [x1, y1] = punt(e);
          retalls = [{ x: Math.min(x0, x1), y: Math.min(y0, y1), ample: Math.abs(x1 - x0), alt: Math.abs(y1 - y0) }];
          inclou.checked = true;
          pintaRetalls();
        };
        const fi = () => {
          marc.removeEventListener("pointermove", mou);
          if (retalls[0] && (retalls[0].ample < 0.03 || retalls[0].alt < 0.02)) retalls = abans; // un clic sense arrossegar
          pintaRetalls();
        };
        marc.addEventListener("pointermove", mou);
        marc.addEventListener("pointerup", fi, { once: true });
        marc.addEventListener("pointercancel", fi, { once: true });
      });
      inclou.addEventListener("change", pintaRetalls);
      pintaRetalls();

      const error = el("p", { classe: "avis hidden", atributs: { role: "alert" } }, el("span", { text: "⚠", atributs: { "aria-hidden": "true" } }), el("span"));
      const crea = el("button", { classe: "btn btn-primari", text: "Crea la cançó" });
      const altra = el("button", { classe: "btn btn-fantasma", text: "Una altra foto", atributs: { type: "button" } });
      const forma = el("form", { classe: "grid gap-5 md:grid-cols-2" },
        el("div", { classe: "flex min-w-0 flex-col gap-3" },
          el("label", {}, el("span", { classe: "etiqueta", text: "Títol" }), titol),
          el("label", {}, el("span", { classe: "etiqueta", text: "Autor" }), autor),
          el("label", { classe: "flex flex-1 flex-col" }, el("span", { classe: "etiqueta", text: "Lletra amb acords" }), text),
          el("p", { classe: "text-[12px] leading-snug text-ink-500", text: "Repassa-la: la IA es pot equivocar, sobretot amb els acords. Van en una línia a sobre de la lletra, alineats amb espais." })),
        el("div", { classe: "flex min-w-0 flex-col gap-3" },
          el("label", { classe: "flex items-center gap-2 text-[14px] font-medium" }, inclou, el("span", { text: "Posa-hi la partitura (un retall de la foto)" })),
          el("div", {}, marc),
          el("p", { classe: "text-[12px] leading-snug text-ink-500", text: retalls.length
            ? "El requadre és el que es retallarà. Si no agafa bé el pentagrama, arrossega sobre la foto per dibuixar-ne un de nou."
            : "No s'hi ha trobat cap pentagrama. Si n'hi ha un, arrossega sobre la foto per marcar-lo." })),
        el("div", { classe: "flex flex-wrap items-center justify-end gap-2 md:col-span-2" }, error, altra, crea));
      cos.replaceChildren(forma);
      altra.addEventListener("click", () => pasTria());
      forma.addEventListener("submit", async (ev) => {
        ev.preventDefault();
        crea.disabled = altra.disabled = true;
        crea.textContent = "Creant…";
        try {
          const partitures = [];
          for (const r of inclou.checked ? retalls : []) {
            const { blob, proporcio } = await jpeg(foto, r, { ampleMaxim: AMPLE_MAXIM_RETALL }, 0.92);
            const dades = new FormData();
            dades.append("imatge", blob, `partitura-${(titol.value.trim() || nomFitxer || "foto").replace(/\.[a-z0-9]+$/i, "").slice(0, 80)}.jpg`);
            const { id } = await resposta(await fetch(urlImatges, { method: "POST", body: dades }));
            partitures.push({ src: id, proporcio });
          }
          resultat = { titol: titol.value.trim(), autor: autor.value.trim(), text: text.value, partitures };
          dialeg.close();
        } catch (e) {
          error.lastChild.textContent = e.message;
          error.classList.remove("hidden");
          crea.disabled = altra.disabled = false;
          crea.textContent = "Crea la cançó";
        }
      });
      titol.focus();
    }

    pasTria();
    dialeg.showModal();
  });
}
