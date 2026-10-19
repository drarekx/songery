# App de Mac (`escriptori.py`)

`Cançoners.app` (PyInstaller, `eines/app/canconers.spec`) arrenca el servidor Flask i el deixa a la barra
de menú (rumps) i al Dock. Construir i publicar: skill `publica-versio`.

## Port i instància

- `tria_port`: el port de l'última vegada (`configuracio.json`) o el primer lliure de `PORTS`
  (48650–48659). Un port aleatori, si tots són ocupats, no es desa.
- `servidor.json` (url, pid) diu que l'app és oberta. `instancia_oberta` ho comprova amb
  `/api/identitat` (app, carpeta de dades i pid): un altre servidor al mateix port no es confon amb l'app.
  Si ja n'hi ha una d'oberta, la segona només porta al navegador i surt.

## Navegador

Cançoners s'obre en una **pestanya** del Chrome de l'usuari (o Edge, Brave, Chromium; si no n'hi ha cap,
el navegador per defecte). No hi ha finestra pròpia.

- Tornar a obrir l'app (Dock, Finder, menú) va a la pestanya que ja hi ha en lloc d'obrir-ne una altra:
  `_pestanya_oberta` la busca amb ScriptingBridge. Hi parla pel **número de procés** del Chrome de
  l'usuari (`es_el_de_l_usuari`: sense `--headless` ni `--user-data-dir`), perquè pel nom macOS podria
  triar el Chrome invisible dels PDF.
- Cal el permís d'automatització: `com.apple.security.automation.apple-events` a
  `eines/app/permisos.plist` i `NSAppleEventsUsageDescription` a l'Info.plist. La primera vegada macOS
  el demana; sense permís, cada vegada s'obre una pestanya nova.
- `tanca_navegador_antic`: fins a la 1.5.4 l'app obria un Chrome propi (`<dades>/navegador`). En arrencar
  es tanca (amb `Browser.close`) i se n'esborra el perfil.

## Barra de menú

«Obre Cançoners», «Obre la carpeta de dades», la versió, «Cerca actualitzacions…», «Fes una còpia de
seguretat ara», «Còpies de seguretat…» (pàgina `/copies`) i «Surt».

## Actualitzacions

`canconer/actualitzacions.py` mira GitHub Releases en obrir l'app i cada dia. `canconer/actualitzador.py`
fa l'actualització des de `/actualitzacio`: còpia de seguretat, baixada (sense compressió HTTP), verificació
de la signatura (equip `3HWTS4AVPU`), instal·lació amb un script que torna a l'app anterior si la nova no
arrenca, i reinici. Detalls i errors que ja han passat: skill `publica-versio`.
