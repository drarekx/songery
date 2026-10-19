---
name: publica-versio
description: Publicar una versió nova de Cançoners (l'app de Mac) i entendre com s'actualitza a les màquines dels usuaris, per no trencar-ho. Fes-la servir quan calgui publicar una versió («fes la nova versió», «publica-la»), quan es toqui el codi d'actualització, instal·lació, signatura o migracions de dades, o quan un usuari digui que l'actualització li falla.
---

# Publicar una versió de Cançoners sense trencar res

Cançoners és una app Flask empaquetada amb PyInstaller com a `Cançoners.app` (signada amb Developer ID,
Team `3HWTS4AVPU`) i publicada a GitHub Releases (`drarekx/songery`). Els usuaris l'actualitzen des de la
mateixa app o tornant a executar `install.sh`. Un error a la cadena d'actualització és el pitjor que pot
passar: **la versió que té l'usuari és la que s'ha d'actualitzar a si mateixa**, així que un error a
l'actualitzador d'una versió publicada només es pot arreglar fent que l'usuari reinstal·li a mà.

## Procés de publicació (en aquest ordre)

1. **Només el que està acabat i provat.** `git status` ha d'estar net abans de començar (sense contar
   `data/`). Si hi ha feina a mitges, o es fa commit de la part acabada i la resta es deixa fora, o no es
   publica. `construeix.sh` empaqueta **el directori de treball tal com és**, no l'últim commit.
2. **Frontend construït.** `construeix.sh` NO executa Vite: l'app fa servir `canconer/static/dist/`, que
   és al repositori. Després de tocar `frontend/src`, cal `cd frontend && npm run build`, i després de
   tocar classes de Tailwind o `static/src/app.css`, `bash eines/css.sh`. Fes commit de `dist/` i
   `static/app.css`.
3. **Tests.** `.venv/bin/python -m pytest -q` (inclou els de punta a punta de `tests/e2e`, amb un Chromium
   real; se salten si no n'hi ha) i `cd frontend && npx vitest run`. Tot ha de passar.
4. **Versió.** `echo X.Y.Z > eines/app/VERSIO`, `git commit -am "Versió X.Y.Z"`, `git push`. És el número que
   surt al peu de la web i el que compara l'actualitzador (`actualitzacions.es_mes_nova`): ha de ser més
   gran que l'anterior. Mai repetir-ne un (`publica.sh` s'atura si l'etiqueta ja existeix).
5. **Publicar.** `./eines/app/publica.sh` (triga uns minuts; redirigeix la sortida a un fitxer i mira'n el
   final). Fa: `construeix.sh` (icones, Ghostscript, PyInstaller, signatura, `.dmg`) → `ditto` el `.app` a
   `dist/Canconers.zip` → `gh release create vX.Y.Z dist/Canconers.zip dist/Cançoners.dmg`.
   - Ha d'acabar amb `✓ Publicada: …/releases/tag/vX.Y.Z`.
   - La notarització és opcional (`CANCONER_NOTARITZA=1`, perfil del clauer «canconers»); no cal per a
     `install.sh` ni per a l'actualitzador. **No es desen mai contrasenyes**: les credencials són al clauer.
6. **Comprovar el paquet** quan s'hagi tocat res de l'empaquetat: per exemple,
   `find "dist/Cançoners.app" -name cacert.pem` (els certificats de certifi han de ser-hi) i
   `codesign -dv "dist/Cançoners.app" 2>&1 | grep TeamIdentifier`.

Mai es puja `data/` (són els cançoners de l'usuari).

## Com s'actualitza una màquina (el que no es pot trencar)

**Avís de versió nova**: `canconer/actualitzacions.py` consulta l'API de GitHub (`releases/latest`) amb
`urllib` i compara `tag_name` amb `eines/app/VERSIO`.

**Actualització des de l'app** (`canconer/actualitzador.py`, progrés a `/actualitzacio`):
1. `copia`: còpia de seguretat de les dades (`copies.fes_copia`); si falla, no es continua.
2. `baixada`: busca a la release l'actiu que es diu **exactament `Canconers.zip`** i el baixa amb
   `requests` (sense compressió HTTP, se'n comprova la mida, un reintent).
3. `verificacio`: `ditto -x -k`, `codesign --verify --deep --strict` i `TeamIdentifier=3HWTS4AVPU`.
4. `installacio`: un script de bash espera que l'app es tanqui, mou l'antiga a un temporal, posa la nova,
   la obre i espera que `servidor.json` de la carpeta de dades indiqui que respon. **Si en un minut no
   arrenca, torna a posar l'antiga** i ho deixa escrit a `actualitzacio-fallida.json`.
5. `reinici`: `escriptori.py` tanca l'app quan veu `estat["sortir"]`.

**Reinstal·lació a mà** (també per arreglar una màquina amb un actualitzador trencat):
`curl -fsSL https://raw.githubusercontent.com/drarekx/songery/main/install.sh | bash`. Baixa
`releases/latest/download/Canconers.zip` amb `curl`, comprova la signatura i l'equip, substitueix l'app i
torna a l'anterior si la nova no arrenca. Les dades (`~/Library/Application Support/Cançoners`) no es
toquen. `install.sh` es llegeix de la branca `main`: un canvi a `install.sh` afecta tothom de seguida.

**Dades**: en obrir-se, `basedades._aplica_migracions` aplica les migracions pendents (`MIGRACIONS`,
versió de l'esquema a `PRAGMA user_version`), amb còpia de seguretat abans i tot en una transacció.

**Protecció contra «s'ha esborrat tot»**: si l'inici no troba cap cançoner ni cap cançó però hi ha una
còpia de seguretat amb dades (`copies.ultima_amb_dades`), ho avisa i ofereix restaurar-la
(`POST /copies/restaura`, que abans guarda l'estat actual). La neteja de còpies antigues (se'n conserven 5)
no esborra mai la més recent que té dades. També es poden restaurar des de la barra de menú
(«Restaura una còpia…»).

## Errors que ja han passat (i com evitar-los)

- **`CERTIFICATE_VERIFY_FAILED`** dins l'app: el Python empaquetat no troba els certificats del sistema.
  Tota petició HTTPS amb `urllib` ha de passar `context=actualitzacions.context_ssl()` (certifi). `requests`
  ja fa servir certifi.
- **`Error -3 while decompressing data: incorrect header check`**: xarxes, proxies o antivirus que marquen
  la resposta com a comprimida sense ser-ho. Les baixades demanen `Accept-Encoding: identity` i desen el
  flux en cru (`r.raw.stream(..., decode_content=False)`), i se'n comprova la mida.
- **«L'app descarregada no està signada per l'equip esperat»** a l'atzar: `codesign -dv | grep -q` amb
  `pipefail` rebia SIGPIPE. Primer es desa la sortida en una variable i després s'hi busca.
- **Error 500 després d'actualitzar el codi**: plantilles noves amb Python antic. A la web, el context de les
  plantilles ha de tolerar valors que falten (`| default(...)`). En desenvolupament, `python app.py` es
  recarrega sol (`--sense-recarrega` per evitar-ho).
- **PDF desactualitzats**: l'empremta de la memòria cau (`pdf.empremta`) ha d'incloure tot el codi del motor
  de dibuix (`dist/canconer.js` i `dist/trossos/*.js`).
- **Publicar feina a mitges**: vegeu el pas 1. Si una funció no està acabada, que no entri a la versió.
- **«S'ha esborrat tot» després d'actualitzar** (1.4.5, en un altre Mac): un cop acabada l'actualització, les
  dades hi eren. Per això hi ha la protecció de l'inici i els tests d'actualització des de cada esquema. Si
  passa, primer comprova la carpeta de dades i `copies/` (no restauris ni creïs res a cegues):
  `ls -la "$HOME/Library/Application Support/Cançoners" "$HOME/Library/Application Support/Cançoners/copies"`
  i llegeix `actualitzacio.log` i `errors.log`.

## Si toques l'actualitzador, l'instal·lador, la signatura o les migracions

- Pensa en **la versió que té instal·lada l'usuari**: el codi nou de l'actualitzador només s'executa a
  partir de la versió següent. Si l'arreglament és per a un error de l'actualitzador, digues a l'usuari que
  reinstal·li amb `install.sh` les màquines afectades.
- No canviïs el nom de l'actiu (`Canconers.zip`), l'etiqueta (`vX.Y.Z`), el Team ID ni el camí de les dades
  sense mantenir la compatibilitat amb les versions ja publicades.
- Migracions: només s'afegeixen al final de `MIGRACIONS`, no destructives (afegir columnes o files, no
  esborrar dades) i idempotents. **Abans d'afegir-ne una**, desa l'esquema de la base de dades de l'última
  versió publicada a `tests/fixtures/esquemes/esquema-N.sql` (N = la `user_version` d'aquella versió; només
  l'estructura: `sqlite3 <base de dades> .schema`, sense dades de ningú). `tests/test_actualitzacio_dades.py`
  crea una base de dades amb cada esquema, la migra amb el codi actual i comprova que no es perd res
  (cançoners, cançons, versions, portades retocades) i que les pàgines funcionen; un altre test falla si
  falta l'esquema de l'última versió.
- Prova-ho abans de publicar:
  - `tests/test_actualitzador.py` (inclou un servidor que fingeix compressió gzip) i
    `tests/test_copies_i_actualitzacions.py` (còpies, comparació de versions i certificats).
  - Per simular una versió antiga: `CANCONER_VERSIO=1.0.0`.
  - Per provar el procés sencer sense tocar l'app de debò: un `HOME` temporal i un `open` fals al `PATH`.
- Després de publicar, comprova que la baixada real funciona:
  `actualitzador.baixa(<browser_download_url>, desti, mida)` amb l'actiu de la release nova.
