"""Generació dels PDF amb Gotenberg (Chromium) i memòria cau.

Gotenberg obre la pàgina d'impressió de l'aplicació (la mateixa que dibuixa l'editor) i la
desa en PDF. Així el que es veu a l'editor és exactament el que s'imprimeix.
Cal tenir Gotenberg en marxa:  docker compose up -d   (vegeu docker-compose.yml)
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from io import BytesIO
from pathlib import Path

import requests
from pypdf import PdfReader

from . import basedades, imposicio

GOTENBERG = os.environ.get("GOTENBERG_URL", "http://127.0.0.1:3000").rstrip("/")
# Adreça amb què Gotenberg (dins de Docker) arriba a aquesta aplicació.
URL_INTERNA = os.environ.get("CANCONER_URL_INTERNA", "")

_ESTATIC = Path(__file__).parent / "static"
_bloqueig = threading.Lock()

A5_POLZADES = (148 / 25.4, 210 / 25.4)
A4_POLZADES = (210 / 25.4, 297 / 25.4)


class GotenbergNoDisponible(RuntimeError):
    pass


def empremta(canconer: dict) -> str:
    """Hash del contingut i del codi de dibuix: si no canvia res, es reaprofiten els PDF."""
    # Les tipografies importades també compten: si se n'importa una que ja es feia servir, el PDF canvia.
    fonts = basedades.tipografies_importades()
    dades = json.dumps([canconer, fonts], sort_keys=True, ensure_ascii=False).encode()
    codi = b"".join(f.read_bytes() for f in (_ESTATIC / "pagines.css", _ESTATIC / "dist" / "canconer.js") if f.exists())
    return hashlib.sha256(dades + codi).hexdigest()[:20]


def _directori_cau() -> Path:
    d = basedades.DIRECTORI / "cau"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _escriu(cami: Path, dades: bytes) -> None:
    temporal = cami.with_name(f"{cami.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    temporal.write_bytes(dades)
    temporal.replace(cami)


def converteix_url(url: str, mida: tuple[float, float], esperar: bool = True) -> bytes:
    """Demana a Gotenberg que converteixi una URL en PDF."""
    camps = {
        "url": url,
        "paperWidth": f"{mida[0]:.4f}", "paperHeight": f"{mida[1]:.4f}",
        "marginTop": "0", "marginBottom": "0", "marginLeft": "0", "marginRight": "0",
        "printBackground": "true", "preferCssPageSize": "true", "emulatedMediaType": "print",
    }
    if esperar:
        camps["waitForExpression"] = "window.paginesLlestes === true"
    try:
        resposta = requests.post(f"{GOTENBERG}/forms/chromium/convert/url",
                                 files={k: (None, v) for k, v in camps.items()}, timeout=180)
    except requests.RequestException as e:
        raise GotenbergNoDisponible(
            f"No es pot connectar amb Gotenberg a {GOTENBERG}. Engega'l amb «docker compose up -d».") from e
    if resposta.status_code != 200:
        raise GotenbergNoDisponible(f"Gotenberg ha retornat un error {resposta.status_code}: {resposta.text[:300]}")
    return resposta.content


def genera_a5(canconer: dict, url_imprimible: str, total_esperat: int | None = None) -> bytes:
    """PDF A5 en ordre de lectura."""
    cami = _directori_cau() / f"{empremta(canconer)}-a5.pdf"
    with _bloqueig:
        if cami.exists():
            return cami.read_bytes()
        dades = converteix_url(url_imprimible, A5_POLZADES)
        pagines = len(PdfReader(BytesIO(dades)).pages)
        if total_esperat and pagines != total_esperat:
            raise RuntimeError(f"El PDF té {pagines} pàgines i se n'esperaven {total_esperat}.")
        _escriu(cami, dades)
        return dades


def genera(canconer: dict, tipus: str, url_imprimible: str, total_esperat: int | None = None) -> bytes:
    """tipus: a5, a4, a4-vora-llarga, davant, darrere, darrere-girat, darrere-invers."""
    dades_a5 = genera_a5(canconer, url_imprimible, total_esperat)
    if tipus == "a5":
        return dades_a5
    cami = _directori_cau() / f"{empremta(canconer)}-{tipus}.pdf"
    if cami.exists():
        return cami.read_bytes()
    opcions = {"a4": {}, "a4-vora-llarga": {"gira_darrere": True},
               "davant": {"costat": "davant"}, "darrere": {"costat": "darrere"},
               "darrere-girat": {"costat": "darrere", "gira_darrere": True},
               "darrere-invers": {"costat": "darrere", "invers": True}}
    if tipus not in opcions:
        raise ValueError(tipus)
    dades = imposicio.imposa(dades_a5, **opcions[tipus])
    _escriu(cami, dades)
    return dades


def instruccions(url: str) -> bytes:
    """Full A4 amb les instruccions per imprimir en una impressora sense doble cara."""
    return converteix_url(url, A4_POLZADES, esperar=False)


def neteja_cau(maxim: int = 200) -> None:
    fitxers = sorted(_directori_cau().glob("*.pdf"), key=lambda f: f.stat().st_mtime)
    for f in fitxers[:-maxim]:
        f.unlink(missing_ok=True)
