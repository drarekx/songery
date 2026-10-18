// JavaScript comú a totes les pàgines.
"use strict";

// Els missatges de confirmació desapareixen sols.
document.querySelectorAll("[data-efimer]").forEach((missatge) => {
  setTimeout(() => missatge.classList.add("opacity-0"), 2500);
});
