# Cançoners

Aplicació web per dissenyar cançoners en format llibret A5 (lletra i acords) i generar-ne el PDF a
punt per imprimir en A4 horitzontal a doble cara, plegar i cosir pel plec (enquadernació a cavallet).

L'editor mostra cada pàgina **exactament com sortirà al PDF**: el mateix codi dibuixa les pàgines a
l'editor i a la pàgina d'impressió, i el PDF el genera Chromium, el mateix motor que el navegador.

## Instal·lació (Mac)

Obre el Terminal i enganxa:

```bash
curl -fsSL https://raw.githubusercontent.com/drarekx/songery/main/install.sh | bash
```

Instal·la l'última versió a Aplicacions i l'obre. Per actualitzar-la, torna a executar la mateixa ordre o
fes servir «Actualitza a l'última versió» a la icona de la barra de menú. Les dades no es toquen.
Cal un Mac amb Apple Silicon (M1 o posterior) i macOS 12 o posterior.

## App per a Mac

`Cançoners.app` porta tot el que cal a dins (no cal Python ni Docker). En obrir-la, arrenca el servidor,
obre el navegador (Chrome si hi és) i deixa una icona a la barra de menú amb «Obre Cançoners», «Obre la
carpeta de dades», «Actualitza a l'última versió» i «Surt». Les dades es desen a
`~/Library/Application Support/Cançoners`, fora de l'app: actualitzar-la no les toca.

Per generar el PDF fa servir el Chrome, Edge o Brave del Mac en mode invisible. Si no n'hi ha cap, la
primera vegada baixa el «Chrome headless shell» oficial de Google (uns 90 MB).

## Publicar una versió nova

Cada versió és una *release* de GitHub amb l'app comprimida (`Canconers.zip`, la que baixa
`install.sh`) i un `.dmg`. Cal un Mac amb Apple Silicon, Python 3.12 (`brew install python@3.12`) i
[`gh`](https://cli.github.com) amb la sessió iniciada (`gh auth login`).

1. **Canvia el número de versió** a `eines/app/VERSIO` (per exemple, `1.0.0` → `1.1.0`).
2. **Puja els canvis** a la branca `main`:
   ```bash
   git add -A && git commit -m "Versió 1.1.0" && git push
   ```
3. **Publica-la**:
   ```bash
   ./eines/app/publica.sh
   ```
   El script construeix l'app amb PyInstaller, la signa, la comprimeix i crea la release `v1.1.0`.
   Tarda un parell de minuts.

A partir d'aquí, qui tingui l'app la pot actualitzar amb «Actualitza a l'última versió» de la barra de
menú, o tornant a executar l'ordre d'instal·lació.

Altres opcions:

```bash
./eines/app/construeix.sh                     # només construeix (dist/Cançoners.app i .dmg), sense publicar
./eines/app/publica.sh --ja-construida        # publica l'app que ja hi ha a dist/
CANCONER_NOTARITZA=1 ./eines/app/publica.sh   # a més, la notaritza amb Apple (vegeu més avall)
```

### Signatura i notarització

L'app s'instal·la per terminal amb `curl`, i macOS no marca com a «descarregat d'internet» el que baixa
`curl`: per això **no cal notaritzar-la**. Només cal si es vol repartir el `.dmg` directament (per
correu, des del navegador…), perquè s'obri sense avisos de seguretat.

`construeix.sh` signa l'app amb el primer certificat **Developer ID Application** que troba al clauer
(o el de `CANCONER_SIGNATURA`). Per poder notaritzar, una sola vegada:

1. Crea el certificat: Xcode → Settings → Accounts → l'equip → Manage Certificates → **+** →
   *Developer ID Application*.
2. Crea una contrasenya específica d'app a appleid.apple.com i desa les credencials al clauer:
   ```bash
   xcrun notarytool store-credentials canconers --apple-id EL_TEU_APPLE_ID --team-id EQUIP
   ```

Per seguir una notarització: `xcrun notarytool history --keychain-profile canconers` (i
`xcrun notarytool log ID --keychain-profile canconers` si Apple la rebutja).

## Instal·lació per desenvolupar

Cal **Python 3.11 o superior** i Chrome, Edge o Brave (o Docker amb Gotenberg).

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Execució

```bash
python app.py                      # http://localhost:5050
python app.py --host 0.0.0.0       # per obrir-lo des del mòbil a la mateixa xarxa
python app.py --port 8080 --debug
```

Motor de PDF: per defecte, el Chrome/Edge/Brave local (`CANCONER_NAVEGADOR` permet triar-ne un altre
executable). Per fer servir Gotenberg (Docker) en lloc seu: `docker compose up -d` i
`GOTENBERG_URL=http://127.0.0.1:3000 python app.py`. Gotenberg obre l'aplicació a través de
`host.docker.internal`; a Linux, arrenca-la amb `--host 0.0.0.0` o defineix `CANCONER_URL_INTERNA`.
`CANCONER_DADES` canvia el directori de dades.

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
app.py                     punt d'entrada (desenvolupament)
escriptori.py              llançador de l'app de Mac (servidor + navegador + barra de menú)
eines/app/                 construcció de Cançoners.app: PyInstaller, icones, signatura i notarització
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
  pdf.py                   tria del motor de PDF i memòria cau
  motor_pdf.py             PDF amb el Chromium local (DevTools), sense Docker
  tipografies.py           catàleg de tipografies i tipografies importades
  templates/               pàgines web, pàgina d'impressió (imprimible.html) i instruccions
  static/
    pagines.css            estils de les pàgines (compartits per l'editor i la impressió)
    editor.js              editor de pàgines
    dist/canconer.js       paquet compilat: Tiptap + motor de dibuix de pàgines
frontend/src/              font del paquet: editor-canco.js (Tiptap) i pagines.js (motor de dibuix)
tests/                     pytest
```
