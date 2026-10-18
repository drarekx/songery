"""Emmagatzematge en SQLite: biblioteca de cançons amb versions, cançoners i imatges.

Model:
  - canco: una cançó de la biblioteca (o una pàgina lliure, si tipus = 'pagina'). El contingut són
    les seves pàgines dissenyades (vegeu plantilles.py). Té un *esborrany* (l'estat que s'edita) i
    un historial de versions immutables.
  - versio: fotografia d'una cançó (títol, autor i document) en un moment donat.
  - canconer: dades de la portada, opcions i disseny (JSON).
  - entrada: una cançó dins d'un cançoner, amb la posició, si surt al PDF, el transport, la
    versió fixada (NULL = segueix l'esborrany, és a dir, sempre l'última) i si ha de començar a
    l'esquerra o on toqui.
  - imatge: fitxers pujats (es desen a data/imatges/).
  - element: elements de disseny desats per reutilitzar-los (biblioteca d'elements).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from . import document, marges as marges_, plantilles

DIRECTORI = Path(os.environ.get("CANCONER_DADES", Path(__file__).resolve().parent.parent / "data"))

# Si l'esborrany fa més d'aquest temps que no es desa com a versió, en desar-lo se'n fa una còpia
# a l'historial automàticament (així l'historial no s'omple amb cada tecla).
INTERVAL_VERSIO_AUTOMATICA = timedelta(minutes=10)

VALORS_PER_DEFECTE = {
    "titol": "Cançoner",
    "subtitol": "",
    "any": "",
    "contraportada": "",
    "pagina_acords": False,
    "posicio_acords": "inici",  # inici (després de l'índex) o final (abans de la contraportada)
    "instrument": "guitarra",  # guitarra o ukulele
    # estils, mestres i especials: vegeu plantilles.amb_valors_per_defecte
}

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS canco (
    id TEXT PRIMARY KEY,
    titol TEXT NOT NULL DEFAULT '',
    autor TEXT NOT NULL DEFAULT '',
    doc TEXT NOT NULL,
    creada TEXT NOT NULL,
    actualitzada TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS versio (
    id TEXT PRIMARY KEY,
    canco_id TEXT NOT NULL REFERENCES canco(id) ON DELETE CASCADE,
    numero INTEGER NOT NULL,
    titol TEXT NOT NULL,
    autor TEXT NOT NULL,
    doc TEXT NOT NULL,
    nota TEXT NOT NULL DEFAULT '',
    creada TEXT NOT NULL,
    UNIQUE (canco_id, numero)
);
CREATE TABLE IF NOT EXISTS canconer (
    id TEXT PRIMARY KEY,
    dades TEXT NOT NULL,
    creat TEXT NOT NULL,
    actualitzat TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entrada (
    canconer_id TEXT NOT NULL REFERENCES canconer(id) ON DELETE CASCADE,
    canco_id TEXT NOT NULL REFERENCES canco(id) ON DELETE CASCADE,
    posicio INTEGER NOT NULL,
    versio_id TEXT REFERENCES versio(id) ON DELETE SET NULL,
    inclosa INTEGER NOT NULL DEFAULT 1,
    transport INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (canconer_id, canco_id)
);
CREATE TABLE IF NOT EXISTS element (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    dades TEXT NOT NULL,
    creat TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tipografia (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    fitxer TEXT NOT NULL,
    format TEXT NOT NULL,
    pes INTEGER NOT NULL DEFAULT 400,
    estil TEXT NOT NULL DEFAULT 'normal',
    creada TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS imatge (
    id TEXT PRIMARY KEY,
    fitxer TEXT NOT NULL,
    tipus TEXT NOT NULL,
    nom TEXT NOT NULL DEFAULT '',
    creada TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS marge (
    id TEXT PRIMARY KEY,
    dades TEXT NOT NULL,
    creat TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_versio_canco ON versio (canco_id, numero);
CREATE INDEX IF NOT EXISTS idx_entrada_canco ON entrada (canco_id);
"""

_ID_VALID = re.compile(r"^[a-z0-9]{1,32}$")
_inicialitzades: set[Path] = set()


def nou_id() -> str:
    return uuid.uuid4().hex[:12]


def ara() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _valida(identificador: str) -> str:
    if not isinstance(identificador, str) or not _ID_VALID.match(identificador):
        raise KeyError(identificador)
    return identificador


@contextmanager
def connexio():
    """Connexió amb transacció: es confirma en sortir o es desfà si hi ha un error."""
    DIRECTORI.mkdir(parents=True, exist_ok=True)
    cami = DIRECTORI / "canconers.sqlite3"
    existia = cami.exists()
    con = sqlite3.connect(cami, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        if cami not in _inicialitzades:
            con.execute("PRAGMA journal_mode = WAL")
            con.executescript(_ESQUEMA)
            _aplica_migracions(con, existia)
            _migra_json(con)
            _migra_a_pagines(con)
            _inicialitzades.add(cami)
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ---------------------------------------------------------------- Cançoners


def _meta(dades: str | dict) -> dict:
    meta = json.loads(dades) if isinstance(dades, str) else dict(dades)
    return plantilles.amb_valors_per_defecte({**VALORS_PER_DEFECTE, **meta})


def llista_canconers() -> list[dict]:
    with connexio() as con:
        files = con.execute("""
            SELECT c.id, c.dades, c.actualitzat, COUNT(e.canco_id) AS n
            FROM canconer c LEFT JOIN entrada e ON e.canconer_id = c.id
            GROUP BY c.id ORDER BY c.actualitzat DESC""").fetchall()
    return [{**_meta(f["dades"]), "id": f["id"], "n_cancons": f["n"], "actualitzat": f["actualitzat"]}
            for f in files]


def crea_canconer(titol: str, **meta) -> str:
    identificador = nou_id()
    dades = {"titol": titol or "Cançoner", "any": str(date.today().year), **meta}
    with connexio() as con:
        con.execute("INSERT INTO canconer (id, dades, creat, actualitzat) VALUES (?, ?, ?, ?)",
                    (identificador, json.dumps(dades, ensure_ascii=False), ara(), ara()))
    return identificador


def meta_canconer(id_canconer: str) -> dict:
    with connexio() as con:
        fila = con.execute("SELECT dades FROM canconer WHERE id = ?", (_valida(id_canconer),)).fetchone()
    if not fila:
        raise KeyError(id_canconer)
    return {**_meta(fila["dades"]), "id": id_canconer}


def copia_mestres(id_desti: str, id_origen: str, ids_mestres: list[str]) -> list[dict]:
    """Copia pàgines mestres d'un altre cançoner (amb els estils de text que facin servir i que no hi siguin).

    Retorna les mestres noves. Si un id ja existeix al destí, la còpia en rep un de nou.
    """
    origen, desti = meta_canconer(id_origen), meta_canconer(id_desti)
    mestres, estils = list(desti["mestres"]), dict(desti["estils"])
    ocupats = {m["id"] for m in mestres}
    noves = []
    for m in origen["mestres"]:
        if m["id"] not in ids_mestres or len(mestres) >= 20:
            continue
        copia = json.loads(json.dumps(m))
        if copia["id"] in ocupats:
            copia["id"] = nou_id()
        ocupats.add(copia["id"])
        for costat in ("parell", "senar"):
            for e in copia[costat]["elements"]:
                if e.get("estil") in origen["estils"] and e["estil"] not in estils:
                    estils[e["estil"]] = origen["estils"][e["estil"]]
        mestres.append(copia)
        noves.append(copia)
    if noves:
        desa_meta(id_desti, {"mestres": mestres, "estils": estils})
    return noves


def desa_meta(id_canconer: str, canvis: dict) -> dict:
    """Actualitza les dades del cançoner (només les claus que es passen)."""
    meta = meta_canconer(id_canconer)
    meta.update(canvis)
    meta.pop("id", None)
    with connexio() as con:
        con.execute("UPDATE canconer SET dades = ?, actualitzat = ? WHERE id = ?",
                    (json.dumps(meta, ensure_ascii=False), ara(), id_canconer))
    return {**meta, "id": id_canconer}


def toca_canconer(con, id_canconer: str) -> None:
    con.execute("UPDATE canconer SET actualitzat = ? WHERE id = ?", (ara(), id_canconer))


def esborra_canconer(id_canconer: str) -> None:
    """Esborra el cançoner. Les cançons es queden a la biblioteca."""
    with connexio() as con:
        con.execute("DELETE FROM canconer WHERE id = ?", (_valida(id_canconer),))


def carrega_canconer(id_canconer: str) -> dict:
    """Cançoner complet per a la web i la maquetació.

    Cada cançó porta el contingut que toca segons l'entrada: la versió fixada o l'esborrany.
    """
    meta = meta_canconer(id_canconer)
    with connexio() as con:
        files = con.execute("""
            SELECT e.canco_id, e.versio_id, e.inclosa, e.transport, e.inici, c.tipus,
                   c.titol AS e_titol, c.autor AS e_autor, c.doc AS e_doc, c.actualitzada,
                   v.numero AS v_numero, v.titol AS v_titol, v.autor AS v_autor, v.doc AS v_doc,
                   (SELECT MAX(numero) FROM versio WHERE canco_id = c.id) AS ultima,
                   (SELECT doc = c.doc AND titol = c.titol AND autor = c.autor FROM versio
                     WHERE canco_id = c.id ORDER BY numero DESC LIMIT 1) AS sense_canvis,
                   (SELECT COUNT(*) FROM entrada e2 WHERE e2.canco_id = c.id) AS usos
            FROM entrada e JOIN canco c ON c.id = e.canco_id
            LEFT JOIN versio v ON v.id = e.versio_id
            WHERE e.canconer_id = ? ORDER BY e.posicio""", (id_canconer,)).fetchall()
    cancons = []
    for f in files:
        fixada = f["versio_id"] is not None
        cancons.append({
            "id": f["canco_id"],
            "titol": f["v_titol"] if fixada else f["e_titol"],
            "autor": f["v_autor"] if fixada else f["e_autor"],
            "contingut": plantilles.normalitza_contingut(json.loads(f["v_doc"] if fixada else f["e_doc"])),
            "tipus": f["tipus"],
            "inici": f["inici"],
            "transport": f["transport"],
            "inclosa": bool(f["inclosa"]),
            "versio_id": f["versio_id"],
            "versio_numero": f["v_numero"],
            "versio_ultima": f["ultima"] or 0,
            # L'esborrany té canvis que no són a cap versió.
            "esborrany_modificat": not f["sense_canvis"],
            "usos": f["usos"],
        })
    return {**meta, "cancons": cancons}


# ---------------------------------------------------------------- Entrades


def _ids_entrades(con, id_canconer: str) -> list[str]:
    return [f[0] for f in con.execute(
        "SELECT canco_id FROM entrada WHERE canconer_id = ? ORDER BY posicio", (id_canconer,))]


def _reordena(con, id_canconer: str, ids: list[str]) -> None:
    for posicio, id_canco in enumerate(ids):
        con.execute("UPDATE entrada SET posicio = ? WHERE canconer_id = ? AND canco_id = ?",
                    (posicio, id_canconer, id_canco))


def afegeix_entrada(id_canconer: str, id_canco: str, versio_id: str | None = None,
                    despres_de: str | None = None) -> None:
    meta_canconer(id_canconer)
    with connexio() as con:
        ids = _ids_entrades(con, id_canconer)
        if id_canco in ids:
            return
        posicio = ids.index(despres_de) + 1 if despres_de in ids else len(ids)
        ids.insert(posicio, id_canco)
        con.execute("INSERT INTO entrada (canconer_id, canco_id, posicio, versio_id) VALUES (?, ?, ?, ?)",
                    (id_canconer, id_canco, posicio, versio_id))
        _reordena(con, id_canconer, ids)
        toca_canconer(con, id_canconer)


def treu_entrada(id_canconer: str, id_canco: str) -> None:
    """Treu la cançó del cançoner. Si ja no és a cap cançoner, es queda igualment a la biblioteca."""
    with connexio() as con:
        con.execute("DELETE FROM entrada WHERE canconer_id = ? AND canco_id = ?", (id_canconer, id_canco))
        _reordena(con, id_canconer, _ids_entrades(con, id_canconer))
        toca_canconer(con, id_canconer)


def ordena_entrades(id_canconer: str, ordre: list[str]) -> bool:
    with connexio() as con:
        if sorted(ordre) != sorted(_ids_entrades(con, id_canconer)):
            return False
        _reordena(con, id_canconer, ordre)
        toca_canconer(con, id_canconer)
    return True


def actualitza_entrada(id_canconer: str, id_canco: str, **canvis) -> None:
    """canvis: inclosa (bool), transport (int), versio_id (id o None = esborrany) i/o inici."""
    camps = {k: v for k, v in canvis.items() if k in ("inclosa", "transport", "versio_id", "inici")}
    if not camps:
        return
    with connexio() as con:
        if camps.get("versio_id"):
            fila = con.execute("SELECT 1 FROM versio WHERE id = ? AND canco_id = ?",
                               (camps["versio_id"], id_canco)).fetchone()
            if not fila:
                raise KeyError(camps["versio_id"])
        assignacions = ", ".join(f"{k} = ?" for k in camps)
        cur = con.execute(f"UPDATE entrada SET {assignacions} WHERE canconer_id = ? AND canco_id = ?",
                          (*camps.values(), id_canconer, id_canco))
        if cur.rowcount == 0:
            raise KeyError(id_canco)
        toca_canconer(con, id_canconer)


# ---------------------------------------------------------------- Cançons i versions


def crea_canco(titol: str = "", autor: str = "", contingut: dict | None = None, tipus: str = "canco") -> str:
    """Crea una cançó (o una pàgina lliure). El contingut pot ser de pàgines o un document sol."""
    identificador = nou_id()
    if contingut is None:
        contingut = plantilles.canco_nova() if tipus == "canco" else {
            "format": 2, "pagines": [plantilles.pagina([])]}
    contingut = plantilles.normalitza_contingut(contingut)
    with connexio() as con:
        con.execute("INSERT INTO canco (id, titol, autor, doc, creada, actualitzada, tipus) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (identificador, titol, autor, json.dumps(contingut, ensure_ascii=False), ara(), ara(), tipus))
    return identificador


def carrega_canco(id_canco: str) -> dict:
    with connexio() as con:
        fila = con.execute("SELECT * FROM canco WHERE id = ?", (_valida(id_canco),)).fetchone()
        if not fila:
            raise KeyError(id_canco)
        ultima = con.execute("SELECT * FROM versio WHERE canco_id = ? ORDER BY numero DESC LIMIT 1",
                             (id_canco,)).fetchone()
    return {
        "id": fila["id"], "titol": fila["titol"], "autor": fila["autor"], "tipus": fila["tipus"],
        "contingut": plantilles.normalitza_contingut(json.loads(fila["doc"])),
        "creada": fila["creada"], "actualitzada": fila["actualitzada"],
        "versio_ultima": ultima["numero"] if ultima else 0,
        "esborrany_modificat": not ultima or (ultima["doc"], ultima["titol"], ultima["autor"])
        != (fila["doc"], fila["titol"], fila["autor"]),
    }


def _crea_versio(con, id_canco: str, nota: str = "") -> dict | None:
    """Desa l'esborrany actual com a versió nova, si és diferent de l'última."""
    fila = con.execute("SELECT titol, autor, doc FROM canco WHERE id = ?", (id_canco,)).fetchone()
    ultima = con.execute("SELECT numero, titol, autor, doc FROM versio WHERE canco_id = ? "
                         "ORDER BY numero DESC LIMIT 1", (id_canco,)).fetchone()
    if ultima and (ultima["titol"], ultima["autor"], ultima["doc"]) == (fila["titol"], fila["autor"], fila["doc"]):
        if nota:  # mateix contingut: només s'hi afegeix la nota
            con.execute("UPDATE versio SET nota = ? WHERE canco_id = ? AND numero = ?",
                        (nota, id_canco, ultima["numero"]))
        return None
    numero = (ultima["numero"] if ultima else 0) + 1
    identificador = nou_id()
    con.execute("INSERT INTO versio (id, canco_id, numero, titol, autor, doc, nota, creada) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (identificador, id_canco, numero, fila["titol"], fila["autor"], fila["doc"], nota, ara()))
    return {"id": identificador, "numero": numero}


def crea_versio(id_canco: str, nota: str = "") -> dict | None:
    with connexio() as con:
        if not con.execute("SELECT 1 FROM canco WHERE id = ?", (_valida(id_canco),)).fetchone():
            raise KeyError(id_canco)
        return _crea_versio(con, id_canco, nota)


def ultima_versio(id_canco: str) -> dict:
    """Retorna l'última versió, creant-ne una si l'esborrany té canvis (per fixar-la en importar)."""
    with connexio() as con:
        _crea_versio(con, id_canco)
        fila = con.execute("SELECT id, numero FROM versio WHERE canco_id = ? ORDER BY numero DESC LIMIT 1",
                           (id_canco,)).fetchone()
    return {"id": fila["id"], "numero": fila["numero"]}


def desa_esborrany(id_canco: str, titol: str | None = None, autor: str | None = None,
                   contingut: dict | None = None) -> None:
    """Desa l'esborrany. Si fa estona de l'última versió, abans en guarda una còpia a l'historial."""
    with connexio() as con:
        fila = con.execute("SELECT * FROM canco WHERE id = ?", (_valida(id_canco),)).fetchone()
        if not fila:
            raise KeyError(id_canco)
        ultima = con.execute("SELECT creada FROM versio WHERE canco_id = ? ORDER BY numero DESC LIMIT 1",
                             (id_canco,)).fetchone()
        referencia = datetime.fromisoformat(ultima["creada"] if ultima else fila["creada"])
        if datetime.now() - referencia > INTERVAL_VERSIO_AUTOMATICA:
            _crea_versio(con, id_canco, "Desada automàticament")
        con.execute("UPDATE canco SET titol = ?, autor = ?, doc = ?, actualitzada = ? WHERE id = ?", (
            fila["titol"] if titol is None else titol,
            fila["autor"] if autor is None else autor,
            fila["doc"] if contingut is None else json.dumps(plantilles.normalitza_contingut(contingut), ensure_ascii=False),
            ara(), id_canco))
        for e in con.execute("SELECT canconer_id FROM entrada WHERE canco_id = ? AND versio_id IS NULL",
                             (id_canco,)).fetchall():
            toca_canconer(con, e["canconer_id"])


def versions(id_canco: str) -> list[dict]:
    with connexio() as con:
        files = con.execute("SELECT id, numero, titol, nota, creada FROM versio WHERE canco_id = ? "
                            "ORDER BY numero DESC", (_valida(id_canco),)).fetchall()
    return [dict(f) for f in files]


def carrega_versio(id_versio: str) -> dict:
    with connexio() as con:
        fila = con.execute("SELECT * FROM versio WHERE id = ?", (_valida(id_versio),)).fetchone()
    if not fila:
        raise KeyError(id_versio)
    return {**dict(fila), "contingut": plantilles.normalitza_contingut(json.loads(fila["doc"]))}


def restaura_versio(id_canco: str, id_versio: str) -> None:
    """Torna l'esborrany a una versió anterior. L'estat actual es guarda abans a l'historial."""
    versio = carrega_versio(id_versio)
    if versio["canco_id"] != id_canco:
        raise KeyError(id_versio)
    with connexio() as con:
        _crea_versio(con, id_canco, "Abans de restaurar la v%d" % versio["numero"])
        con.execute("UPDATE canco SET titol = ?, autor = ?, doc = ?, actualitzada = ? WHERE id = ?",
                    (versio["titol"], versio["autor"], json.dumps(versio["contingut"], ensure_ascii=False),
                     ara(), id_canco))


ORDRES_BIBLIOTECA = {
    "titol": "c.titol COLLATE NOCASE",
    "autor": "c.autor COLLATE NOCASE, c.titol COLLATE NOCASE",
    "data": "c.actualitzada DESC",
}


def biblioteca(cerca: str = "", ordre: str = "titol") -> list[dict]:
    """Totes les cançons (també les que no són a cap cançoner), amb els cançoners on surten.

    Per a cada cançó: data de l'última modificació, nombre de versions, número de l'última i si
    l'esborrany té canvis que encara no són a cap versió.
    """
    with connexio() as con:
        files = con.execute(f"""
            SELECT c.id, c.titol, c.autor, c.actualitzada,
                   (SELECT MAX(numero) FROM versio WHERE canco_id = c.id) AS ultima,
                   (SELECT COUNT(*) FROM versio WHERE canco_id = c.id) AS n_versions,
                   COALESCE((SELECT NOT (doc = c.doc AND titol = c.titol AND autor = c.autor) FROM versio
                             WHERE canco_id = c.id ORDER BY numero DESC LIMIT 1), 1) AS modificat
            FROM canco c WHERE c.tipus = 'canco'
            ORDER BY {ORDRES_BIBLIOTECA.get(ordre, ORDRES_BIBLIOTECA["titol"])}""").fetchall()
        usos = con.execute("SELECT e.canco_id, k.id, k.dades FROM entrada e "
                           "JOIN canconer k ON k.id = e.canconer_id").fetchall()
    per_canco: dict[str, list] = {}
    for u in usos:
        per_canco.setdefault(u["canco_id"], []).append({"id": u["id"], "titol": json.loads(u["dades"]).get("titol") or "Cançoner"})
    cerca = cerca.strip().lower()
    return [{**dict(f), "modificat": bool(f["modificat"]), "canconers": per_canco.get(f["id"], [])} for f in files
            if not cerca or cerca in f"{f['titol']} {f['autor']}".lower()]


def usos_canco(id_canco: str) -> list[dict]:
    """Cançoners on surt la cançó i quina versió hi fan servir (None = l'esborrany, sempre l'última)."""
    with connexio() as con:
        files = con.execute("""
            SELECT k.id, k.dades, e.versio_id, v.numero FROM entrada e
            JOIN canconer k ON k.id = e.canconer_id LEFT JOIN versio v ON v.id = e.versio_id
            WHERE e.canco_id = ?""", (_valida(id_canco),)).fetchall()
    return [{"id": f["id"], "titol": json.loads(f["dades"]).get("titol") or "Cançoner",
             "versio_id": f["versio_id"], "versio_numero": f["numero"]} for f in files]


def edita_nota_versio(id_versio: str, nota: str) -> None:
    with connexio() as con:
        cur = con.execute("UPDATE versio SET nota = ? WHERE id = ?", (nota[:200], _valida(id_versio)))
        if cur.rowcount == 0:
            raise KeyError(id_versio)


def esborra_canco(id_canco: str) -> None:
    """Esborra la cançó de la biblioteca (i de tots els cançoners)."""
    with connexio() as con:
        con.execute("DELETE FROM canco WHERE id = ?", (_valida(id_canco),))


# ---------------------------------------------------------------- Biblioteca d'elements


def elements_desats() -> list[dict]:
    with connexio() as con:
        files = con.execute("SELECT id, nom, dades, creat FROM element ORDER BY creat DESC").fetchall()
    return [{"id": f["id"], "nom": f["nom"], "elements": json.loads(f["dades"]), "creat": f["creat"]} for f in files]


def desa_element(nom: str, elements: list[dict]) -> str:
    identificador = nou_id()
    with connexio() as con:
        con.execute("INSERT INTO element (id, nom, dades, creat) VALUES (?, ?, ?, ?)",
                    (identificador, nom[:120] or "Element", json.dumps(elements, ensure_ascii=False), ara()))
    return identificador


def esborra_element(id_element: str) -> None:
    with connexio() as con:
        con.execute("DELETE FROM element WHERE id = ?", (_valida(id_element),))


# ---------------------------------------------------------------- Tipografies importades


def _directori_tipografies() -> Path:
    d = DIRECTORI / "tipografies"
    d.mkdir(parents=True, exist_ok=True)
    return d


def desa_tipografia(dades: bytes, format_: str, nom: str, pes: int = 400, estil: str = "normal") -> str:
    """Desa un fitxer de font (ttf, otf, woff o woff2) com una cara de la família «nom»."""
    identificador = nou_id()
    fitxer = f"{identificador}.{format_}"
    (_directori_tipografies() / fitxer).write_bytes(dades)
    with connexio() as con:
        con.execute("INSERT INTO tipografia (id, nom, fitxer, format, pes, estil, creada) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (identificador, nom[:80], fitxer, format_, max(100, min(900, int(pes))),
                     "italic" if estil == "italic" else "normal", ara()))
    return identificador


def tipografies_importades() -> list[dict]:
    with connexio() as con:
        return [dict(f) for f in con.execute("SELECT id, nom, format, pes, estil FROM tipografia ORDER BY nom, pes")]


def fitxer_tipografia(id_tipografia: str) -> tuple[Path, str]:
    with connexio() as con:
        fila = con.execute("SELECT fitxer, format FROM tipografia WHERE id = ?", (_valida(id_tipografia),)).fetchone()
    if not fila:
        raise KeyError(id_tipografia)
    return _directori_tipografies() / fila["fitxer"], fila["format"]


def esborra_tipografia(id_tipografia: str) -> None:
    cami, _ = fitxer_tipografia(id_tipografia)
    with connexio() as con:
        con.execute("DELETE FROM tipografia WHERE id = ?", (id_tipografia,))
    cami.unlink(missing_ok=True)


# ---------------------------------------------------------------- Imatges

TIPUS_IMATGE = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif",
                "image/svg+xml": "svg"}


def _directori_imatges() -> Path:
    d = DIRECTORI / "imatges"
    d.mkdir(parents=True, exist_ok=True)
    return d


def desa_imatge(dades: bytes, tipus: str, nom: str = "") -> str:
    if tipus not in TIPUS_IMATGE:
        raise ValueError(f"Tipus d'imatge no admès: {tipus}")
    identificador = nou_id()
    fitxer = f"{identificador}.{TIPUS_IMATGE[tipus]}"
    (_directori_imatges() / fitxer).write_bytes(dades)
    with connexio() as con:
        con.execute("INSERT INTO imatge (id, fitxer, tipus, nom, creada) VALUES (?, ?, ?, ?, ?)",
                    (identificador, fitxer, tipus, nom[:200], ara()))
    return identificador


def imatge(id_imatge: str) -> tuple[Path, str]:
    """Camí del fitxer i tipus MIME d'una imatge."""
    with connexio() as con:
        fila = con.execute("SELECT fitxer, tipus FROM imatge WHERE id = ?", (_valida(id_imatge),)).fetchone()
    if not fila:
        raise KeyError(id_imatge)
    return _directori_imatges() / fila["fitxer"], fila["tipus"]


# ---------------------------------------------------------------- Migracions


def _aplica_migracions(con, existia: bool) -> None:
    """Aplica en ordre les migracions que falten (la versió de l'esquema és PRAGMA user_version).

    Abans de migrar una base de dades que ja existia se'n fa una còpia de seguretat; si la còpia
    falla, no es toca res. Si una migració falla, es desfà tota la transacció (les dades queden
    com estaven) i l'error diu on és la còpia.
    """
    actual = con.execute("PRAGMA user_version").fetchone()[0]
    pendents = MIGRACIONS[actual:]
    if not pendents:
        return
    copia = None
    if existia and con.execute("SELECT 1 FROM canco UNION ALL SELECT 1 FROM canconer LIMIT 1").fetchone():
        from . import actualitzacions, copies  # aquí per evitar una importació circular
        copia = copies.fes_copia(actualitzacions.versio_actual(), f"abans-de-migrar-{actual}")
    try:
        con.execute("BEGIN")
        for numero, migracio in enumerate(pendents, start=actual + 1):
            migracio(con)
            con.execute(f"PRAGMA user_version = {numero}")
        con.execute("COMMIT")
    except Exception as e:
        con.execute("ROLLBACK")
        on = f" Hi ha una còpia de les dades a {copia}." if copia else ""
        raise RuntimeError(f"No s'han pogut actualitzar les dades ({e}). No s'ha canviat res.{on}") from e


def _afegeix_columnes(con) -> None:
    """Columnes noves en bases de dades creades amb versions anteriors."""
    columnes_canco = {f[1] for f in con.execute("PRAGMA table_info(canco)")}
    if "tipus" not in columnes_canco:
        con.execute("ALTER TABLE canco ADD COLUMN tipus TEXT NOT NULL DEFAULT 'canco'")
    columnes_entrada = {f[1] for f in con.execute("PRAGMA table_info(entrada)")}
    if "inici" not in columnes_entrada:
        con.execute("ALTER TABLE entrada ADD COLUMN inici TEXT NOT NULL DEFAULT 'esquerra'")


def _migra_a_pagines(con) -> None:
    """Converteix les cançons d'un sol document (format anterior) al format de pàgines."""
    for taula in ("canco", "versio"):
        for f in con.execute(f"SELECT id, doc FROM {taula} WHERE doc NOT LIKE '%\"format\": 2%'").fetchall():
            contingut = json.loads(f["doc"])
            if plantilles.es_format_pagines(contingut):
                continue
            nou = json.dumps(plantilles.normalitza_contingut(contingut), ensure_ascii=False)
            con.execute(f"UPDATE {taula} SET doc = ? WHERE id = ?", (nou, f["id"]))



def _migra_json(con) -> None:
    """Importa els cançoners de la versió anterior (data/canconers/*.json) i en mou els fitxers."""
    origen = DIRECTORI / "canconers"
    if not origen.is_dir():
        return
    fitxers = sorted(origen.glob("*.json"))
    if not fitxers:
        return
    desti = DIRECTORI / "canconers-migrats"
    desti.mkdir(exist_ok=True)
    for fitxer in fitxers:
        try:
            antic = json.loads(fitxer.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        id_canconer = antic.get("id") or nou_id()
        if con.execute("SELECT 1 FROM canconer WHERE id = ?", (id_canconer,)).fetchone():
            fitxer.rename(desti / fitxer.name)
            continue
        cancons = antic.pop("cancons", [])
        antic.pop("id", None)
        moment = datetime.fromtimestamp(fitxer.stat().st_mtime).isoformat(timespec="seconds")
        con.execute("INSERT INTO canconer (id, dades, creat, actualitzat) VALUES (?, ?, ?, ?)",
                    (id_canconer, json.dumps(antic, ensure_ascii=False), moment, moment))
        for posicio, c in enumerate(cancons):
            id_canco = c.get("id") if _ID_VALID.match(str(c.get("id", ""))) else nou_id()
            if con.execute("SELECT 1 FROM canco WHERE id = ?", (id_canco,)).fetchone():
                id_canco = nou_id()
            doc = json.dumps(document.de_text(c.get("cos", "")), ensure_ascii=False)
            con.execute("INSERT INTO canco (id, titol, autor, doc, creada, actualitzada) VALUES (?, ?, ?, ?, ?, ?)",
                        (id_canco, c.get("titol", ""), c.get("autor", ""), doc, moment, moment))
            con.execute("INSERT INTO versio (id, canco_id, numero, titol, autor, doc, nota, creada) "
                        "VALUES (?, ?, 1, ?, ?, ?, 'Importada del format antic', ?)",
                        (nou_id(), id_canco, c.get("titol", ""), c.get("autor", ""), doc, moment))
            con.execute("INSERT INTO entrada (canconer_id, canco_id, posicio, transport) VALUES (?, ?, ?, ?)",
                        (id_canconer, id_canco, posicio, int(c.get("transport") or 0)))
        fitxer.rename(desti / fitxer.name)


# ---------------------------------------------------------------- Mestres de marges (globals)


def _sembra_marges(con) -> None:
    """La primera vegada, crea les mestres de marges predefinides."""
    if con.execute("SELECT 1 FROM marge LIMIT 1").fetchone():
        return
    for i, m in enumerate(marges_.PREDEFINIDES):
        con.execute("INSERT INTO marge (id, dades, creat) VALUES (?, ?, ?)",
                    (m["id"], json.dumps(m, ensure_ascii=False), f"{ara()}.{i:03d}"))


def llista_marges() -> list[dict]:
    with connexio() as con:
        files = con.execute("SELECT id, dades FROM marge ORDER BY id != ?, creat", (marges_.SENSE_MARGES,)).fetchall()
    return [marges_.normalitza(json.loads(f["dades"]), f["id"]) for f in files]


def carrega_marge(id_marge: str | None) -> dict:
    """Mestra de marges; si no existeix (o no se'n tria cap), «Sense marges»."""
    with connexio() as con:
        fila = con.execute("SELECT dades FROM marge WHERE id = ?", (str(id_marge or ""),)).fetchone()
    if not fila:
        return marges_.normalitza(marges_.PREDEFINIDES[0], marges_.SENSE_MARGES)
    return marges_.normalitza(json.loads(fila["dades"]), id_marge)


def desa_marge(dades: dict, id_marge: str | None = None) -> str:
    """Crea (sense id) o actualitza una mestra de marges. «Sense marges» no es pot canviar."""
    if id_marge == marges_.SENSE_MARGES:
        raise ValueError("La mestra «Sense marges» no es pot modificar.")
    with connexio() as con:
        if id_marge:
            if not con.execute("SELECT 1 FROM marge WHERE id = ?", (_valida(id_marge),)).fetchone():
                raise KeyError(id_marge)
            con.execute("UPDATE marge SET dades = ? WHERE id = ?",
                        (json.dumps(marges_.normalitza(dades, id_marge), ensure_ascii=False), id_marge))
            return id_marge
        id_marge = nou_id()
        con.execute("INSERT INTO marge (id, dades, creat) VALUES (?, ?, ?)",
                    (id_marge, json.dumps(marges_.normalitza(dades, id_marge), ensure_ascii=False), ara()))
        return id_marge


def esborra_marge(id_marge: str) -> None:
    if id_marge == marges_.SENSE_MARGES:
        raise ValueError("La mestra «Sense marges» no es pot esborrar.")
    with connexio() as con:
        con.execute("DELETE FROM marge WHERE id = ?", (_valida(id_marge),))


# Migracions de l'esquema, en ordre. No se'n treu ni se'n canvia mai cap de publicada: les noves
# s'afegeixen al final. La primera també posa al dia les bases de dades d'abans d'haver-n'hi.
MIGRACIONS = [
    _afegeix_columnes,  # 1: canco.tipus i entrada.inici
    _sembra_marges,  # 2: mestres de marges predefinides
]
