# Arquitectura

## Un sol dibuix per a l'editor i el PDF

`frontend/src/pagines.js` dibuixa una pàgina A5 a partir del seu model (elements amb mides en mm). El
fan servir l'editor, les miniatures i `templates/imprimible.html`, la pàgina que el Chromium invisible
(`canconer/motor_pdf.py`, per DevTools) desa en PDF. Per això el que es veu a l'editor és el que surt.
`static/pagines.css` són els estils de les pàgines, compartits.

`pdf.empremta()` és la clau de la memòria cau dels PDF (`<dades>/cau/`): el cançoner i tot el codi de
dibuix (`dist/canconer.js`, `dist/trossos/*.js`, `pagines.css`). Si el dibuix canvia, la clau també.

## Del cançoner al llibret

- `plantilles.py`: estils, pàgines mestres, pàgines especials per defecte (`ESPECIALS`: portada, índex,
  acords, `acords_dos` per a guitarra i ukulele, índex de QR, contraportada) i la pàgina de cançó.
- `maquetacio.pla(canconer)`: la seqüència de pàgines. Cada cançó comença a l'esquerra (amb blanc si
  cal); s'arrodoneix a múltiple de 4, o de 2 si els fulls van solts (anelles: la mestra de marges té
  forats, `marges.fulls_solts`). La pàgina d'acords porta `diagrames` i `diagrames_instrument`
  (guitarra i ukulele) perquè cada bloc de diagrames triï l'instrument.
- `diagrames.py`: SVG de cada acord. Instrument del cançoner: `guitarra`, `ukulele` o `tots` (als diagrames
  de les cançons, els dos un al costat de l'altre).
- `imposicio.py`: fulls A4. Cavallet (plegar i cosir) o «talla i apila» (anelles, `ordre_talla_i_apila`).
- `marges.py`: mestres de marges d'enquadernació. Al PDF només s'hi afegeixen les marques dels forats.
- `cmyk.py`, `colors.py`: PDF per a impremta (colors CMYK exactes, Ghostscript per a la resta).

## Editor

`templates/editor.html` + `static/editor.js` (el llenç, els gestos, desar) + components Vue muntats amb
les funcions `munta…` de `frontend/src/vue.js`. L'estat compartit és l'store Pinia `useEditorStore`
(`frontend/src/stores/editor.js`): editor.js hi escriu amb `sincronitza` i els components criden les
accions d'editor.js amb `store.crida(nom, …)`.

- Lletra: Tiptap (`frontend/src/editor-canco.js`). Acords ancorats a la síl·laba, marques (tònica, cor,
  mida, tipografia, colors), ajust automàtic de mida (`ajustaMarcs` a pagines.js). Canviar la mida a mà
  treu l'ajust (`fixaMidaAjustada`), i «Reparteix» passa el que no hi cap a les pàgines següents.
- Eines i ajuda: `frontend/src/eines.js` és l'única llista d'eines (barres, menús i panell d'ajuda).
- Galeria de mèdia: `GaleriaMedia.vue`, oberta amb `obreGaleria({ tria })` (`frontend/src/galeria.js`).
- Preferències per usuari (amplada de columnes, pestanyes…): store `usePreferencies`, desades al servidor.

## Imprimir

`templates/imprimir.html`: visor de PDF amb pdf.js (`static/visor.js`: fulls A4 i llibret A5) i el llibret
en 3D (`static/llibret3d.js`: fulls amb transformacions CSS 3D; cada pàgina es dibuixa en un llenç a part
i es copia quan està acabada).

## Tests

- `tests/`: pytest del servidor. `tests/e2e/`: l'app de debò i un Chromium invisible (`conftest.py`:
  `pagina.obre`, `avalua`, `espera`, gestos del ratolí). Se salten si no hi ha cap Chromium.
- `tests/test_actualitzacio_dades.py`: obre bases de dades de cada esquema publicat i comprova que no es
  perd res.
- `frontend/tests/`: Vitest.
