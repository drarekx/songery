// Diàlegs de l'aplicació (en lloc dels confirm, alert i prompt del navegador): confirmar, avisar i
// preguntar un text. Tornen una promesa. Sense dependències: es carrega a totes les pàgines.
//
//   if (await confirma({ titol: "Esborrar la pàgina?", text: "…", accepta: "Esborra", perill: true })) …
//   await avisa({ titol: "Fet", text: "…" });
//   const nom = await pregunta({ titol: "Nom de la mestra", valor: "Mestra nova" }); // null si es cancel·la

const ICONES = {
  pregunta: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6v.6M12 17.2v.1"/>',
  perill: '<path d="M12 3.5 2.5 20h19z"/><path d="M12 10v4.5M12 17.2v.1"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.8v.1"/>',
  text: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>',
};

function element(etiqueta, classe, text) {
  const node = document.createElement(etiqueta);
  if (classe) node.className = classe;
  if (text !== undefined) node.textContent = text;
  return node;
}

/**
 * Obre un diàleg i torna una promesa amb el que s'hi ha triat.
 * opcions: titol, text, tipus (pregunta | perill | info | text), accepta, cancela (null: sense botó de
 * cancel·lar), camp ({valor, placeholder, etiqueta}) per preguntar un text.
 */
function obre({ titol, text = "", tipus = "pregunta", accepta = "D'acord", cancela = "Cancel·la", camp = null }) {
  return new Promise((resol) => {
    const dialeg = element("dialog", `dialeg-app dialeg-${tipus}`);
    dialeg.setAttribute("aria-labelledby", "dialeg-app-titol");
    const forma = element("form", "dialeg-app-cos");
    forma.method = "dialog";
    const icona = element("span", "dialeg-app-icona");
    icona.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONES[tipus] || ICONES.pregunta}</svg>`;
    const contingut = element("div", "dialeg-app-contingut");
    const h = element("h2", "dialeg-app-titol", titol);
    h.id = "dialeg-app-titol";
    contingut.append(h);
    if (text) contingut.append(element("p", "dialeg-app-text", text));
    let input = null;
    if (camp) {
      input = element("input", "camp dialeg-app-camp");
      input.value = camp.valor ?? "";
      input.placeholder = camp.placeholder ?? "";
      input.setAttribute("aria-label", camp.etiqueta || titol);
      input.maxLength = camp.maxim ?? 200;
      contingut.append(input);
    }
    const botons = element("div", "dialeg-app-botons");
    const boto = (etiqueta, classe, valor) => {
      const b = element("button", `btn ${classe}`, etiqueta);
      b.value = valor;
      return b;
    };
    const acceptar = boto(accepta, tipus === "perill" ? "btn-perill-ple" : "btn-primari", "si");
    if (cancela !== null) botons.append(boto(cancela, "btn-fantasma", "no"));
    botons.append(acceptar);
    forma.append(icona, contingut, botons);
    dialeg.append(forma);
    document.body.append(dialeg);

    const comprova = () => { if (input) acceptar.disabled = !input.value.trim(); };
    input?.addEventListener("input", comprova);
    comprova();
    // Clicar fora (al fons) és com cancel·lar.
    dialeg.addEventListener("click", (ev) => { if (ev.target === dialeg && cancela !== null) dialeg.close("no"); });
    dialeg.addEventListener("close", () => {
      const si = dialeg.returnValue === "si";
      dialeg.classList.add("tancant");
      setTimeout(() => dialeg.remove(), 160);
      resol(camp ? (si ? input.value.trim() : null) : si);
    }, { once: true });
    dialeg.addEventListener("cancel", (ev) => { if (cancela === null) ev.preventDefault(); });
    dialeg.showModal();
    // En un perill, el focus va a «cancel·lar» perquè un Intro despistat no esborri res.
    if (input) { input.focus(); input.select(); }
    else (tipus === "perill" && cancela !== null ? botons.firstChild : acceptar).focus();
  });
}

export const confirma = ({ perill = false, ...opcions }) => obre({ tipus: perill ? "perill" : "pregunta", accepta: "D'acord", ...opcions });
export const avisa = (opcions) => obre({ tipus: "info", cancela: null, ...opcions });
export const pregunta = ({ valor = "", placeholder = "", ...opcions }) =>
  obre({ tipus: "text", accepta: "Desa", camp: { valor, placeholder }, ...opcions });

// Formularis amb data-confirma: abans d'enviar-los, es demana confirmació (el text pot ser del
// formulari o del botó que l'envia; data-confirma-titol i data-confirma-accepta el personalitzen).
document.addEventListener("submit", async (ev) => {
  const form = ev.target;
  const font = ev.submitter?.dataset.confirma !== undefined ? ev.submitter : form;
  const missatge = font?.dataset?.confirma;
  if (!missatge || form.dataset.confirmat) return;
  ev.preventDefault();
  const si = await confirma({
    titol: font.dataset.confirmaTitol || "Segur?", text: missatge,
    accepta: font.dataset.confirmaAccepta || ev.submitter?.textContent.trim() || "D'acord", perill: true,
  });
  if (!si) return;
  form.dataset.confirmat = "1";
  if (ev.submitter?.name) {
    const ocult = element("input");
    Object.assign(ocult, { type: "hidden", name: ev.submitter.name, value: ev.submitter.value });
    form.append(ocult);
  }
  form.submit();
});
