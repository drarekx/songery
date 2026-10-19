// Eines de l'editor de cançons: una sola font per a la barra d'eines, la barra de la lletra i l'ajuda
// («?»). Cada eina: nom (el que es crida), titol, drecera (opcional), descripcio i icona (SVG de 20×20).
// Una eina nova afegida aquí surt alhora a la barra i a l'ajuda.

/** Text del tooltip d'una eina: el títol i, si en té, la drecera. */
export const tooltip = (eina) => (eina.drecera ? `${eina.titol} (${eina.drecera})` : eina.titol);

/** Barra d'eines del llenç (BarraEines.vue). */
export const GRUPS_EINES = [
  { titol: "Edició", eines: [
    { nom: "desfes", titol: "Desfés", drecera: "⌘Z", descripcio: "Desfà l'últim canvi de la pàgina.",
      icona: '<path d="M7 5 3 9l4 4M3 9h9a4 4 0 0 1 0 8h-1"/>' },
    { nom: "refes", titol: "Refés", drecera: "⇧⌘Z", descripcio: "Torna a fer el que s'ha desfet.",
      icona: '<path d="m13 5 4 4-4 4M17 9H8a4 4 0 0 0 0 8h1"/>' },
  ] },
  { etiqueta: "Afegeix", titol: "Afegeix a la pàgina", eines: [
    { nom: "nou-lletra", titol: "Marc de lletra amb acords", descripcio: "Un marc per escriure la lletra amb els acords a sobre. Es fa més petita sola si no hi cap.",
      icona: '<rect x="3" y="3" width="14" height="14" rx="1"/><path d="M6 8h8M6 11h8M6 14h5"/><path d="M6 5.5h1.5" stroke-width="2.4"/>' },
    { nom: "nou-text", titol: "Text", descripcio: "Un text lliure: títols, peus, dedicatòries… Pot portar {titol}, {autor}, {pagina}…",
      icona: '<path d="M4 5h12M10 5v11M8 16h4"/>' },
    { nom: "nou-imatge", titol: "Imatge", descripcio: "Una imatge de l'ordinador. També es pot arrossegar o enganxar (⌘V).",
      icona: '<rect x="3" y="4" width="14" height="12" rx="1.5"/><circle cx="7.5" cy="8.5" r="1.5"/><path d="m3 14 4-4 3 3 2-2 5 5"/>' },
    { nom: "nou-forma", titol: "Rectangle", descripcio: "Un rectangle de color, per a fons, franges o requadres.",
      icona: '<rect x="3.5" y="5" width="13" height="10" rx="1"/>' },
    { nom: "nou-elipse", titol: "El·lipse", descripcio: "Una el·lipse o un cercle de color.",
      icona: '<ellipse cx="10" cy="10" rx="7" ry="5.5"/>' },
    { nom: "nou-numero", titol: "Número de pàgina", descripcio: "El número de la pàgina, que es posa sol segons on caigui al llibret.",
      icona: '<path d="M6 4 4.5 16M11.5 4 10 16M3.5 8h11M3 12h11"/>' },
    { nom: "acords", titol: "Diagrames d'acords: arrossega'ls a la pàgina", premut: true,
      descripcio: "Obre el panell amb els diagrames dels acords de la cançó; arrossega'n un (o tots) a la pàgina.",
      icona: '<rect x="4" y="3" width="12" height="14" rx="1"/><path d="M7 3v14M10 3v14M13 3v14M4 7h12M4 11h12"/><circle cx="10" cy="9" r="1.3" fill="currentColor"/><circle cx="13" cy="13" r="1.3" fill="currentColor"/>' },
    { nom: "nou-qr", titol: "Codi QR d'un vídeo de la cançó", descripcio: "Un codi QR que porta a un dels vídeos de YouTube de la cançó (pestanya Cançó).",
      icona: '<path d="M3 3h5v5H3zM12 3h5v5h-5zM3 12h5v5H3z"/><path d="M12 12h2v2h-2zM15 15h2v2h-2zM12 16h1M16 12h1" stroke-width="1.8"/>' },
    { nom: "importa-text", titol: "Importa text amb acords (de webs de tabs) al marc de lletra",
      descripcio: "Enganxa una cançó amb els acords a sobre de la lletra (com a les webs d'acords) i la converteix.",
      icona: '<path d="M7 4H5v13h10V4h-2M7 3h6v3H7z"/><path d="M8 10h4M8 13h4"/>' },
  ] },
  { etiqueta: "Pàgina", titol: "Pàgines de la cançó", pagina: true, eines: [
    { nom: "pagina-nova", titol: "Afegeix una pàgina a la cançó", descripcio: "Una pàgina nova després de la que tens oberta, amb un marc de lletra a punt.",
      icona: '<path d="M5 3h7l3 3v11H5z"/><path d="M10 9v5M7.5 11.5h5"/>' },
    { nom: "pagina-duplica", titol: "Duplica la pàgina", descripcio: "Una còpia de la pàgina, just després.",
      icona: '<rect x="6" y="6" width="10" height="11" rx="1"/><path d="M4 13V3h8"/>' },
    { nom: "pagina-esquerra", titol: "Mou la pàgina enrere", descripcio: "Canvia l'ordre de les pàgines de la cançó.",
      icona: '<path d="m12 5-5 5 5 5"/>' },
    { nom: "pagina-dreta", titol: "Mou la pàgina endavant", descripcio: "Canvia l'ordre de les pàgines de la cançó.",
      icona: '<path d="m8 5 5 5-5 5"/>' },
    { nom: "pagina-esborra", titol: "Esborra la pàgina", descripcio: "Treu la pàgina de la cançó (es pot desfer).",
      icona: '<path d="M4 6h12M8 6V4h4v2M6 6l.8 11h6.4L14 6"/>' },
  ] },
];

/** Moure el llenç i zoom (a la dreta de la barra d'eines). */
export const EINES_LLENC = [
  { nom: "ma", titol: "Mou el llenç", drecera: "espai", descripcio: "Arrossega per moure't pel llenç. També mantenint l'espai premut o amb el botó del mig del ratolí.",
    icona: '<path d="M7 10V4.5a1.2 1.2 0 0 1 2.4 0V9m0-4.5V3.3a1.2 1.2 0 0 1 2.4 0V9m0-4.2a1.2 1.2 0 0 1 2.4 0V10m0-3a1.2 1.2 0 0 1 2.4 0v4.5c0 3.4-2.4 6-5.6 6-2.2 0-3.6-1-4.7-2.7L4.3 12a1.2 1.2 0 0 1 2-1.3L7 11.6"/>' },
  { nom: "zoom", titol: "Zoom", drecera: "⌘ + roda o pessic", descripcio: "− i + apropen i allunyen; «Ajusta» posa la doble pàgina a la mida de la finestra.",
    icona: '<circle cx="9" cy="9" r="5.5"/><path d="m13 13 4 4M7 9h4M9 7v4"/>' },
];

/** Barra de la lletra, mentre s'edita un marc de lletra (BarraText.vue). */
export const GRUPS_LLETRA = [
  [
    { nom: "tonica", titol: "Síl·laba tònica", drecera: "⌘U", marca: true, descripcio: "Marca la síl·laba on va l'accent de la melodia.",
      icona: '<path d="M6 4v6a4 4 0 0 0 8 0V4M4 17h12" stroke-width="1.8"/>' },
    { nom: "bold", titol: "Negreta", drecera: "⌘B", marca: true, descripcio: "Text en negreta.",
      icona: '<path d="M6 4h5a3 3 0 0 1 0 6H6zm0 6h6a3 3 0 0 1 0 6H6z" stroke-width="1.9"/>' },
    { nom: "italic", titol: "Cursiva", drecera: "⌘I", marca: true, descripcio: "Text en cursiva.",
      icona: '<path d="M12 4H8m4 12H8m3-12-2 12"/>' },
    { nom: "cor", titol: "Veus del cor", drecera: "⇧⌘K", marca: true, descripcio: "Marca el que canta el cor (es mostra diferent).",
      icona: '<circle cx="7" cy="7" r="2.5"/><circle cx="13" cy="7" r="2.5"/><path d="M3 16a4 4 0 0 1 8 0m-2 0a4 4 0 0 1 8 0"/>' },
  ],
  [
    { nom: "seccio", titol: "Secció: Intro, Tornada…", drecera: "⌥⌘1", marca: true, descripcio: "Converteix la línia en una etiqueta de secció. També escrivint [Tornada] sol en una línia.",
      icona: '<path d="M4 5h12M4 10h7M4 15h9"/><path d="M14 10h3" stroke-width="2.4"/>' },
    { nom: "nota", titol: "Nota: x2, només veus…", drecera: "⌥⌘2", marca: true, descripcio: "Converteix la línia en una indicació en petit.",
      icona: '<path d="M5 3h7l3 3v11H5z"/><path d="M8 9h4M8 12h4"/>' },
    { nom: "imatge", titol: "Imatge dins la lletra (amb el text al voltant)", descripcio: "Una imatge dins del marc, amb la lletra al costat.",
      icona: '<rect x="3" y="4" width="14" height="12" rx="1.5"/><circle cx="7.5" cy="8.5" r="1.5"/><path d="m3 14 4-4 3 3 2-2 5 5"/>' },
    { nom: "enganxa", titol: "Importa text amb acords (de webs de tabs)", descripcio: "Enganxa una cançó amb els acords a sobre i la posa al marc.",
      icona: '<path d="M7 4H5v13h10V4h-2M7 3h6v3H7z"/><path d="M8 10h4M8 13h4"/>' },
  ],
  [
    { nom: "talla", titol: "Talla aquí: passa la lletra que hi ha després del cursor a la pàgina següent",
      descripcio: "Talla la lletra on és el cursor i en passa la resta a la pàgina següent.",
      icona: '<circle cx="5" cy="6" r="2.2"/><circle cx="5" cy="14" r="2.2"/><path d="m7 7 10 7M7 13l10-7"/>' },
    { nom: "reparteix", titol: "Reparteix: passa a la pàgina següent la lletra que no hi cap, tallant per una estrofa",
      descripcio: "Passa a la pàgina següent la lletra que no hi cap, tallant entre estrofes.",
      icona: '<rect x="2.5" y="3" width="6.5" height="14" rx="1"/><rect x="11" y="3" width="6.5" height="14" rx="1"/><path d="M4.5 7h2.5M4.5 10h2.5M13 7h2.5M13 10h1.5"/><path d="M7.5 14h5m-1.5-1.5 1.5 1.5-1.5 1.5" stroke-width="1.4"/>' },
  ],
];

/** El que surt en seleccionar text dins la lletra (la bombolla) i altres dreceres. */
export const TEXT_SELECCIONAT = [
  { titol: "Acord", drecera: "⌘K", descripcio: "Posa un acord a sobre de la síl·laba (o escriu [G] a la lletra)." },
  { titol: "Mida", descripcio: "Fa el text seleccionat més petit o més gran que la resta." },
  { titol: "Tipografia (Aa)", descripcio: "Canvia la tipografia del text seleccionat." },
  { titol: "Color del text i del fons", descripcio: "Colors del text seleccionat i del seu fons (en CMYK, exactes al PDF)." },
];

export const DRECERES = [
  ["⌘C ⌘V ⌘D", "Copia, enganxa i duplica elements (⌘V també enganxa imatges copiades)"],
  ["⇧ clic", "Afegeix un element a la selecció"],
  ["⌘A", "Selecciona tota la pàgina"],
  ["⌘G ⇧⌘G", "Agrupa i desagrupa"],
  ["← ↑ → ↓", "Mou 0,5 mm (amb ⇧, 5 mm)"],
  ["⌥ arrossega", "Mou sense que s'enganxi a les guies"],
  ["Supr", "Esborra l'element seleccionat"],
  ["clic dret", "Menú amb totes les opcions de l'element o de la pàgina"],
  ["⌥ clic dret", "Dins la lletra que edites, el menú del navegador (corrector, copiar…)"],
  ["doble clic", "Edita la lletra o el text"],
  ["?", "Obre aquesta ajuda"],
];
