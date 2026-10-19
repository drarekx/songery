"""Còpies de seguretat de totes les dades: la base de dades, les imatges i les tipografies.

La base de dades es copia amb l'API de còpia de seguretat de SQLite, que dona una còpia
consistent encara que l'aplicació estigui oberta i escrivint. Tot plegat va en un .zip a
<dades>/copies/AAAA-MM-DD_HHMM_vX.Y.Z.zip. Se'n conserven les 10 últimes i totes les dels últims
30 dies (fins a 60), i mai s'esborra la més recent que té dades.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

from . import basedades

CONSERVADES = 10  # se'n conserven sempre com a mínim aquestes (les més recents)...
DIES_CONSERVADES = 30  # ...i totes les d'aquests últims dies...
MAXIM_COPIES = 60  # ...fins a aquest màxim (l'espai al disc); la més recent amb dades no s'esborra mai
BASE_DADES = "canconers.sqlite3"
CARPETES = ("imatges", "tipografies")
_NOM = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{4}(\d{2})?_v[\w.]+(_[\w-]+)?\.zip$")


class CopiaInvalida(ValueError):
    """El fitxer no és una còpia de seguretat de Cançoners o està malmès."""


def directori() -> Path:
    d = basedades.DIRECTORI / "copies"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _copia_bd(origen: Path, desti: Path) -> None:
    """Còpia consistent d'una base de dades SQLite (encara que estigui oberta)."""
    font = sqlite3.connect(origen, timeout=30)
    try:
        copia = sqlite3.connect(desti)
        try:
            font.backup(copia)
        finally:
            copia.close()
    finally:
        font.close()


def _integra(cami: Path) -> bool:
    con = sqlite3.connect(cami)
    try:
        return con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    except sqlite3.DatabaseError:
        return False
    finally:
        con.close()


def fes_copia(versio: str = "", motiu: str = "", conserva: int = CONSERVADES) -> Path:
    """Crea una còpia de seguretat i retorna'n el camí. Si alguna cosa falla, llança una excepció
    (i no deixa cap còpia a mitges)."""
    dades = basedades.DIRECTORI
    ara = datetime.now()
    sufix = f"_{re.sub(r'[^a-z0-9-]', '', motiu.lower())}" if motiu else ""
    nom = f"{ara:%Y-%m-%d_%H%M%S}_v{re.sub(r'[^0-9A-Za-z.]', '', versio) or '0'}{sufix}.zip"
    desti = directori() / nom
    with tempfile.TemporaryDirectory() as temporal:
        bd = Path(temporal) / BASE_DADES
        if (dades / BASE_DADES).exists():
            _copia_bd(dades / BASE_DADES, bd)
            if not _integra(bd):
                raise RuntimeError("La còpia de la base de dades no ha passat la comprovació d'integritat.")
        parcial = desti.with_suffix(".zip.tmp")
        try:
            with zipfile.ZipFile(parcial, "w", zipfile.ZIP_DEFLATED) as z:
                if bd.exists():
                    z.write(bd, BASE_DADES)
                for carpeta in CARPETES:
                    for fitxer in sorted((dades / carpeta).rglob("*")) if (dades / carpeta).is_dir() else []:
                        if fitxer.is_file():
                            z.write(fitxer, fitxer.relative_to(dades).as_posix())
                z.writestr("COPIA.txt", f"Còpia de seguretat de Cançoners\nVersió: {versio}\nData: {ara.isoformat(timespec='seconds')}\n"
                                        f"Motiu: {motiu or 'manual'}\n")
            parcial.replace(desti)
        finally:
            parcial.unlink(missing_ok=True)
    neteja(conserva)
    return desti


def llista() -> list[Path]:
    """Còpies existents, de la més nova a la més antiga."""
    return sorted((f for f in directori().glob("*.zip") if _NOM.match(f.name)), key=lambda f: f.name, reverse=True)


def _data(copia: Path) -> datetime:
    try:
        return datetime.strptime(copia.name[:10], "%Y-%m-%d")
    except ValueError:
        return datetime.fromtimestamp(copia.stat().st_mtime)


def neteja(conserva: int = CONSERVADES) -> None:
    """Esborra les còpies antigues: només les que no són entre les `conserva` més recents i, a més,
    tenen més de DIES_CONSERVADES dies o passen de MAXIM_COPIES. Mai la més recent que té dades: si
    l'app s'ha obert sense dades (i n'ha anat fent còpies buides), aquella és la que permet recuperar-les.
    (Abans es conservaven només les 5 últimes, i unes quantes còpies seguides de restaurar i migrar
    van fer fora les bones.)"""
    totes = llista()
    amb_dades = ultima_amb_dades()
    limit = datetime.now() - timedelta(days=DIES_CONSERVADES)
    for i, copia in enumerate(totes):
        if i < conserva or copia == amb_dades:
            continue
        if _data(copia) < limit or i >= MAXIM_COPIES:
            copia.unlink(missing_ok=True)


_resums: dict[tuple[str, float], dict] = {}


def resum(copia: Path) -> dict:
    """Quants cançoners (fora de la paperera) i cançons hi ha en una còpia: {"canconers", "cancons"}."""
    clau = (copia.name, copia.stat().st_mtime)
    if clau not in _resums:
        resultat = {"canconers": 0, "cancons": 0}
        try:
            with tempfile.TemporaryDirectory() as temporal, zipfile.ZipFile(copia) as z:
                if BASE_DADES in z.namelist():
                    z.extract(BASE_DADES, temporal)
                    con = sqlite3.connect(Path(temporal) / BASE_DADES)
                    try:
                        columnes = {f[1] for f in con.execute("PRAGMA table_info(canconer)")}
                        filtre = " WHERE paperera IS NULL" if "paperera" in columnes else ""
                        resultat = {"canconers": con.execute(f"SELECT COUNT(*) FROM canconer{filtre}").fetchone()[0],
                                    "cancons": con.execute("SELECT COUNT(*) FROM canco").fetchone()[0]}
                    finally:
                        con.close()
        except (zipfile.BadZipFile, sqlite3.DatabaseError, OSError):
            pass
        _resums[clau] = resultat
    return _resums[clau]


MOTIUS = {
    "abans-d-actualitzar": "Abans d'actualitzar l'app",
    "abans-de-restaurar": "Abans de restaurar una còpia",
    "manual": "Feta a mà",
}


def descripcio(copia: Path) -> dict:
    """Data, versió i motiu d'una còpia (del nom del fitxer), la mida i el resum del contingut."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})_(\d{2})(\d{2})(\d{2})?_v([\w.]+?)(?:_([\w-]+))?\.zip$", copia.name)
    motiu = (m.group(8) if m else "") or ""
    if motiu.startswith("abans-de-migrar"):
        text = "Abans d'actualitzar les dades (migració)"
    else:
        text = MOTIUS.get(motiu, "Automàtica" if not motiu else motiu.replace("-", " ").capitalize())
    return {
        "nom": copia.name,
        "data": f"{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}" if m else "",
        "versio": m.group(7) if m else "",
        "motiu": text,
        "mida": copia.stat().st_size,
        **resum(copia),
    }


def contingut(copia: Path) -> dict:
    """Què hi ha en una còpia, per previsualitzar-la: cada cançoner amb les seves cançons (en ordre),
    les cançons que no són a cap cançoner i quantes imatges i tipografies porta."""
    with tempfile.TemporaryDirectory() as temporal, zipfile.ZipFile(copia) as z:
        noms = z.namelist()
        if BASE_DADES not in noms:
            raise CopiaInvalida("Aquest fitxer no és una còpia de seguretat de Cançoners.")
        z.extract(BASE_DADES, temporal)
        con = sqlite3.connect(Path(temporal) / BASE_DADES)
        con.row_factory = sqlite3.Row
        try:
            columnes = {f[1] for f in con.execute("PRAGMA table_info(canconer)")}
            paperera = "paperera" in columnes
            canconers = []
            for k in con.execute(f"SELECT id, dades{', paperera' if paperera else ''} FROM canconer ORDER BY actualitzat DESC"):
                dades = json.loads(k["dades"])
                cancons = [f["titol"] or "Sense títol" for f in con.execute(
                    "SELECT c.titol FROM entrada e JOIN canco c ON c.id = e.canco_id WHERE e.canconer_id = ? ORDER BY e.posicio",
                    (k["id"],))]
                canconers.append({"titol": dades.get("titol") or "Cançoner", "cancons": cancons,
                                  "paperera": bool(paperera and k["paperera"])})
            soltes = [f["titol"] or "Sense títol" for f in con.execute(
                "SELECT titol FROM canco WHERE id NOT IN (SELECT canco_id FROM entrada) ORDER BY titol COLLATE NOCASE")]
        finally:
            con.close()
    return {
        "canconers": canconers, "soltes": soltes,
        "imatges": sum(1 for n in noms if n.startswith("imatges/") and not n.endswith("/")),
        "tipografies": sum(1 for n in noms if n.startswith("tipografies/") and not n.endswith("/")),
    }


def ultima_amb_dades() -> Path | None:
    """La còpia més recent que té algun cançoner o alguna cançó."""
    return next((c for c in llista() if resum(c)["canconers"] or resum(c)["cancons"]), None)


def restaura(copia: Path, versio: str = "") -> Path:
    """Torna les dades a l'estat d'una còpia. Abans en fa una de l'estat actual (que es retorna),
    per si de cas. La base de dades es restaura amb l'API de SQLite, així que l'aplicació pot
    continuar oberta."""
    dades = basedades.DIRECTORI
    with tempfile.TemporaryDirectory() as temporal:
        temporal = Path(temporal)
        try:
            with zipfile.ZipFile(copia) as z:
                noms = z.namelist()
                if BASE_DADES not in noms:
                    raise CopiaInvalida("Aquest fitxer no és una còpia de seguretat de Cançoners.")
                for nom in noms:
                    # Només s'extreu el que toca, i mai fora de la carpeta temporal.
                    if nom == BASE_DADES or (nom.split("/", 1)[0] in CARPETES and ".." not in Path(nom).parts):
                        z.extract(nom, temporal)
        except zipfile.BadZipFile as e:
            raise CopiaInvalida("El fitxer de la còpia està malmès.") from e
        if not _integra(temporal / BASE_DADES):
            raise CopiaInvalida("La base de dades de la còpia està malmesa.")

        abans = fes_copia(versio, "abans-de-restaurar", conserva=CONSERVADES + 1)
        _copia_bd(temporal / BASE_DADES, dades / BASE_DADES)
        for carpeta in CARPETES:
            if (dades / carpeta).exists():
                shutil.rmtree(dades / carpeta)
            if (temporal / carpeta).exists():
                shutil.copytree(temporal / carpeta, dades / carpeta)
    # La memòria cau de PDF pot ser de l'estat anterior, i la base de dades restaurada pot
    # necessitar migracions: es tornen a comprovar en la connexió següent.
    shutil.rmtree(dades / "cau", ignore_errors=True)
    basedades._inicialitzades.discard(dades / BASE_DADES)
    return abans
