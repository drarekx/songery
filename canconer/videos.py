"""Vídeos de YouTube vinculats a les cançons.

Cada cançó porta (dins del contingut, així que es versionen amb ella) una llista de vídeos:
  {"id", "video" (identificador de YouTube, 11 caràcters), "inici" (segons), "titol", "canal",
   "inclou_qr" (si surt a l'índex de QR)}
Els codis QR apunten a l'adreça curta youtu.be (el codi surt més petit) i es dibuixen al navegador,
amb el mateix codi a l'editor i al PDF, sense connexió.
"""

from __future__ import annotations

import re
import uuid
from urllib.parse import parse_qs, urlparse

import requests

MAXIM = 20
_ID_VIDEO = re.compile(r"^[A-Za-z0-9_-]{11}$")
_ID = re.compile(r"^[a-z0-9]{1,16}$")
_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtube-nocookie.com",
          "www.youtube-nocookie.com"}


class UrlInvalida(ValueError):
    """L'adreça no és d'un vídeo de YouTube."""


def _segons(valor: str | None) -> int:
    """«90», «90s», «1m30s» o «1h2m3s» → segons."""
    if not valor:
        return 0
    if valor.isdigit():
        return int(valor)
    parts = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", valor)
    if not parts or not any(parts.groups()):
        return 0
    h, m, s = (int(x or 0) for x in parts.groups())
    return h * 3600 + m * 60 + s


def analitza(url: str) -> dict:
    """Extreu l'identificador i el temps d'inici d'una adreça de YouTube (watch, youtu.be, shorts,
    embed, live). Llança UrlInvalida si no ho és."""
    text = str(url or "").strip()
    if not text:
        raise UrlInvalida("Enganxa l'adreça d'un vídeo de YouTube.")
    if "://" not in text:
        text = "https://" + text
    u = urlparse(text)
    host = (u.hostname or "").lower()
    consulta = parse_qs(u.query)
    video = None
    if host in ("youtu.be", "www.youtu.be"):
        video = u.path.strip("/").split("/")[0]
    elif host in _HOSTS:
        if u.path == "/watch":
            video = (consulta.get("v") or [None])[0]
        else:
            parts = [p for p in u.path.split("/") if p]
            if len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
                video = parts[1]
    if not video or not _ID_VIDEO.match(video):
        raise UrlInvalida("Aquesta adreça no és d'un vídeo de YouTube (per exemple, https://youtu.be/… o "
                          "https://www.youtube.com/watch?v=…).")
    inici = _segons((consulta.get("t") or consulta.get("start") or [None])[0])
    return {"video": video, "inici": inici}


def url_curta(v: dict) -> str:
    return f"https://youtu.be/{v['video']}" + (f"?t={v['inici']}" if v.get("inici") else "")


def miniatura(v: dict) -> str:
    return f"https://i.ytimg.com/vi/{v['video']}/hqdefault.jpg"


def informacio(v: dict, temps_maxim: float = 4) -> dict:
    """Títol i canal amb oEmbed (sense clau d'API). Sense connexió, retorna un diccionari buit."""
    try:
        r = requests.get("https://www.youtube.com/oembed",
                         params={"url": f"https://www.youtube.com/watch?v={v['video']}", "format": "json"},
                         timeout=temps_maxim)
        if r.status_code != 200:
            return {}
        dades = r.json()
    except (requests.RequestException, ValueError):
        return {}
    return {"titol": str(dades.get("title") or "")[:200], "canal": str(dades.get("author_name") or "")[:120]}


def normalitza(llista) -> list[dict]:
    """Valida la llista de vídeos d'una cançó (ve del navegador o de la base de dades)."""
    net = []
    vistos = set()
    for v in (llista if isinstance(llista, list) else [])[:MAXIM]:
        if not isinstance(v, dict) or not _ID_VIDEO.match(str(v.get("video", ""))):
            continue
        identificador = str(v.get("id") or "")
        if not _ID.match(identificador) or identificador in vistos:
            identificador = uuid.uuid4().hex[:8]
        vistos.add(identificador)
        try:
            inici = max(0, min(24 * 3600, int(v.get("inici") or 0)))
        except (TypeError, ValueError):
            inici = 0
        net.append({
            "id": identificador,
            "video": v["video"],
            "inici": inici,
            "titol": str(v.get("titol") or "")[:200],
            "canal": str(v.get("canal") or "")[:120],
            "inclou_qr": bool(v.get("inclou_qr", True)),
        })
    return net


def per_al_dibuix(llista) -> list[dict]:
    """Vídeos amb el que cal per dibuixar els QR: {id, titol, url}."""
    return [{"id": v["id"], "titol": v["titol"], "url": url_curta(v)} for v in normalitza(llista)]
