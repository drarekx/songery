# Cançoners

Aplicació web per dissenyar cançoners en format llibret A5 (lletra i acords) i generar-ne el PDF a
punt per imprimir en A4 horitzontal a doble cara, plegar i cosir pel plec (enquadernació a cavallet).

L'editor mostra cada pàgina **exactament com sortirà al PDF**: el mateix codi dibuixa les pàgines a
l'editor i a la pàgina d'impressió, i el PDF el genera Chromium (Gotenberg), el mateix motor que el
navegador.

## Instal·lació

Cal **Python 3.11 o superior** i **Docker** (per a Gotenberg).

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
docker compose up -d               # engega Gotenberg a http://127.0.0.1:3000
```

## Execució

```bash
python app.py                      # http://localhost:5050
python app.py --host 0.0.0.0       # per obrir-lo des del mòbil a la mateixa xarxa
python app.py --port 8080 --debug
```

Gotenberg obre la pàgina d'impressió de l'aplicació des de Docker a través de
`host.docker.internal`. A Linux, arrenca l'aplicació amb `--host 0.0.0.0` o defineix
`CANCONER_URL_INTERNA` amb l'adreça amb què el contenidor arriba a l'aplicació. Altres variables:
`GOTENBERG_URL` (per defecte `http://127.0.0.1:3000`) i `CANCONER_DADES` (directori de dades).

> El navegador recomanat per editar és Chrome o Edge, el mateix motor que genera el PDF. Amb
> Safari o Firefox el resultat és pràcticament igual, però hi pot haver diferències mínimes de
> mesura de les fonts.

## Com funciona

Cada pàgina és un llenç A5 on es col·loquen elements amb el ratolí (mides en mil·límetres):

| Element | Què és |
|---|---|
| **Lletra** | Marc amb la lletra i els acords ancorats a la síl·laba. S'ajusta sol de mida perquè hi càpiga (i totes les pàgines d'una cançó fan servir la mateixa mida). Pot tenir columnes. |
| **Text** | Text lliure amb variables: `{titol}`, `{autor}`, `{acords}`, `{pagina}`, `{subtitol}`, `{any}`, `{contraportada}`. |
| **Imatge**, **rectangle**, **el·lipse** | Per decorar, il·lustrar o fer fons. |
| **Número de pàgina** | Sobretot a les pàgines mestres. |

- **Pàgines mestres**: elements que es repeteixen (número de pàgina, sanefes, fons), diferents per a
  les pàgines parells i les senars. Cada pàgina tria la seva mestra.
- **Estils**: Títol, Lletra, Acord, Secció, Nota… Canvies un estil i s'actualitza tot el cançoner.
  Cada element pot canviar-ne alguna propietat.
- **Biblioteca d'elements**: desa un element (o tots els d'una pàgina) i reutilitza'l a qualsevol
  pàgina o cançoner.
- **Lletra**: fes doble clic en un marc. Escriu `[G]` just abans de la síl·laba per posar un acord;
  `[Chorus]` sol en una línia crea una secció. Enganxa text de webs de tabs i es converteix sol.
  Marques: síl·laba tònica (⌘U), veus del cor (⇧⌘K), negreta, cursiva, notes. «Talla aquí» passa la
  resta de la lletra a la pàgina següent.
- **Biblioteca de cançons** amb **versions**: cada cançoner fa servir l'última versió o una de
  fixada, tria quines cançons surten al PDF i el transport.

### Paginació

Automàtica, amb excepcions:

- 1: portada. Després, l'índex (tantes pàgines com calgui) i, si es vol, la pàgina d'acords.
- Cada cançó comença en pàgina parella (esquerra), amb una pàgina en blanc si cal. Es pot marcar
  «comença on toqui» per posar dues cançons curtes a la mateixa doble pàgina. Les **pàgines
  lliures** (dedicatòries, il·lustracions) van on les posis.
- Pàgines en blanc fins a un múltiple de 4, la pàgina d'acords si va al final, i la contraportada.

### Imposició

Amb N pàgines i F = N/4 fulls, el full *i* (0..F-1) porta:

| Cara      | Esquerra | Dreta      |
|-----------|----------|------------|
| davantera | N − 2i   | 1 + 2i     |
| darrere   | 2 + 2i   | N − 1 − 2i |

Exemple N=12: `12|1, 2|11, 10|3, 4|9, 8|5, 6|7`. Imprimeix el PDF A4 a **mida real**, a **doble cara
girant per la vora curta**. Per a impressores sense doble cara hi ha PDF separats de cares
davanteres i del darrere, i un **full d'instruccions** imprimible.

## Dades

- `data/canconers.sqlite3`: cançoners, cançons, versions i biblioteca d'elements.
- `data/imatges/`: imatges pujades. `data/cau/`: PDF generats (es poden esborrar sense perill).
- Les dades de versions anteriors (JSON o cançons d'un sol document) es migren soles en arrencar.

## Desenvolupament

```bash
python -m pytest                   # tests (la prova amb Gotenberg s'omet si no està en marxa)
./eines/css.sh [--watch]           # compila el CSS de Tailwind (sense Node)
cd frontend && npm install && npm run build   # editor i motor de pàgines (Tiptap + esbuild)
```

Els fitxers compilats (`canconer/static/app.css` i `canconer/static/dist/canconer.js`) ja vénen fets.

```
app.py                     punt d'entrada
docker-compose.yml         Gotenberg
canconer/
  web.py                   rutes Flask i API JSON
  basedades.py             SQLite: cançons, versions, cançoners, entrades, imatges, elements
  plantilles.py            estils, mestres, pàgines especials i plantilla de cançó per defecte
  maquetacio.py            seqüència de pàgines del llibret (regles de paginació)
  disseny.py               validació del disseny que envia l'editor
  document.py              format de la lletra (Tiptap): conversió de text de tabs i transport
  parser.py                detecció d'acords i transport
  diagrames.py             diagrames de guitarra i ukulele en SVG
  imposicio.py             ordre de cavallet i muntatge A4 amb pypdf
  pdf.py                   Gotenberg i memòria cau
  templates/               pàgines web, pàgina d'impressió (imprimible.html) i instruccions
  static/
    pagines.css            estils de les pàgines (compartits per l'editor i la impressió)
    editor.js              editor de pàgines
    dist/canconer.js       paquet compilat: Tiptap + motor de dibuix de pàgines
frontend/src/              font del paquet: editor-canco.js (Tiptap) i pagines.js (motor de dibuix)
tests/                     pytest
```
