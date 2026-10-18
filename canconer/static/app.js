// JavaScript comú a totes les pàgines.
"use strict";

// Confirmació abans d'accions que no es poden desfer.
// El missatge pot ser del formulari o només del botó que l'envia.
document.querySelectorAll("form").forEach((form) => {
  form.addEventListener("submit", (e) => {
    const missatge = e.submitter?.dataset.confirma ?? form.dataset.confirma;
    if (missatge && !confirm(missatge)) e.preventDefault();
  });
});

// Els missatges de confirmació desapareixen sols.
document.querySelectorAll("[data-efimer]").forEach((missatge) => {
  setTimeout(() => missatge.classList.add("opacity-0"), 2500);
});
