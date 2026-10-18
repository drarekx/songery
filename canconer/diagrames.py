"""Diagrames d'acords de guitarra i d'ukulele en SVG.

Les posicions són llistes de trasts, de la corda més greu a la més aguda:
  - guitarra (6 cordes): Mi La Re Sol Si Mi
  - ukulele (4 cordes, afinació estàndard): Sol Do Mi La
-1 vol dir corda apagada (x) i 0 corda a l'aire (o).
Guitarra: si l'acord no és a la taula d'acords oberts, es calcula una cejilla amb la forma
de Mi (arrel a la 6a corda) o de La (arrel a la 5a corda).
Ukulele: es parteix dels acords oberts de Do, Re, Fa, Sol i La i es desplacen pel mànec.
"""

from __future__ import annotations

import re
from html import escape

from .parser import _SEMITO

X = -1

# Acords oberts habituals que no surten bé de les formes amb cejilla.
OBERTS: dict[str, list[int]] = {
    "C": [X, 3, 2, 0, 1, 0], "C7": [X, 3, 2, 3, 1, 0], "Cmaj7": [X, 3, 2, 0, 0, 0],
    "Cadd9": [X, 3, 2, 0, 3, 0], "Csus2": [X, 3, 0, 0, 1, 0], "Csus4": [X, 3, 3, 0, 1, 1],
    "D": [X, X, 0, 2, 3, 2], "Dm": [X, X, 0, 2, 3, 1], "D7": [X, X, 0, 2, 1, 2],
    "Dm7": [X, X, 0, 2, 1, 1], "Dmaj7": [X, X, 0, 2, 2, 2], "Dsus2": [X, X, 0, 2, 3, 0],
    "Dsus4": [X, X, 0, 2, 3, 3], "D6": [X, X, 0, 2, 0, 2],
    "G": [3, 2, 0, 0, 0, 3], "G7": [3, 2, 0, 0, 0, 1], "Gmaj7": [3, 2, 0, 0, 0, 2],
    "G6": [3, 2, 0, 0, 0, 0], "Gsus4": [3, X, 0, 0, 1, 3],
    "B7": [X, 2, 1, 2, 0, 2],
    "Fmaj7": [X, X, 3, 2, 1, 0],
}

# Formes mòbils relatives a l'arrel. Els 0 es converteixen en el trast de l'arrel.
FORMA_MI: dict[str, list[int]] = {
    "": [0, 2, 2, 1, 0, 0], "m": [0, 2, 2, 0, 0, 0], "7": [0, 2, 0, 1, 0, 0],
    "m7": [0, 2, 0, 0, 0, 0], "maj7": [0, 2, 1, 1, 0, 0], "sus4": [0, 2, 2, 2, 0, 0],
    "7sus4": [0, 2, 0, 2, 0, 0], "6": [0, 2, 2, 1, 2, 0], "m6": [0, 2, 2, 0, 2, 0],
    "aug": [0, 3, 2, 1, 1, 0], "5": [0, 2, 2, X, X, X],
}
FORMA_LA: dict[str, list[int]] = {
    "": [X, 0, 2, 2, 2, 0], "m": [X, 0, 2, 2, 1, 0], "7": [X, 0, 2, 0, 2, 0],
    "m7": [X, 0, 2, 0, 1, 0], "maj7": [X, 0, 2, 1, 2, 0], "sus2": [X, 0, 2, 2, 0, 0],
    "sus4": [X, 0, 2, 2, 3, 0], "7sus4": [X, 0, 2, 0, 3, 0], "6": [X, 0, 2, 2, 2, 2],
    "m6": [X, 0, 2, 2, 1, 2], "9": [X, 0, 2, 4, 2, 3], "add9": [X, 0, 2, 4, 2, 0],
    "dim": [X, 0, 1, 2, 1, X], "dim7": [X, 0, 1, 2, 1, 2], "m7b5": [X, 0, 1, 0, 1, X],
    "aug": [X, 0, 3, 2, 2, 1], "5": [X, 0, 2, 2, X, X], "m9": [X, 0, 2, 0, 0, 0],
}

# Sinònims de qualitats.
SINONIMS = {
    "min": "m", "-": "m", "M": "", "maj": "", "M7": "maj7", "Maj7": "maj7", "ma7": "maj7",
    "min7": "m7", "-7": "m7", "sus": "sus4", "+": "aug", "°": "dim", "o": "dim",
    "ø": "m7b5", "°7": "dim7", "2": "sus2", "4": "sus4", "add2": "add9",
}

_REGEX = re.compile(r"^([A-G](?:#|b)?)([^/]*)(?:/.*)?$")
_NOTA_MI = 4  # Mi (6a corda a l'aire)
_NOTA_LA = 9  # La (5a corda a l'aire)


# Ukulele: acords oberts per qualitat i nota arrel (semitò). Desplaçant-los n trasts
# (els 0 passen a ser una cejilla al trast n) s'obtenen totes les altres arrels.
FORMES_UKULELE: dict[str, dict[int, list[int]]] = {
    "": {0: [0, 0, 0, 3], 2: [2, 2, 2, 0], 5: [2, 0, 1, 0], 7: [0, 2, 3, 2], 9: [2, 1, 0, 0]},
    "m": {0: [0, 3, 3, 3], 2: [2, 2, 1, 0], 5: [1, 0, 1, 3], 7: [0, 2, 3, 1], 9: [2, 0, 0, 0]},
    "7": {0: [0, 0, 0, 1], 2: [2, 2, 2, 3], 5: [2, 3, 1, 0], 7: [0, 2, 1, 2], 9: [0, 1, 0, 0]},
    "m7": {0: [3, 3, 3, 3], 2: [2, 2, 1, 3], 5: [1, 3, 1, 3], 7: [0, 2, 1, 1], 9: [0, 0, 0, 0]},
    "maj7": {0: [0, 0, 0, 2], 2: [2, 2, 2, 4], 7: [0, 2, 2, 2], 9: [1, 1, 0, 0]},
    "sus4": {0: [0, 0, 1, 3], 2: [0, 2, 3, 0], 5: [3, 0, 1, 1], 7: [0, 2, 3, 3], 9: [2, 2, 0, 0]},
    "sus2": {0: [0, 2, 3, 3], 2: [2, 2, 0, 0], 5: [0, 0, 1, 3], 7: [0, 2, 3, 0]},
    "6": {0: [0, 0, 0, 0], 2: [2, 2, 2, 2], 5: [2, 2, 1, 3], 7: [0, 2, 0, 2], 9: [2, 4, 2, 4]},
    "m6": {0: [2, 3, 3, 3], 2: [2, 2, 1, 2], 9: [2, 4, 2, 3]},
    "aug": {0: [1, 0, 0, 3], 5: [2, 1, 1, 0]},
    "dim7": {0: [2, 3, 2, 3], 1: [0, 1, 0, 1]},
    "m7b5": {11: [2, 2, 1, 2]},
    "add9": {0: [0, 2, 0, 3]},
    "7sus4": {7: [0, 2, 1, 3], 9: [0, 2, 0, 0]},
}
# Qualitats que a l'ukulele es toquen amb una altra forma.
EQUIVALENTS_UKULELE = {"dim": "dim7", "9": "7", "5": "", "m9": "m7"}

CORDES = {"guitarra": 6, "ukulele": 4}


def _desplaca(forma: list[int], trast: int) -> list[int]:
    return [X if t == X else t + trast for t in forma]


def _parts(acord: str) -> tuple[int, str] | None:
    m = _REGEX.match(acord)
    if not m:
        return None
    arrel, qualitat = m.groups()
    semito = _SEMITO.get(arrel)
    if semito is None:
        return None
    return semito, SINONIMS.get(qualitat, qualitat)


def posicio(acord: str, instrument: str = "guitarra") -> tuple[list[int], int] | None:
    """Retorna (posició, trast de la cejilla o 0) o None si no se'n coneix cap.
    Els acords amb baix (D/F#) es mostren com l'acord sense baix."""
    parts = _parts(acord)
    if not parts:
        return None
    semito, qualitat = parts
    if instrument == "ukulele":
        return _posicio_ukulele(semito, qualitat)

    arrel = _REGEX.match(acord).group(1)
    if arrel + qualitat in OBERTS:
        return OBERTS[arrel + qualitat], 0
    candidates = []
    if qualitat in FORMA_MI:
        trast = (semito - _NOTA_MI) % 12
        candidates.append((_desplaca(FORMA_MI[qualitat], trast), trast))
    if qualitat in FORMA_LA:
        trast = (semito - _NOTA_LA) % 12
        candidates.append((_desplaca(FORMA_LA[qualitat], trast), trast))
    if not candidates:
        return None
    # La forma més a prop del capdamunt del mànec.
    return min(candidates, key=lambda c: max(t for t in c[0] if t != X))


def _posicio_ukulele(semito: int, qualitat: str) -> tuple[list[int], int] | None:
    formes = FORMES_UKULELE.get(qualitat) or FORMES_UKULELE.get(EQUIVALENTS_UKULELE.get(qualitat, "\0"))
    if not formes:
        return None
    candidates = []
    for arrel, forma in formes.items():
        trast = (semito - arrel) % 12
        # La cejilla només té sentit si la forma té cordes a l'aire que passen a ser premudes.
        candidates.append((_desplaca(forma, trast), trast if trast and 0 in forma else 0))
    return min(candidates, key=lambda c: (max(c[0]), c[1]))


def svg(acord: str, instrument: str = "guitarra") -> str:
    """Genera el diagrama SVG d'un acord (o un quadre buit amb el nom si no es coneix)."""
    trobat = posicio(acord, instrument)
    posicions, cejilla = trobat if trobat else (None, 0)
    n_cordes = CORDES.get(instrument, 6)
    ample, alt = 70, 92
    sep_c, sep_t, n_trasts, y0 = 9.5, 12, 5, 26
    amplada_mastil = sep_c * (n_cordes - 1)
    x0 = (ample - amplada_mastil) / 2 - 1
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ample} {alt}" '
        f'class="diagrama" role="img" aria-label="Acord {escape(acord)}">',
        f'<text x="{ample / 2}" y="11" text-anchor="middle" font-size="11" '
        f'font-weight="bold" font-family="sans-serif">{escape(acord)}</text>',
    ]
    if posicions is None:
        parts.append(f'<text x="{ample / 2}" y="55" text-anchor="middle" font-size="7" '
                     f'font-family="sans-serif" fill="#777">sense diagrama</text></svg>')
        return "".join(parts)

    premuts = [t for t in posicions if t > 0]
    inici = 1 if not premuts or max(premuts) <= n_trasts else min(premuts)

    # Cordes i trasts.
    for c in range(n_cordes):
        x = x0 + c * sep_c
        parts.append(f'<line x1="{x}" y1="{y0}" x2="{x}" y2="{y0 + sep_t * n_trasts}" '
                     f'stroke="#000" stroke-width="0.8"/>')
    for t in range(n_trasts + 1):
        y = y0 + t * sep_t
        gruix = 3 if (t == 0 and inici == 1) else 0.8
        parts.append(f'<line x1="{x0}" y1="{y}" x2="{x0 + amplada_mastil}" y2="{y}" '
                     f'stroke="#000" stroke-width="{gruix}"/>')
    if inici > 1:
        parts.append(f'<text x="{x0 + amplada_mastil + 3}" y="{y0 + sep_t * 0.75}" '
                     f'font-size="8" font-family="sans-serif">{inici}</text>')

    # Cejilla: des de la primera corda que sona fins a la més aguda, al trast de la forma mòbil.
    if cejilla:
        primera = next(i for i, t in enumerate(posicions) if t != X)
        y = y0 + (cejilla - inici + 0.5) * sep_t
        parts.append(f'<line x1="{x0 + primera * sep_c}" y1="{y}" x2="{x0 + amplada_mastil}" '
                     f'y2="{y}" stroke="#000" stroke-width="6" stroke-linecap="round"/>')

    for c, t in enumerate(posicions):
        x = x0 + c * sep_c
        if t == X:
            parts.append(f'<text x="{x}" y="{y0 - 4}" text-anchor="middle" font-size="8" '
                         f'font-family="sans-serif">×</text>')
        elif t == 0:
            parts.append(f'<circle cx="{x}" cy="{y0 - 6.5}" r="2.6" fill="none" '
                         f'stroke="#000" stroke-width="0.8"/>')
        else:
            y = y0 + (t - inici + 0.5) * sep_t
            parts.append(f'<circle cx="{x}" cy="{y}" r="3.6" fill="#000"/>')
    parts.append("</svg>")
    return "".join(parts)
