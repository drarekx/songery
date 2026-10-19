# Dades

Carpeta de dades: `data/` en desenvolupament, `~/Library/Application Support/Cançoners` a l'app de Mac
(`CANCONER_DADES` la canvia). Tot el que hi ha és de l'usuari.

| Què | On |
|---|---|
| Base de dades SQLite | `canconers.sqlite3` |
| Imatges (la mèdia) | `imatges/` |
| Tipografies importades | `tipografies/` |
| PDF generats (es poden esborrar) | `cau/` |
| Còpies de seguretat | `copies/AAAA-MM-DD_HHMMSS_vX.Y.Z_motiu.zip` |
| Preferències de l'usuari | `preferencies.json` (`canconer/preferencies.py`) |
| Registres | `canconers.log`, `errors.log`, `actualitzacio.log` |

## Base de dades (`canconer/basedades.py`)

- `canco` (també les pàgines lliures, `tipus`) i `versio` (historial). El contingut és JSON (pàgines
  amb elements). `canco.autor_id` → `autor`.
- `canconer` (`dades` JSON: títol, opcions, estils, mestres, especials) i `entrada` (cançons d'un
  cançoner, ordre, versió fixada, transport, inici).
- `imatge` i `carpeta_media`: la **mèdia**, compartida per totes les cançons i cançoners, que hi apunten
  per l'id (camps `src`). La carpeta és només per ordenar: moure-la no canvia cap cançó.
  `usos_imatges()` diu on es fa servir cada imatge; no se n'esborra cap que es faci servir.
  Només es poden pujar PNG, JPEG, WEBP i GIF (`puja_imatge`, que mira el contingut del fitxer). Les SVG
  antigues o importades es continuen servint, amb una CSP que no deixa executar res.
- `marge`: mestres de marges (comunes a tots els cançoners). `tipografia`: tipografies importades.
  `element`: biblioteca d'elements.
- Paperera de cançons i cançoners (columna `paperera`).

### Migracions

`PRAGMA user_version` és la versió de l'esquema; `MIGRACIONS` les aplica en ordre en obrir la base de
dades, totes en una transacció, i abans en fa una còpia de seguretat. N'hi ha 7 (l'última:
`_afegeix_media`). Cada esquema publicat és a `tests/fixtures/esquemes/` i el prova
`test_actualitzacio_dades.py`.

## Còpies de seguretat (`canconer/copies.py`)

Zip amb la base de dades (API de còpia de SQLite), les imatges i les tipografies. Se'n fa una abans de
cada actualització i de cada migració, i des del menú. Es conserven les 10 últimes, totes les dels
últims 30 dies (fins a 60), i mai s'esborra la més recent que té dades. La pàgina `/copies` les mostra,
en permet veure el contingut i restaurar-ne una (abans en desa una de l'estat actual).

## Intercanvi (`canconer/intercanvi.py`)

Exportar i importar un cançoner amb les seves imatges i tipografies (fitxer `.canconer`). En importar,
les imatges reben ids nous i les referències es reescriuen.
