"""Document d'una cançó: el format JSON de l'editor Tiptap (ProseMirror).

Esquema:
  doc       → bloc*
  bloc      → linia | seccio | nota | imatge
  linia     → (text | acord)*           una línia de lletra; una línia buida separa estrofes
  seccio    → text*                     etiqueta de secció: Intro, Tornada, Estrofa 1...
  nota      → text*                     indicació en petit: «x2», «només veus»...
  imatge    → (atom) attrs: src (id), posicio (esquerra|dreta|centre), amplada (% de l'amplada útil)
  acord     → (atom en línia) attrs: nom. S'ancora al caràcter que el segueix.
  marques del text: tonica (síl·laba tònica), bold, italic, cor (veus del cor), i amb un valor (attrs.valor):
  mida (em), font (clau de la tipografia), color i fons (color del text i del fons: #rrggbb o cmyk(...))

Exemple de línia: [acord G]"Camino pel " [acord D/F#]"sender de la " [acord Em]"muntanya"
"""

from __future__ import annotations

import copy
import re

from . import parser

TIPUS_BLOCS = {"linia", "seccio", "nota", "imatge"}
MARQUES = {"tonica", "bold", "italic", "cor"}


# Etiquetes de secció habituals a les webs d'acords (en anglès o castellà) → en català.
SECCIONS_CATALA = {
    "verse": "Estrofa", "verso": "Estrofa", "estrofa": "Estrofa",
    "chorus": "Tornada", "coro": "Tornada", "estribillo": "Tornada", "refrain": "Tornada", "hook": "Tornada",
    "pre-chorus": "Pre-tornada", "prechorus": "Pre-tornada", "pre chorus": "Pre-tornada", "pre-coro": "Pre-tornada",
    "post-chorus": "Post-tornada", "bridge": "Pont", "puente": "Pont",
    "intro": "Intro", "outro": "Final", "final": "Final", "ending": "Final", "coda": "Coda",
    "interlude": "Interludi", "interludio": "Interludi", "instrumental": "Instrumental", "solo": "Solo",
}


def etiqueta_catalana(etiqueta: str) -> str:
    """«Verse 1» → «Estrofa 1», «Chorus» → «Tornada»... Les que no es coneixen queden igual."""
    m = re.match(r"^\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ -]*?)\s*(\d+|[IVX]+)?\s*:?\s*$", etiqueta)
    if not m:
        return etiqueta
    nom = SECCIONS_CATALA.get(m.group(1).lower())
    return f"{nom} {m.group(2)}" if nom and m.group(2) else nom or etiqueta


def buit() -> dict:
    return {"type": "doc", "content": [{"type": "linia"}]}


def _text(text: str, marques: list[str] | None = None) -> dict:
    node = {"type": "text", "text": text}
    if marques:
        node["marks"] = [{"type": m} for m in marques]
    return node


def _acord(nom: str) -> dict:
    return {"type": "acord", "attrs": {"nom": nom}}


def _linia(contingut: list[dict] | None = None) -> dict:
    node = {"type": "linia"}
    contingut = [n for n in (contingut or []) if n.get("type") != "text" or n.get("text")]
    if contingut:
        node["content"] = contingut
    return node


# ---------------------------------------------------------------- Conversió del format de text


def linia_amb_acords(acords: str, lletra: str) -> dict:
    """Combina una línia d'acords i la de lletra de sota: cada acord s'ancora a la columna on és."""
    posicions = [(m.start(), m.group()) for m in re.finditer(r"\S+", acords)]
    contingut: list[dict] = []
    cursor = 0
    for columna, nom in posicions:
        if not parser.es_acord(nom):
            continue  # barres de compàs i repeticions es descarten
        if columna > len(lletra):
            lletra = lletra + " " * (columna - len(lletra))
        if columna > cursor:
            contingut.append(_text(lletra[cursor:columna]))
            cursor = columna
        contingut.append(_acord(nom))
    if cursor < len(lletra):
        contingut.append(_text(lletra[cursor:]))
    return _linia(contingut)


def linia_nomes_acords(text: str) -> dict:
    noms = [e for e in text.split() if parser.es_acord(e)]
    return _linia([_acord(n) for n in noms])


def de_text(text: str) -> dict:
    """Converteix el format de les webs de tabs (acords en una línia a sobre de la lletra)."""
    linies = parser.analitza(text)
    blocs: list[dict] = []
    i = 0
    while i < len(linies):
        l = linies[i]
        seguent = linies[i + 1] if i + 1 < len(linies) else None
        if l.tipus == "buida":
            if blocs and blocs[-1] != {"type": "linia"}:
                blocs.append({"type": "linia"})
        elif l.tipus == "seccio":
            etiqueta = etiqueta_catalana(l.etiqueta.strip("[]").strip())
            blocs.append({"type": "seccio", "content": [_text(etiqueta)]} if etiqueta else {"type": "seccio"})
            if l.resta_acords:
                blocs.append(linia_nomes_acords(l.resta))
            elif l.resta.strip():
                blocs.append(_linia([_text(l.resta.strip())]))
        elif l.tipus == "acords":
            if seguent is not None and seguent.tipus == "lletra":
                blocs.append(linia_amb_acords(l.text, seguent.text))
                i += 1
            else:
                blocs.append(linia_nomes_acords(l.text))
        else:
            blocs.append(_linia([_text(l.text)]))
        i += 1
    return {"type": "doc", "content": blocs or [{"type": "linia"}]}


def sembla_text_amb_acords(text: str) -> bool:
    """True si un text enganxat té línies d'acords (per convertir-lo en enganxar-lo a l'editor)."""
    return any(l.tipus == "acords" or (l.tipus == "seccio" and l.resta_acords) for l in parser.analitza(text))


def a_chordpro(doc: dict) -> str:
    """Text en format ChordPro: [G]Camino pel [D/F#]sender... (per exportar i per cercar)."""
    sortida = []
    for bloc in doc.get("content", []):
        tipus = bloc.get("type")
        if tipus == "seccio":
            sortida.append("{comment: %s}" % _text_pla(bloc))
        elif tipus == "nota":
            sortida.append("{comment_italic: %s}" % _text_pla(bloc))
        elif tipus == "imatge":
            sortida.append("{image: %s}" % bloc.get("attrs", {}).get("src", ""))
        else:
            sortida.append("".join(f"[{n['attrs']['nom']}]" if n["type"] == "acord" else n.get("text", "")
                                   for n in bloc.get("content", [])))
    return "\n".join(sortida)


def _text_pla(bloc: dict) -> str:
    return "".join(n.get("text", "") for n in bloc.get("content", []) if n.get("type") == "text")


# ---------------------------------------------------------------- Consultes i transformacions


def _acords_del_doc(doc: dict):
    for bloc in doc.get("content", []):
        for node in bloc.get("content", []) or []:
            if node.get("type") == "acord":
                yield node


def acords(doc: dict) -> list[str]:
    """Acords diferents en ordre d'aparició (sense N.C.)."""
    vistos: list[str] = []
    for node in _acords_del_doc(doc):
        nom = node.get("attrs", {}).get("nom", "")
        if nom and not nom.upper().startswith("N") and nom not in vistos:
            vistos.append(nom)
    return vistos


def transporta(doc: dict, semitons: int) -> dict:
    if semitons % 12 == 0:
        return doc
    nou = copy.deepcopy(doc)
    for node in _acords_del_doc(nou):
        node["attrs"]["nom"] = parser.transporta_acord(node["attrs"]["nom"], semitons)
    return nou


def imatges(doc: dict) -> list[str]:
    return [b["attrs"]["src"] for b in doc.get("content", [])
            if b.get("type") == "imatge" and b.get("attrs", {}).get("src")]


def de_canco(canco: dict) -> dict:
    """Document d'una cançó (accepta també el camp «cos» en text, del format antic)."""
    if canco.get("doc"):
        return canco["doc"]
    return de_text(canco.get("cos", ""))
