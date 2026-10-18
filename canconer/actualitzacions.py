"""Versió de l'aplicació i comprovació de versions noves a GitHub Releases."""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from functools import cache
from pathlib import Path

REPOSITORI = "drarekx/songery"
API_ULTIMA = f"https://api.github.com/repos/{REPOSITORI}/releases/latest"


@cache
def versio_actual() -> str:
    """Versió d'eines/app/VERSIO (dins de l'app, PyInstaller la desa al mateix camí relatiu)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    try:
        return (base / "eines" / "app" / "VERSIO").read_text().strip() or "0"
    except OSError:
        return "0"


def numeros(versio: str) -> tuple[int, ...]:
    """«v1.10.2» → (1, 10, 2). El que no és un número s'ignora."""
    return tuple(int(n) for n in re.findall(r"\d+", versio.split("-")[0])[:4]) or (0,)


def es_mes_nova(candidata: str, actual: str) -> bool:
    a, b = numeros(candidata), numeros(actual)
    llarg = max(len(a), len(b))
    return a + (0,) * (llarg - len(a)) > b + (0,) * (llarg - len(b))


def ultima_publicada(temps_maxim: float = 8) -> dict:
    """Última release publicada: {"versio", "url", "notes"}. Llança OSError si no s'hi pot accedir."""
    peticio = urllib.request.Request(API_ULTIMA, headers={
        "Accept": "application/vnd.github+json", "User-Agent": f"Canconers/{versio_actual()}"})
    with urllib.request.urlopen(peticio, timeout=temps_maxim) as resposta:
        dades = json.load(resposta)
    return {"versio": str(dades.get("tag_name", "")).lstrip("v"), "url": dades.get("html_url", ""),
            "notes": str(dades.get("body") or "")[:2000]}


def comprova(temps_maxim: float = 8) -> dict | None:
    """La release més nova si n'hi ha una de posterior a la instal·lada; si no, None."""
    ultima = ultima_publicada(temps_maxim)
    return ultima if ultima["versio"] and es_mes_nova(ultima["versio"], versio_actual()) else None
