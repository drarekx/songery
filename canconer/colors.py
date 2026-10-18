"""Colors del disseny: RGB («#rrggbb») o CMYK exacte per a impremta («cmyk(c,m,y,k)», en %).

Els colors CMYK es dibuixen a la pantalla i al PDF de Chromium amb un RGB aproximat. Perquè al PDF
per a impremta surtin amb el valor CMYK exacte, cada color CMYK té un RGB «testimoni» únic dins del
cançoner (taula_testimonis): el PDF es dibuixa amb aquests testimonis i després cmyk.py els canvia
pels valors CMYK triats.
"""

from __future__ import annotations

import re

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_CMYK = re.compile(r"^cmyk\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*\)$")


def llegeix_cmyk(valor) -> tuple[float, float, float, float] | None:
    """«cmyk(0, 100, 100, 0)» → (0, 100, 100, 0) en %; None si no és CMYK vàlid."""
    m = _CMYK.match(str(valor or "").strip())
    if not m:
        return None
    try:
        parts = tuple(round(min(100.0, max(0.0, float(x))), 1) for x in m.groups())
    except ValueError:
        return None
    return parts  # type: ignore[return-value]


def text_cmyk(c: float, m: float, y: float, k: float) -> str:
    return "cmyk({})".format(",".join(f"{v:g}" for v in (c, m, y, k)))


def normalitza(valor, defecte: str = "") -> str:
    """Color vàlid en forma canònica («#rrggbb» en minúscules o «cmyk(c,m,y,k)»), o el defecte."""
    if isinstance(valor, str) and _HEX.match(valor):
        return valor.lower()
    cmyk = llegeix_cmyk(valor)
    return text_cmyk(*cmyk) if cmyk else defecte


# Color aproximat de cada tinta d'impremta (cian, magenta, groc, negre) sobre paper blanc.
TINTES = ((0, 158, 224), (226, 0, 122), (255, 236, 0), (30, 28, 27))


def a_rgb(c: float, m: float, y: float, k: float) -> tuple[int, int, int]:
    """Aproximació per a la pantalla (la mateixa fórmula que pagines.js): les tintes es multipliquen
    com sobre el paper, cadascuna en la seva proporció."""
    canals = []
    for canal in range(3):
        valor = 1.0
        for quantitat, tinta in zip((c, m, y, k), TINTES):
            valor *= 1 - quantitat / 100 * (1 - tinta[canal] / 255)
        canals.append(round(255 * valor))
    return tuple(canals)  # type: ignore[return-value]


def recull(dades) -> set[str]:
    """Tots els colors CMYK (canònics) que apareixen en una estructura (cançoner, pàgines…)."""
    trobats: set[str] = set()

    def recorre(x):
        if isinstance(x, str):
            if x.startswith("cmyk("):
                n = normalitza(x)
                if n:
                    trobats.add(n)
        elif isinstance(x, dict):
            for v in x.values():
                recorre(v)
        elif isinstance(x, list):
            for v in x:
                recorre(v)

    recorre(dades)
    return trobats


def taula_testimonis(colors) -> dict[str, str]:
    """Color CMYK → RGB testimoni («#rrggbb») únic. Determinista: el mateix conjunt dona la mateixa taula.

    El testimoni és l'aproximació de pantalla; si dos colors CMYK hi coincideixen (p. ex. negre
    100 % i negre ric), el segon es mou un punt en un canal fins que és únic: a la vista no es nota.
    """
    taula: dict[str, str] = {}
    usats: set[tuple[int, int, int]] = set()
    for color in sorted(colors):
        base = a_rgb(*llegeix_cmyk(color))
        for candidat in _veins(base):
            if candidat not in usats:
                break
        usats.add(candidat)
        taula[color] = "#{:02x}{:02x}{:02x}".format(*candidat)
    return taula


def _veins(rgb: tuple[int, int, int]):
    """El color i, després, els més propers: ±1, ±2… en el blau, el verd i el vermell."""
    yield rgb
    for distancia in range(1, 256):
        for canal in (2, 1, 0):
            for signe in (1, -1):
                valors = list(rgb)
                valors[canal] += signe * distancia
                if 0 <= valors[canal] <= 255:
                    yield tuple(valors)
