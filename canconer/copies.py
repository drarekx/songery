"""Còpies de seguretat de totes les dades: la base de dades, les imatges i les tipografies.

La base de dades es copia amb l'API de còpia de seguretat de SQLite, que dona una còpia
consistent encara que l'aplicació estigui oberta i escrivint. Tot plegat va en un .zip a
<dades>/copies/AAAA-MM-DD_HHMM_vX.Y.Z.zip i se'n conserven les últimes N.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from . import basedades

CONSERVADES = 5
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


def neteja(conserva: int = CONSERVADES) -> None:
    """Esborra les còpies més antigues. Mai la més recent que té dades: si l'app s'ha obert sense dades
    (i n'ha fet còpies buides), aquella és la que permet recuperar-les."""
    totes = llista()
    amb_dades = ultima_amb_dades()
    for antiga in totes[conserva:]:
        if antiga != amb_dades:
            antiga.unlink(missing_ok=True)


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
