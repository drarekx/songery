# Cançoners

App per dissenyar cançoners en llibret A5 (lletra i acords) i treure'n el PDF per imprimir. Flask +
SQLite al servidor, Vue 3 + Pinia a l'editor, i el PDF el fa un Chromium invisible amb el mateix codi
que dibuixa l'editor. Es reparteix com a app de Mac (`Cançoners.app`, PyInstaller) per GitHub Releases.

Tot en català: interfície, codi (noms de funcions i variables), comentaris, commits i documentació.

## Ordres

```bash
python app.py                       # desenvolupament: http://127.0.0.1:5180, es recarrega sol
python -m pytest -q                 # servidor + tests de punta a punta (tests/e2e, Chromium real)
cd frontend && npm run build        # Vite → canconer/static/dist/ (cal després de tocar frontend/src)
cd frontend && npx vitest run       # tests del frontend
bash eines/css.sh                   # Tailwind → canconer/static/app.css (cal després de tocar classes)
```

`dist/` i `app.css` són al repositori: s'han de construir i pujar amb els canvis.

## Regles

- **Mai pugis `data/`**: són els cançoners de l'usuari (dades del servidor de desenvolupament).
- **Publicar una versió, actualitzacions, signatura o migracions**: segueix la skill
  `.claude/skills/publica-versio/SKILL.md`. Un error a l'actualitzador d'una versió publicada només
  s'arregla reinstal·lant a mà.
- **Migracions** (`MIGRACIONS` a `canconer/basedades.py`): només al final, no destructives, idempotents.
  Abans d'afegir-ne una, desa l'esquema actual a `tests/fixtures/esquemes/esquema-N.sql`.
- **Fitxers estàtics a les plantilles**: sempre `estatic('…')` (adreça amb la versió, `/v/<versió>/…`),
  mai `url_for('static', …)`: si no, després d'actualitzar el navegador fa servir JavaScript antic.
- **Proves de l'app empaquetada** amb un `HOME` fals i `CANCONER_NO_OBRIS=1`. Amb un `HOME` fals el PDF
  no es pot provar (Chrome no dibuixa la pàgina): prova'l amb el `HOME` normal i unes dades a part
  (`CANCONER_DADES=… python app.py --port …`).
- Les credencials (signatura, notarització) són al clauer; no en desis mai cap.
- Comprova els canvis d'interfície al navegador (captures amb el Chromium dels tests e2e) abans de
  dir que funcionen.

## Referència

- [docs/arquitectura.md](docs/arquitectura.md): com es dibuixen les pàgines, l'editor (editor.js + Vue),
  la maquetació del llibret, la imposició i el PDF.
- [docs/dades.md](docs/dades.md): base de dades, migracions, mèdia (imatges i carpetes), autors,
  còpies de seguretat i preferències.
- [docs/escriptori.md](docs/escriptori.md): l'app de Mac: port, pestanya de Chrome, Dock, barra de menú
  i actualitzador.
- [README.md](README.md): què fa l'app, per a qui la fa servir.
