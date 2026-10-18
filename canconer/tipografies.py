"""Tipografies disponibles: les de base, el catàleg descarregat i les que importa l'usuari.

Cada tipografia té una clau (la que es desa als estils i elements: "display", "lora", "u-la-meva"...)
i una o més cares (gruix i estil). El CSS @font-face es genera a /fonts.css i el fan servir tant
l'editor com la pàgina d'impressió que llegeix Gotenberg.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

DIRECTORI_FONTS = Path(__file__).resolve().parent / "static" / "fonts"

# Tipografies de base (les de la interfície). Les claus són les dels estils per defecte.
NUCLI = [
    {"clau": "display", "nom": "Newsreader", "categoria": "serif", "cares": [
        {"fitxer": "newsreader-latin-opsz-normal.woff2", "pes": "200 800", "estil": "normal"},
        {"fitxer": "newsreader-latin-opsz-italic.woff2", "pes": "200 800", "estil": "italic"}]},
    {"clau": "sans", "nom": "Hanken Grotesk", "categoria": "sans", "cares": [
        {"fitxer": "hanken-grotesk-latin-wght-normal.woff2", "pes": "100 900", "estil": "normal"}]},
    {"clau": "mono", "nom": "JetBrains Mono", "categoria": "mono", "cares": [
        {"fitxer": "jetbrains-mono-latin-wght-normal.woff2", "pes": "100 800", "estil": "normal"}]},
]

GENERIQUES = {"serif": "serif", "sans": "sans-serif", "display": "sans-serif", "manuscrita": "cursive",
              "mono": "monospace", "importada": "sans-serif"}

FORMATS = {"ttf": "truetype", "otf": "opentype", "woff": "woff", "woff2": "woff2"}
_SIGNATURES = {b"\x00\x01\x00\x00": "ttf", b"true": "ttf", b"OTTO": "otf", b"wOFF": "woff", b"wOF2": "woff2"}


@lru_cache(maxsize=1)
def cataleg() -> tuple[dict, ...]:
    manifest = DIRECTORI_FONTS / "cataleg" / "fonts.json"
    descarregades = json.loads(manifest.read_text("utf-8")) if manifest.exists() else []
    for t in descarregades:
        for c in t["cares"]:
            c["fitxer"] = f"cataleg/{c['fitxer']}"
    return tuple(NUCLI + descarregades)


def clau_importada(nom: str) -> str:
    text = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().lower()
    return "u-" + (re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:40] or "font")


def tipus_fitxer(dades: bytes) -> str | None:
    """Format real del fitxer segons la signatura (no es refia de l'extensió)."""
    return _SIGNATURES.get(dades[:4])


def llista(importades: list[dict]) -> list[dict]:
    """Totes les tipografies agrupades per família: [{clau, nom, categoria, familia, cares}]."""
    resultat = [{**t, "familia": t["nom"]} for t in cataleg()]
    families: dict[str, dict] = {}
    for f in importades:
        clau = clau_importada(f["nom"])
        familia = families.setdefault(clau, {"clau": clau, "nom": f["nom"], "categoria": "importada",
                                             "familia": f"{f['nom']} (importada)", "cares": [], "importada": True})
        familia["cares"].append({"id": f["id"], "pes": str(f["pes"]), "estil": f["estil"], "format": f["format"]})
    return resultat + sorted(families.values(), key=lambda t: t["nom"].lower())


def css(tipografies: list[dict], url_estatic, url_importada) -> str:
    """Regles @font-face de totes les tipografies (el navegador només baixa les que es fan servir)."""
    regles = []
    for t in tipografies:
        for c in t["cares"]:
            if t.get("importada"):
                url, format_ = url_importada(c["id"]), FORMATS.get(c.get("format"), "truetype")
            else:
                url, format_ = url_estatic(c["fitxer"]), "woff2"
            regles.append(
                f'@font-face{{font-family:"{t["familia"]}";font-style:{c["estil"]};font-weight:{c["pes"]};'
                f'font-display:block;src:url("{url}") format("{format_}")}}')
    return "\n".join(regles)


def per_al_navegador(tipografies: list[dict]) -> list[dict]:
    """El que necessita el motor de dibuix: clau → família CSS amb la genèrica de reserva."""
    return [{"clau": t["clau"], "nom": t["nom"], "categoria": t["categoria"],
             "css": f'"{t["familia"]}", {GENERIQUES.get(t["categoria"], "sans-serif")}'} for t in tipografies]
