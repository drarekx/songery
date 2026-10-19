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

Instal·la l'última versió a Aplicacions i l'obre. L'app avisa quan n'hi ha una de nova (vegeu
[Actualitzacions i còpies de seguretat](#actualitzacions-i-còpies-de-seguretat)); també es pot
actualitzar tornant a executar la mateixa ordre. Les dades no es toquen.
Cal un Mac amb Apple Silicon (M1 o posterior) i macOS 12 o posterior.

## App per a Mac

`Cançoners.app` porta tot el que cal a dins (no cal Python ni Docker). En obrir-la, arrenca el servidor
(sempre al mateix port si és lliure) i obre Cançoners en una pestanya de Chrome (o Edge o Brave; si no
n'hi ha cap, al navegador per defecte). Tornar-la a obrir des del Dock va a la mateixa pestanya: la
primera vegada macOS demana permís perquè Cançoners pugui controlar Chrome.

A la barra de menú hi ha «Obre Cançoners», «Obre la carpeta de dades», la versió instal·lada, «Cerca
actualitzacions…», «Fes una còpia de seguretat ara», «Còpies de seguretat…» i «Surt». Les dades es desen
a `~/Library/Application Support/Cançoners`, fora de l'app: actualitzar-la no les toca.

### Actualitzacions i còpies de seguretat

- En obrir l'app i un cop al dia, es mira a GitHub Releases si hi ha una versió més nova que la
  d'`eines/app/VERSIO`. Si n'hi ha, avisa i pregunta si es vol instal·lar. «Cerca actualitzacions…» ho
  comprova a l'acte.
- Abans d'actualitzar es fa **sempre** una còpia de seguretat; si falla, no s'actualitza.
- L'actualització es fa a la pàgina `/actualitzacio`, que en mostra cada pas: còpia de seguretat,
  baixada, verificació de la signatura (Developer ID), instal·lació i reinici. Si la versió nova no
  arrenca en un minut, es torna a posar l'anterior. El registre queda a `actualitzacio.log`.
- Les còpies (`copies/` a la carpeta de dades) porten la base de dades, les imatges i les tipografies.
  Es conserven les 10 últimes i totes les dels últims 30 dies (fins a 60), i mai s'esborra la més
  recent amb dades. A «Còpies de seguretat…» (pàgina `/copies`) es pot veure què hi ha a cadascuna i
  restaurar-la; abans de restaurar se'n desa una de l'estat actual.
- Les dades es migren soles en obrir una versió nova (amb còpia abans; si una migració falla, no es
  toca res).

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

A partir d'aquí, les apps instal·lades avisen que hi ha la versió nova (en obrir-se o en un dia com a
molt) i s'actualitzen si s'accepta. També es pot fer amb «Cerca actualitzacions…» o tornant a
executar l'ordre d'instal·lació.

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
python app.py                      # http://localhost:5180 (amb una franja «DESENVOLUPAMENT»)
python app.py --host 0.0.0.0       # per obrir-lo des del mòbil a la mateixa xarxa
python app.py --port 8080 --debug
python app.py --sense-recarrega    # per defecte es recarrega sol quan canvia el codi
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
| **Lletra** | Marc amb la lletra i els acords ancorats a la síl·laba. S'ajusta sol de mida perquè hi càpiga (si no se li canvia la mida a mà). Pot tenir columnes. |
| **Text** | Text lliure amb variables: `{titol}`, `{autor}`, `{acords}`, `{pagina}`, `{subtitol}`, `{any}`, `{contraportada}`. |
| **Imatge**, **rectangle**, **el·lipse** | Per decorar, il·lustrar o fer fons. |
| **Diagrames d'acords** | Un acord sol o tots els de la cançó, per a guitarra, ukulele o tots dos. |
| **Codi QR** | Porta a un vídeo de la cançó. |
| **Número de pàgina** | Sobretot a les pàgines mestres. |

- **Pàgines mestres**: elements que es repeteixen (número de pàgina, sanefes, fons), diferents per a
  les pàgines parells i les senars.
- **Estils**: Títol, Lletra, Acord, Secció, Nota… i els propis que hi creïs (també a partir d'un
  element). Canvies un estil i s'actualitza tot el cançoner; se'n pot posar un a diversos elements d'un cop.
- **Mèdia**: una galeria d'imatges compartida per tots els cançoners, en carpetes. Hi pots pujar imatges
  (PNG, JPG, WEBP o GIF), arrossegar-les o enganxar-les (⌘V), moure-les de carpeta i esborrar les que no
  es fan servir. Les imatges enganxades o arrossegades a la pàgina també s'hi desen.
- **Lletra**: fes doble clic en un marc. Escriu `[G]` just abans de la síl·laba per posar un acord;
  `[Chorus]` sol en una línia crea una secció. Enganxa text de webs de tabs i es converteix sol.
  Marques: síl·laba tònica (⌘U), veus del cor (⇧⌘K), negreta, cursiva, notes, i mida, tipografia i
  colors del text seleccionat. Amb el botó dret: «Reparteix» passa el que no hi cap a les pàgines
  següents i «Talla aquí» hi passa la resta des del punt clicat.
- **Biblioteca de cançons** amb **versions** i **autors**: cada cançoner fa servir l'última versió o una
  de fixada, tria quines cançons surten al PDF i el transport.
- **Biblioteca d'elements**: desa un element (o tots els d'una pàgina) i reutilitza'l on vulguis.
- **Recursos**: cançoners de base per començar (nadales i cançons populars, de domini públic).
- **Opcions del cançoner**: índex, pàgina d'acords (al principi o al final), instrument dels diagrames
  (guitarra, ukulele o els dos, amb una pàgina d'acords de dos blocs) i marges d'enquadernació, que a
  l'editor es veuen com a guies.

### Paginació

Automàtica, amb excepcions:

- 1: portada. Després, l'índex (tantes pàgines com calgui) i, si es vol, la pàgina d'acords.
- Cada cançó comença en pàgina parella (esquerra), amb una pàgina en blanc si cal. Es pot marcar
  «comença on toqui». Les **pàgines lliures** (dedicatòries, il·lustracions) van on les posis.
- Pàgines en blanc fins a un múltiple de 4 (un full plegat fa 4 pàgines), o de 2 amb anelles (marges amb
  forats: els fulls van solts). Després, la pàgina d'acords si va al final, i la contraportada.

### Imposició

Fulls A4 en horitzontal amb dues pàgines A5 per cara, a **doble cara girant per la vora curta** i a
**mida real**.

**Per plegar i cosir** (cavallet). Amb N pàgines i F = N/4 fulls, el full *i* (0..F-1) porta:

| Cara      | Esquerra | Dreta      |
|-----------|----------|------------|
| davantera | N − 2i   | 1 + 2i     |
| darrere   | 2 + 2i   | N − 1 − 2i |

Exemple N=12: `12|1, 2|11, 10|3, 4|9, 8|5, 6|7`.

**Amb anelles** (talla i apila): els fulls es tallen pel mig i la pila de les meitats esquerres va a sobre
de la de les dretes, i les pàgines queden en ordre. Amb F = ⌈N/4⌉ fulls, el full *i* porta 1 + 2i |
1 + 2(F + i) a davant i 2 + 2(F + i) | 2 + 2i al darrere; el que passa de N queda en blanc.

Per a impressores sense doble cara hi ha PDF separats de cares davanteres i del darrere, i un **full
d'instruccions** imprimible. A Imprimir es pot veure el llibret obert, els fulls A4 i un **llibret en 3D**
on es passen les pàgines.

### Colors per a impremta (CMYK)

Els colors es poden triar en CMYK (C, M, Y, K en %) a tots els selectors de color de l'editor, o en
RGB. A Imprimir, «Per a impremta (CMYK)» dona el llibret A5 i els fulls A4 imposats en CMYK:

- Els colors triats en CMYK surten **exactes**. Per aconseguir-ho, cada color CMYK es dibuixa amb un
  RGB «testimoni» únic (`canconer/colors.py`) i, al PDF, aquestes ordres de color es canvien per les
  CMYK (`canconer/cmyk.py`).
- La resta (colors en RGB i imatges) la converteix Ghostscript amb el seu perfil CMYK.
- Els colors per defecte de les plantilles ja són CMYK, i els grisos només fan servir tinta negra,
  perquè la lletra petita no surti borrosa.
- Els PDF de sempre (RGB) continuen igual, per a la impressora de casa.

Ghostscript es compila des del codi font oficial amb `./eines/app/ghostscript.sh` (el fa servir
`construeix.sh`) i va dins de l'app. **Llicència:** Ghostscript és © Artifex Software, sota
[AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.html); l'app en porta la llicència i l'adreça del
codi font (`eines/ghostscript/LICENSE` i `CODI_FONT`) i es fa servir sense modificar-lo.

## Dades

- `data/canconers.sqlite3`: cançoners, cançons, versions, autors, mèdia i biblioteca d'elements.
- `data/imatges/`, `data/tipografies/`: imatges i tipografies pujades. `data/cau/`: PDF generats (es
  poden esborrar sense perill). `data/copies/`: còpies de seguretat.
- Les mestres de marges d'enquadernació (`/marges`) són comunes a tots els cançoners.

Més detalls a [docs/dades.md](docs/dades.md).

## Desenvolupament

```bash
python -m pytest                   # tests del servidor (la prova amb Gotenberg s'omet si no està en marxa)
python -m pytest -m "not e2e"     # sense els tests de punta a punta (navegador real, tests/e2e)
./eines/css.sh [--watch]           # compila el CSS de Tailwind (sense Node)
cd frontend && npm install
npm run build                      # Vite: motor de pàgines, Tiptap i components Vue → canconer/static/dist/
npm test                           # Vitest: motor de pàgines i components Vue (Vue Test Utils)
```

Els fitxers compilats (`canconer/static/app.css` i `canconer/static/dist/`) ja vénen fets.

### Frontend: Vue 3 + Pinia

Les pàgines les genera Flask (Jinja); els components Vue es munten on cal amb les funcions `munta…` de
`frontend/src/vue.js`. L'editor (`canconer/static/editor.js`) i els components comparteixen l'store Pinia
`useEditorStore`. Ja són Vue les barres d'eines, els panells (propietats, capes, estils, cançó, acords,
vídeos, llista), el menú del botó dret, l'ajuda, la galeria de mèdia i el selector d'autor.

Referència per al desenvolupament (i per a Claude): [CLAUDE.md](CLAUDE.md),
[docs/arquitectura.md](docs/arquitectura.md), [docs/dades.md](docs/dades.md) i
[docs/escriptori.md](docs/escriptori.md).

```
app.py                     punt d'entrada (desenvolupament)
escriptori.py              llançador de l'app de Mac (servidor, pestanya de Chrome, Dock i barra de menú)
eines/app/                 construcció de Cançoners.app: PyInstaller, icones, signatura i publicació
canconer/
  web.py                   rutes Flask i API JSON
  basedades.py             SQLite: cançons, versions, autors, cançoners, entrades, mèdia; migracions
  plantilles.py            estils, mestres, pàgines especials i plantilla de cançó per defecte
  maquetacio.py            seqüència de pàgines del llibret (regles de paginació)
  disseny.py               validació del disseny que envia l'editor
  document.py, parser.py   format de la lletra (Tiptap): text de webs de tabs, acords i transport
  diagrames.py             diagrames de guitarra i ukulele en SVG
  imposicio.py, marges.py  fulls A4 (cavallet o talla i apila) i marges d'enquadernació
  pdf.py, motor_pdf.py     PDF amb el Chromium local (DevTools) i memòria cau
  cmyk.py, colors.py       PDF per a impremta en CMYK
  copies.py                còpies de seguretat
  actualitzacions.py, actualitzador.py   avís i instal·lació de versions noves
  intercanvi.py            exportar i importar cançoners
  recursos.py              cançoners de base (nadales, populars)
  preferencies.py, tipografies.py, videos.py
  templates/               pàgines web, pàgina d'impressió (imprimible.html) i instruccions
  static/
    pagines.css            estils de les pàgines (compartits per l'editor i la impressió)
    editor.js              editor de pàgines
    visor.js, llibret3d.js visor de PDF (pdf.js) i llibret en 3D
    dist/                  compilat amb Vite: canconer.js (Tiptap + motor de dibuix) i vue.js (components)
frontend/src/              pagines.js (motor de dibuix), editor-canco.js (Tiptap), eines.js, galeria.js,
                           vue.js (muntatge), components/*.vue i stores/ (Pinia)
frontend/tests/            Vitest
tests/                     pytest (tests/e2e: punta a punta amb un Chromium real)
```
