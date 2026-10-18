"""Parser de cançons en format "acords a sobre de la lletra".

El cos d'una cançó és text pla. Cada línia pot ser:
  - una línia d'acords (tots els elements són acords, p. ex. "G   D/F#  Em"),
  - una etiqueta de secció ("[Chorus]", "[Verse 1]"...), opcionalment seguida d'acords,
  - una línia de lletra,
  - una línia buida (separa estrofes).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Nota arrel: A-G amb alteració opcional.
_NOTA = r"[A-G](?:#|b)?"
# Qualitats i extensions acceptades darrere de l'arrel (es poden encadenar: m7b5, maj7, sus4, add9...).
_QUALITAT = r"(?:maj|Maj|min|dim|aug|sus|add|m|M|\+|-|°|ø|\d|#|b|\(|\))*"
REGEX_ACORD = re.compile(rf"^(?:N\.?C\.?|{_NOTA}{_QUALITAT}(?:/{_NOTA})?)$")

# Elements neutres que poden aparèixer en una línia d'acords sense ser-ne (barres de compàs, repeticions).
REGEX_NEUTRE = re.compile(r"^(?:\|+|:?\|\|?:?|%|-+|\(?x\d+\)?)$", re.IGNORECASE)

REGEX_SECCIO = re.compile(r"^(\s*)(\[[^\]]+\])(.*)$")

NOTES_SOSTINGUDES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTES_BEMOLLS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
# Grafia per a notes naturals després de transportar (barreja habitual en guitarra).
NOTES_PREFERIDES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
_SEMITO = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "Fb": 4, "E#": 5,
    "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11, "B#": 0,
}


def es_acord(element: str) -> bool:
    """Retorna True si l'element és un acord vàlid (inclou N.C.)."""
    return bool(REGEX_ACORD.match(element))


def es_linia_acords(linia: str) -> bool:
    """Una línia és d'acords si tots els seus elements són acords (o separadors neutres)
    i n'hi ha com a mínim un d'acord de veritat."""
    elements = linia.split()
    if not elements:
        return False
    hi_ha_acord = False
    for element in elements:
        if es_acord(element):
            hi_ha_acord = True
        elif not REGEX_NEUTRE.match(element):
            return False
    return hi_ha_acord


@dataclass
class Linia:
    """Una línia ja classificada.

    tipus: "acords", "lletra", "buida" o "seccio".
    etiqueta: text de l'etiqueta de secció (només si tipus == "seccio").
    resta: el que hi ha després de l'etiqueta, amb els espais originals.
    resta_acords: True si la resta és una línia d'acords.
    """

    text: str
    tipus: str
    etiqueta: str = ""
    prefix: str = ""
    resta: str = ""
    resta_acords: bool = False


def normalitza(cos: str) -> list[str]:
    """Separa el cos en línies, converteix tabuladors en espais i treu espais finals."""
    cos = cos.replace("\r\n", "\n").replace("\r", "\n")
    return [l.expandtabs(8).rstrip() for l in cos.split("\n")]


def classifica_linia(linia: str) -> Linia:
    if not linia.strip():
        return Linia(linia, "buida")
    m = REGEX_SECCIO.match(linia)
    if m:
        prefix, etiqueta, resta = m.groups()
        return Linia(linia, "seccio", etiqueta=etiqueta, prefix=prefix, resta=resta,
                     resta_acords=es_linia_acords(resta))
    if es_linia_acords(linia):
        return Linia(linia, "acords")
    return Linia(linia, "lletra")


def analitza(cos: str) -> list[Linia]:
    """Classifica totes les línies del cos."""
    linies = normalitza(cos)
    # Treu línies buides a l'inici i al final.
    while linies and not linies[0].strip():
        linies.pop(0)
    while linies and not linies[-1].strip():
        linies.pop()
    return [classifica_linia(l) for l in linies]


def estrofes(linies: list[Linia]) -> list[list[Linia]]:
    """Agrupa les línies en estrofes separades per línies buides."""
    blocs: list[list[Linia]] = []
    actual: list[Linia] = []
    for linia in linies:
        if linia.tipus == "buida":
            if actual:
                blocs.append(actual)
                actual = []
        else:
            actual.append(linia)
    if actual:
        blocs.append(actual)
    return blocs


def _acords_de_text(text: str) -> list[str]:
    return [e for e in text.split() if es_acord(e)]


def acords_utilitzats(cos: str) -> list[str]:
    """Llista d'acords diferents de la cançó, en ordre d'aparició (sense N.C.)."""
    vistos: list[str] = []
    for linia in analitza(cos):
        if linia.tipus == "acords":
            candidats = _acords_de_text(linia.text)
        elif linia.tipus == "seccio" and linia.resta_acords:
            candidats = _acords_de_text(linia.resta)
        else:
            continue
        for acord in candidats:
            if acord.upper().startswith("N.C") or acord.upper() == "NC":
                continue
            if acord not in vistos:
                vistos.append(acord)
    return vistos


# ---------------------------------------------------------------- Transport


def transporta_nota(nota: str, semitons: int) -> str:
    """Transporta una nota (C, F#, Bb...) un nombre de semitons.

    Es manté el tipus d'alteració de l'original (F# → G#, Bb → C, Eb → Gb);
    les notes naturals fan servir la grafia més habitual en guitarra (C → Eb, E → F#)."""
    index = (_SEMITO[nota] + semitons) % 12
    if nota.endswith("#"):
        return NOTES_SOSTINGUDES[index]
    if nota.endswith("b"):
        return NOTES_BEMOLLS[index]
    return NOTES_PREFERIDES[index]


_REGEX_PARTS = re.compile(rf"^({_NOTA})(.*?)(?:/({_NOTA}))?$")


def transporta_acord(acord: str, semitons: int) -> str:
    """Transporta un acord, incloent-hi el baix (D/F# → E/G#). N.C. no canvia."""
    if semitons % 12 == 0 or not es_acord(acord) or acord.upper().startswith("N"):
        return acord
    m = _REGEX_PARTS.match(acord)
    if not m:
        return acord
    arrel, qualitat, baix = m.groups()
    resultat = transporta_nota(arrel, semitons) + qualitat
    if baix:
        resultat += "/" + transporta_nota(baix, semitons)
    return resultat


def transporta_linia_acords(linia: str, semitons: int) -> str:
    """Transporta una línia d'acords mantenint cada acord a la mateixa columna.

    Si un acord s'allarga, es mengen espais del següent buit (deixant-ne com a mínim un);
    si s'escurça, s'hi afegeixen espais. Així els acords continuen sobre la síl·laba correcta.
    """
    resultat = ""
    for m in re.finditer(r"\S+", linia):
        inici = m.start()
        element = m.group()
        nou = transporta_acord(element, semitons) if es_acord(element) else element
        if len(resultat) < inici:
            resultat += " " * (inici - len(resultat))
        elif resultat:
            resultat += " "  # l'acord anterior s'ha allargat: deixem un espai com a mínim
        resultat += nou
    return resultat


def transporta_cos(cos: str, semitons: int) -> str:
    """Transporta totes les línies d'acords d'un cos de cançó."""
    if semitons % 12 == 0:
        return cos
    sortida = []
    for text in normalitza(cos):
        linia = classifica_linia(text)
        if linia.tipus == "acords":
            sortida.append(transporta_linia_acords(text, semitons))
        elif linia.tipus == "seccio" and linia.resta_acords:
            cap = linia.prefix + linia.etiqueta
            # Es transporta la línia sencera amb l'etiqueta substituïda per espais,
            # perquè les columnes es mantinguin.
            cos_linia = transporta_linia_acords(" " * len(cap) + linia.resta, semitons)
            sortida.append(cap + cos_linia[len(cap):])
        else:
            sortida.append(text)
    return "\n".join(sortida)


def amplada_maxima(cos: str) -> int:
    """Nombre de caràcters de la línia més llarga."""
    return max((len(l) for l in normalitza(cos)), default=0)
