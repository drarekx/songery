"""Duplicar, exportar i importar cançoners.

Format del fitxer exportat (.canconer): un ZIP amb
  canconer.json   {"format": 1, "aplicacio": "canconers", "exportat": data,
                   "canconer": {dades}, "entrades": [...], "cancons": [...amb les versions],
                   "imatges": [...], "tipografies": [...]}
  imatges/<fitxer>, tipografies/<fitxer>
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path

from . import basedades as bd
from . import disseny, plantilles, tipografies

FORMAT = 1
MIDA_MAXIMA = 200 * 1024 * 1024  # mida màxima del fitxer importat
MIDA_MAXIMA_DESCOMPRIMIT = 600 * 1024 * 1024


class ImportacioInvalida(ValueError):
    """El fitxer no és un cançoner exportat vàlid."""


# ---------------------------------------------------------------- Duplicar


def duplica(id_canconer: str, duplicar_cancons: bool = False) -> str:
    """Còpia independent d'un cançoner: disseny, ordre, versions fixades, transport i inclusió.

    Per defecte les cançons continuen sent les de la biblioteca (editar-ne una afecta tots dos
    cançoners si segueixen l'esborrany). Amb duplicar_cancons=True, cada cançó es copia com una
    cançó nova amb el contingut que fa servir aquest cançoner.
    """
    meta = bd.meta_canconer(id_canconer)
    dades = {k: v for k, v in meta.items() if k != "id"}
    dades["titol"] = f"{meta['titol']} (còpia)"
    origen = bd.carrega_canconer(id_canconer)
    nou = bd.nou_id()
    with bd.connexio() as con:
        con.execute("INSERT INTO canconer (id, dades, creat, actualitzat) VALUES (?, ?, ?, ?)",
                    (nou, json.dumps(dades, ensure_ascii=False), bd.ara(), bd.ara()))
        entrades = con.execute("SELECT * FROM entrada WHERE canconer_id = ? ORDER BY posicio", (id_canconer,)).fetchall()
        for e in entrades:
            id_canco, versio = e["canco_id"], e["versio_id"]
            if duplicar_cancons:
                c = next(x for x in origen["cancons"] if x["id"] == e["canco_id"])
                id_canco, versio = bd.nou_id(), None
                con.execute("INSERT INTO canco (id, titol, autor, doc, creada, actualitzada, tipus) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (id_canco, c["titol"], c["autor"], json.dumps(c["contingut"], ensure_ascii=False),
                             bd.ara(), bd.ara(), c.get("tipus", "canco")))
            con.execute("INSERT INTO entrada (canconer_id, canco_id, posicio, versio_id, inclosa, transport, inici) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (nou, id_canco, e["posicio"], versio, e["inclosa"], e["transport"], e["inici"]))
    return nou


# ---------------------------------------------------------------- Referències a imatges i tipografies


def _imatges_referenciades(objecte) -> set[str]:
    """Ids d'imatge de tots els camps «src» (elements de pàgina i imatges dins la lletra)."""
    trobades: set[str] = set()

    def recorre(o):
        if isinstance(o, dict):
            if isinstance(o.get("src"), str) and o["src"]:
                trobades.add(o["src"])
            for v in o.values():
                recorre(v)
        elif isinstance(o, list):
            for v in o:
                recorre(v)

    recorre(objecte)
    return trobades


def _reanomena_imatges(objecte, mapa: dict[str, str]):
    if isinstance(objecte, dict):
        return {k: (mapa.get(v, v) if k == "src" and isinstance(v, str) else _reanomena_imatges(v, mapa))
                for k, v in objecte.items()}
    if isinstance(objecte, list):
        return [_reanomena_imatges(v, mapa) for v in objecte]
    return objecte


# ---------------------------------------------------------------- Exportar


def exporta(id_canconer: str) -> bytes:
    meta = bd.meta_canconer(id_canconer)
    with bd.connexio() as con:
        entrades = [dict(f) for f in con.execute(
            "SELECT canco_id, posicio, versio_id, inclosa, transport, inici FROM entrada "
            "WHERE canconer_id = ? ORDER BY posicio", (id_canconer,))]
        cancons = []
        for e in entrades:
            c = con.execute("SELECT * FROM canco WHERE id = ?", (e["canco_id"],)).fetchone()
            versions = [{**dict(v), "doc": json.loads(v["doc"])} for v in con.execute(
                "SELECT id, numero, titol, autor, doc, nota, creada FROM versio WHERE canco_id = ? ORDER BY numero",
                (c["id"],))]
            cancons.append({"id": c["id"], "titol": c["titol"], "autor": c["autor"], "tipus": c["tipus"],
                            "doc": json.loads(c["doc"]), "creada": c["creada"], "versions": versions})

    dades = {k: v for k, v in meta.items() if k != "id"}
    referenciades = _imatges_referenciades([dades, cancons])
    text = json.dumps([dades, cancons], ensure_ascii=False)
    importades = bd.tipografies_importades()
    fonts_usades = [f for f in importades if f'"{tipografies.clau_importada(f["nom"])}"' in text]

    sortida = io.BytesIO()
    with zipfile.ZipFile(sortida, "w", zipfile.ZIP_DEFLATED) as z:
        imatges = []
        for id_imatge in sorted(referenciades):
            try:
                cami, tipus = bd.imatge(id_imatge)
            except KeyError:
                continue
            if cami.exists():
                z.write(cami, f"imatges/{cami.name}")
                imatges.append({"id": id_imatge, "fitxer": cami.name, "tipus": tipus})
        fonts = []
        for f in fonts_usades:
            cami, format_ = bd.fitxer_tipografia(f["id"])
            if cami.exists():
                z.write(cami, f"tipografies/{cami.name}")
                fonts.append({**f, "fitxer": cami.name})
        z.writestr("canconer.json", json.dumps({
            "format": FORMAT, "aplicacio": "canconers", "exportat": datetime.now().isoformat(timespec="seconds"),
            "canconer": dades, "entrades": entrades, "cancons": cancons, "imatges": imatges, "tipografies": fonts,
        }, ensure_ascii=False, indent=1))
    return sortida.getvalue()


# ---------------------------------------------------------------- Importar


def _llegeix(dades: bytes) -> tuple[dict, zipfile.ZipFile]:
    if len(dades) > MIDA_MAXIMA:
        raise ImportacioInvalida(f"El fitxer fa més de {MIDA_MAXIMA // (1024 * 1024)} MB.")
    try:
        z = zipfile.ZipFile(io.BytesIO(dades))
        if sum(i.file_size for i in z.infolist()) > MIDA_MAXIMA_DESCOMPRIMIT:
            raise ImportacioInvalida("El fitxer descomprimit és massa gran.")
        contingut = json.loads(z.read("canconer.json"))
    except ImportacioInvalida:
        raise
    except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ImportacioInvalida("No és un fitxer de cançoner vàlid (.canconer).") from e
    if not isinstance(contingut, dict) or contingut.get("aplicacio") != "canconers":
        raise ImportacioInvalida("No és un fitxer de cançoner vàlid (.canconer).")
    if not isinstance(contingut.get("format"), int) or contingut["format"] > FORMAT:
        raise ImportacioInvalida("Aquest fitxer és d'una versió més nova de Cançoners. Actualitza l'aplicació.")
    for clau, tipus in (("canconer", dict), ("entrades", list), ("cancons", list), ("imatges", list), ("tipografies", list)):
        if not isinstance(contingut.get(clau, [] if tipus is list else None), tipus):
            raise ImportacioInvalida("El fitxer de cançoner està malmès.")
    return contingut, z


_ID = re.compile(r"^[a-z0-9]{1,32}$")


def importa(dades: bytes) -> str:
    """Crea un cançoner nou a partir d'un fitxer exportat. Si falla, no deixa res a mitges."""
    contingut, z = _llegeix(dades)
    fitxers_nous: list[Path] = []
    try:
        # Imatges: sempre amb ids nous (es reescriuen les referències).
        mapa_imatges: dict[str, str] = {}
        imatges_a_inserir = []
        directori_imatges = bd.DIRECTORI / "imatges"
        directori_imatges.mkdir(parents=True, exist_ok=True)
        for im in contingut["imatges"]:
            tipus = im.get("tipus")
            if tipus not in bd.TIPUS_IMATGE or not isinstance(im.get("fitxer"), str):
                continue
            try:
                bytes_imatge = z.read(f"imatges/{Path(im['fitxer']).name}")
            except KeyError:
                continue
            nou = bd.nou_id()
            cami = directori_imatges / f"{nou}.{bd.TIPUS_IMATGE[tipus]}"
            cami.write_bytes(bytes_imatge)
            fitxers_nous.append(cami)
            mapa_imatges[str(im.get("id"))] = nou
            imatges_a_inserir.append((nou, cami.name, tipus, "importada"))

        # Tipografies: es reutilitzen si ja hi ha la mateixa cara (família, gruix i estil).
        existents = {(f["nom"], f["pes"], f["estil"]) for f in bd.tipografies_importades()}
        fonts_a_inserir = []
        directori_fonts = bd.DIRECTORI / "tipografies"
        directori_fonts.mkdir(parents=True, exist_ok=True)
        for f in contingut["tipografies"]:
            try:
                clau = (str(f["nom"])[:80], int(f["pes"]), "italic" if f.get("estil") == "italic" else "normal")
                bytes_font = z.read(f"tipografies/{Path(f['fitxer']).name}")
            except (KeyError, TypeError, ValueError):
                continue
            format_ = tipografies.tipus_fitxer(bytes_font)
            if not format_ or clau in existents:
                continue
            nou = bd.nou_id()
            cami = directori_fonts / f"{nou}.{format_}"
            cami.write_bytes(bytes_font)
            fitxers_nous.append(cami)
            existents.add(clau)
            fonts_a_inserir.append((nou, clau[0], cami.name, format_, clau[1], clau[2]))

        # Dades del cançoner, validades amb els normalitzadors de l'editor.
        meta = _reanomena_imatges(contingut["canconer"], mapa_imatges)
        dades_canconer = {k: meta[k] for k in bd.VALORS_PER_DEFECTE if k in meta and isinstance(meta[k], (str, bool))}
        dades_canconer["titol"] = str(meta.get("titol") or "Cançoner importat")[:200]
        dades_canconer["estils"] = disseny.estils(meta.get("estils"))
        mestres = disseny.mestres(meta.get("mestres"))
        if mestres and any(m["id"] == "estandard" for m in mestres):
            dades_canconer["mestres"] = mestres
        dades_canconer["especials"] = disseny.especials(meta.get("especials"))

        id_canconer = bd.nou_id()
        with bd.connexio() as con:  # una sola transacció: si alguna cosa falla, no es desa res
            for fila in imatges_a_inserir:
                con.execute("INSERT INTO imatge (id, fitxer, tipus, nom, creada) VALUES (?, ?, ?, ?, ?)", (*fila, bd.ara()))
            for fila in fonts_a_inserir:
                con.execute("INSERT INTO tipografia (id, nom, fitxer, format, pes, estil, creada) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (*fila, bd.ara()))
            con.execute("INSERT INTO canconer (id, dades, creat, actualitzat) VALUES (?, ?, ?, ?)",
                        (id_canconer, json.dumps(dades_canconer, ensure_ascii=False), bd.ara(), bd.ara()))

            ids_cancons: dict[str, str] = {}
            versions_conegudes: set[str] = set()
            for c in contingut["cancons"]:
                if not isinstance(c, dict):
                    raise ImportacioInvalida("El fitxer de cançoner està malmès.")
                # Es conserva l'id de la cançó: si ja és a la biblioteca (p. ex. l'exportació ve d'aquí
                # mateix), es reutilitza; si no, es crea amb el mateix id.
                id_origen = str(c.get("id", ""))
                id_canco = id_origen if _ID.match(id_origen) else bd.nou_id()
                existent = con.execute("SELECT 1 FROM canco WHERE id = ?", (id_canco,)).fetchone() is not None
                if not existent:
                    doc = disseny.contingut(plantilles.normalitza_contingut(_reanomena_imatges(c.get("doc") or {}, mapa_imatges)))
                    con.execute("INSERT INTO canco (id, titol, autor, doc, creada, actualitzada, tipus) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                (id_canco, str(c.get("titol", ""))[:300], str(c.get("autor", ""))[:300],
                                 json.dumps(doc, ensure_ascii=False), str(c.get("creada") or bd.ara()), bd.ara(),
                                 "pagina" if c.get("tipus") == "pagina" else "canco"))
                ids_cancons[id_origen] = id_canco
                # Versions: s'afegeixen les que falten (si la cançó ja hi era, amb números nous al final).
                maxim = con.execute("SELECT COALESCE(MAX(numero), 0) FROM versio WHERE canco_id = ?", (id_canco,)).fetchone()[0]
                for v in c.get("versions") or []:
                    id_versio = str(v.get("id", ""))
                    if _ID.match(id_versio) and con.execute("SELECT 1 FROM versio WHERE id = ?", (id_versio,)).fetchone():
                        versions_conegudes.add(id_versio)
                        continue
                    if not _ID.match(id_versio):
                        id_versio = bd.nou_id()
                    numero = int(v.get("numero") or 0) if not existent else 0
                    if existent or numero <= maxim:
                        numero = maxim + 1
                    maxim = max(maxim, numero)
                    doc = disseny.contingut(plantilles.normalitza_contingut(_reanomena_imatges(v.get("doc") or {}, mapa_imatges)))
                    con.execute("INSERT INTO versio (id, canco_id, numero, titol, autor, doc, nota, creada) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                (id_versio, id_canco, numero, str(v.get("titol", ""))[:300], str(v.get("autor", ""))[:300],
                                 json.dumps(doc, ensure_ascii=False), str(v.get("nota", ""))[:200], str(v.get("creada") or bd.ara())))
                    versions_conegudes.add(id_versio)

            for posicio, e in enumerate(contingut["entrades"]):
                id_canco = ids_cancons.get(str(e.get("canco_id")))
                if not id_canco:
                    continue
                versio = e.get("versio_id") if e.get("versio_id") in versions_conegudes else None
                con.execute("INSERT OR IGNORE INTO entrada (canconer_id, canco_id, posicio, versio_id, inclosa, transport, inici) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (id_canconer, id_canco, posicio, versio, 1 if e.get("inclosa", True) else 0,
                             max(-11, min(11, int(e.get("transport") or 0))),
                             "qualsevol" if e.get("inici") == "qualsevol" else "esquerra"))
        return id_canconer
    except Exception:
        for f in fitxers_nous:  # no deixar fitxers orfes si la importació falla
            f.unlink(missing_ok=True)
        raise
    finally:
        z.close()
