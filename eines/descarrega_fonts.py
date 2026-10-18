"""Descarrega el catàleg de tipografies (fontsource, via jsDelivr) a canconer/static/fonts/cataleg/.

Les fonts es desen dins de l'aplicació perquè funcioni sense connexió i perquè Gotenberg les pugui
fer servir en generar el PDF. Només es baixa el subconjunt «latin» (inclou à, ç, l·l...).

    python eines/descarrega_fonts.py
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

DESTI = Path(__file__).resolve().parent.parent / "canconer" / "static" / "fonts" / "cataleg"
CDN = "https://cdn.jsdelivr.net/npm"
API = "https://data.jsdelivr.com/v1/package/npm"

# (identificador de fontsource, nom, categoria)
CATALEG = [
    # Serif
    ("playfair-display", "Playfair Display", "serif"), ("lora", "Lora", "serif"),
    ("merriweather", "Merriweather", "serif"), ("eb-garamond", "EB Garamond", "serif"),
    ("cormorant-garamond", "Cormorant Garamond", "serif"), ("libre-baskerville", "Libre Baskerville", "serif"),
    ("crimson-pro", "Crimson Pro", "serif"), ("pt-serif", "PT Serif", "serif"),
    ("source-serif-4", "Source Serif 4", "serif"), ("noto-serif", "Noto Serif", "serif"),
    ("spectral", "Spectral", "serif"), ("alegreya", "Alegreya", "serif"),
    ("bitter", "Bitter", "serif"), ("roboto-slab", "Roboto Slab", "serif"),
    ("zilla-slab", "Zilla Slab", "serif"), ("arvo", "Arvo", "serif"),
    ("dm-serif-display", "DM Serif Display", "serif"), ("fraunces", "Fraunces", "serif"),
    # Sans
    ("roboto", "Roboto", "sans"), ("open-sans", "Open Sans", "sans"), ("lato", "Lato", "sans"),
    ("montserrat", "Montserrat", "sans"), ("raleway", "Raleway", "sans"), ("poppins", "Poppins", "sans"),
    ("nunito", "Nunito", "sans"), ("work-sans", "Work Sans", "sans"), ("rubik", "Rubik", "sans"),
    ("inter", "Inter", "sans"), ("dm-sans", "DM Sans", "sans"), ("fira-sans", "Fira Sans", "sans"),
    ("karla", "Karla", "sans"), ("mulish", "Mulish", "sans"), ("barlow", "Barlow", "sans"),
    ("source-sans-3", "Source Sans 3", "sans"), ("pt-sans", "PT Sans", "sans"), ("cabin", "Cabin", "sans"),
    ("josefin-sans", "Josefin Sans", "sans"), ("quicksand", "Quicksand", "sans"), ("oswald", "Oswald", "sans"),
    ("archivo", "Archivo", "sans"), ("comfortaa", "Comfortaa", "sans"),
    # Display
    ("bebas-neue", "Bebas Neue", "display"), ("abril-fatface", "Abril Fatface", "display"),
    ("righteous", "Righteous", "display"), ("lobster", "Lobster", "display"),
    ("alfa-slab-one", "Alfa Slab One", "display"), ("special-elite", "Special Elite", "display"),
    # Manuscrites
    ("pacifico", "Pacifico", "manuscrita"), ("dancing-script", "Dancing Script", "manuscrita"),
    ("caveat", "Caveat", "manuscrita"), ("great-vibes", "Great Vibes", "manuscrita"),
    ("satisfy", "Satisfy", "manuscrita"), ("amatic-sc", "Amatic SC", "manuscrita"),
    ("indie-flower", "Indie Flower", "manuscrita"), ("permanent-marker", "Permanent Marker", "manuscrita"),
    ("shadows-into-light", "Shadows Into Light", "manuscrita"), ("patrick-hand", "Patrick Hand", "manuscrita"),
    ("kalam", "Kalam", "manuscrita"),
    # Monoespaiades
    ("roboto-mono", "Roboto Mono", "mono"), ("space-mono", "Space Mono", "mono"),
    ("courier-prime", "Courier Prime", "mono"), ("ibm-plex-mono", "IBM Plex Mono", "mono"),
]


def _json(url: str):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def _baixa(url: str, desti: Path) -> bool:
    if desti.exists():
        return True
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            desti.write_bytes(r.read())
        return True
    except OSError as e:
        print(f"  ! {url}: {e}", file=sys.stderr)
        return False


def fitxers_variable(clau: str) -> list[dict]:
    """Fonts variables: un fitxer per estil amb tots els gruixos (wght)."""
    try:
        versio = _json(f"{API}/@fontsource-variable/{clau}")["tags"]["latest"]
        noms = [f["name"] for f in _json(f"{API}/@fontsource-variable/{clau}@{versio}/flat")["files"]]
    except OSError:
        return []
    resultat = []
    for estil in ("normal", "italic"):
        cami = f"/files/{clau}-latin-wght-{estil}.woff2"
        if cami in noms:
            resultat.append({"url": f"{CDN}/@fontsource-variable/{clau}@{versio}{cami}", "pes": "100 900", "estil": estil})
    return resultat


def fitxers_estatics(clau: str) -> list[dict]:
    """Fonts no variables: els gruixos 400 i 700 (normal i cursiva) que existeixin."""
    versio = _json(f"{API}/@fontsource/{clau}")["tags"]["latest"]
    noms = {f["name"] for f in _json(f"{API}/@fontsource/{clau}@{versio}/flat")["files"]}
    resultat = []
    for pes in (400, 700):
        for estil in ("normal", "italic"):
            cami = f"/files/{clau}-latin-{pes}-{estil}.woff2"
            if cami in noms:
                resultat.append({"url": f"{CDN}/@fontsource/{clau}@{versio}{cami}", "pes": str(pes), "estil": estil})
    if not resultat:  # algunes fonts només tenen un gruix (p. ex. Bebas Neue)
        for nom in sorted(noms):
            m = re.match(rf"/files/{clau}-latin-(\d+)-(normal|italic)\.woff2$", nom)
            if m:
                resultat.append({"url": f"{CDN}/@fontsource/{clau}@{versio}{nom}", "pes": m[1], "estil": m[2]})
    return resultat


def main() -> None:
    DESTI.mkdir(parents=True, exist_ok=True)
    manifest = []
    for clau, nom, categoria in CATALEG:
        print(f"{nom}…")
        fitxers = fitxers_variable(clau) or fitxers_estatics(clau)
        cares = []
        for f in fitxers:
            fitxer = f"{clau}-{f['pes'].replace(' ', '-')}-{f['estil']}.woff2"
            if _baixa(f["url"], DESTI / fitxer):
                cares.append({"fitxer": fitxer, "pes": f["pes"], "estil": f["estil"]})
        if cares:
            manifest.append({"clau": clau, "nom": nom, "categoria": categoria, "cares": cares})
        else:
            print(f"  ! sense fitxers per a {nom}", file=sys.stderr)
    (DESTI / "fonts.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), "utf-8")
    print(f"{len(manifest)} tipografies a {DESTI}")


if __name__ == "__main__":
    main()
