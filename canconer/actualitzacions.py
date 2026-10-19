"""Versió de l'aplicació i comprovació de versions noves a GitHub Releases."""

from __future__ import annotations

import gzip
import json
import os
import re
import ssl
import sys
import urllib.request
import zlib
from functools import cache
from pathlib import Path

REPOSITORI = "drarekx/songery"
API_ULTIMA = f"https://api.github.com/repos/{REPOSITORI}/releases/latest"


@cache
def context_ssl() -> ssl.SSLContext:
    """Context HTTPS amb els certificats arrel de certifi. Dins l'app empaquetada, el Python no troba
    els del sistema i urllib fallava amb «CERTIFICATE_VERIFY_FAILED: unable to get local issuer
    certificate». Sense certifi, el context per defecte."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError):
        return ssl.create_default_context()


@cache
def versio_actual() -> str:
    """Versió d'eines/app/VERSIO (dins de l'app, PyInstaller la desa al mateix camí relatiu)."""
    if os.environ.get("CANCONER_VERSIO"):  # per provar l'actualització amb una versió «antiga»
        return os.environ["CANCONER_VERSIO"]
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


def llegeix_json(url: str, temps_maxim: float = 10) -> dict:
    """JSON d'una API (la de GitHub) llegit tal com arriba. Amb urllib, que no descomprimeix res pel seu
    compte: algunes xarxes, proxies o antivirus marquen la resposta com a comprimida sense ser-ho, i
    `requests` fallava amb «Error -3 while decompressing data: incorrect header check». Si la resposta
    sí que ve comprimida (gzip o zlib), es descomprimeix aquí. Llança OSError o ValueError si falla."""
    peticio = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json", "Accept-Encoding": "identity",
        "User-Agent": f"Canconers/{versio_actual()}"})
    with urllib.request.urlopen(peticio, timeout=temps_maxim, context=context_ssl()) as resposta:
        cos = resposta.read()
    if cos[:2] == b"\x1f\x8b":
        cos = gzip.decompress(cos)
    elif cos[:1] == b"\x78":
        try:
            cos = zlib.decompress(cos)
        except zlib.error:
            pass
    return json.loads(cos)


def ultima_publicada(temps_maxim: float = 8) -> dict:
    """Última release publicada: {"versio", "url", "notes"}. Llança OSError si no s'hi pot accedir."""
    dades = llegeix_json(API_ULTIMA, temps_maxim)
    return {"versio": str(dades.get("tag_name", "")).lstrip("v"), "url": dades.get("html_url", ""),
            "notes": str(dades.get("body") or "")[:2000]}


def comprova(temps_maxim: float = 8) -> dict | None:
    """La release més nova si n'hi ha una de posterior a la instal·lada; si no, None."""
    ultima = ultima_publicada(temps_maxim)
    return ultima if ultima["versio"] and es_mes_nova(ultima["versio"], versio_actual()) else None
