// JavaScript comú a totes les pàgines.
"use strict";

// Confirmació abans d'accions que no es poden desfer.
document.querySelectorAll("form[data-confirma]").forEach((form) => {
  form.addEventListener("submit", (e) => {
    if (!confirm(form.dataset.confirma)) e.preventDefault();
  });
});

// Els missatges de confirmació desapareixen sols.
document.querySelectorAll("[data-efimer]").forEach((missatge) => {
  setTimeout(() => missatge.classList.add("opacity-0"), 2500);
});
