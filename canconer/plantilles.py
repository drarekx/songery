"""Plantilles i valors per defecte del disseny de pàgines.

Cada pàgina és un llenç A5 (148 × 210 mm) amb elements col·locats en mil·límetres:
  lletra     marc amb la lletra i els acords (document Tiptap), amb ajust automàtic de mida
  text       text amb variables: {titol}, {autor}, {acords}, {subtitol}, {any}, {contraportada}, {pagina}
  imatge     imatge pujada
  forma      rectangle o el·lipse
  numero     número de pàgina (sobretot a les pàgines mestres)
  index      llista de cançons amb el número de pàgina (pàgina d'índex)
  diagrames  diagrames d'acords (pàgina d'acords)
Els elements de text fan servir un estil amb nom (Títol, Lletra, Acord...) i en poden canviar propietats.
"""

from __future__ import annotations

import copy
import uuid

from . import document

AMPLE = 148.0
ALT = 210.0

# Estils de text compartits per tot el cançoner.
ESTILS = {
    "titol": {"nom": "Títol", "font": "display", "mida": 18, "pes": 600, "cursiva": False, "color": "#1b1a17",
              "interlineat": 1.1, "espaiat": 0, "majuscules": False},
    "autor": {"nom": "Autor", "font": "display", "mida": 10, "pes": 400, "cursiva": True, "color": "#3a3832",
              "interlineat": 1.2, "espaiat": 0, "majuscules": False},
    "llista_acords": {"nom": "Llista d'acords", "font": "sans", "mida": 8.5, "pes": 700, "cursiva": False,
                      "color": "#b3261e", "interlineat": 1.2, "espaiat": 0.02, "majuscules": False},
    "lletra": {"nom": "Lletra", "font": "display", "mida": 11.5, "pes": 400, "cursiva": False, "color": "#1b1a17",
               "interlineat": 1.25, "espaiat": 0, "majuscules": False},
    "acord": {"nom": "Acord", "font": "sans", "mida": 9, "pes": 700, "cursiva": False, "color": "#b3261e",
              "interlineat": 1.2, "espaiat": 0, "majuscules": False},
    "seccio": {"nom": "Secció", "font": "sans", "mida": 7.5, "pes": 700, "cursiva": False, "color": "#6b665c",
               "interlineat": 1.3, "espaiat": 0.1, "majuscules": True},
    "nota": {"nom": "Nota", "font": "sans", "mida": 8.5, "pes": 400, "cursiva": True, "color": "#6b665c",
             "interlineat": 1.3, "espaiat": 0, "majuscules": False},
    "text": {"nom": "Text", "font": "sans", "mida": 10, "pes": 400, "cursiva": False, "color": "#1b1a17",
             "interlineat": 1.35, "espaiat": 0, "majuscules": False},
    "numero": {"nom": "Número de pàgina", "font": "sans", "mida": 9, "pes": 500, "cursiva": False, "color": "#6b665c",
               "interlineat": 1, "espaiat": 0, "majuscules": False},
    "index": {"nom": "Índex", "font": "display", "mida": 11, "pes": 400, "cursiva": False, "color": "#1b1a17",
              "interlineat": 1.5, "espaiat": 0, "majuscules": False},
}

FONTS = ("display", "sans", "mono")

# Línies d'índex i diagrames que caben en una pàgina (per saber quantes pàgines calen).
ENTRADES_PER_PAGINA_INDEX = 24
DIAGRAMES_PER_PAGINA = 20


def nou_id() -> str:
    return uuid.uuid4().hex[:8]


def _el(tipus: str, x: float, y: float, w: float, h: float, **propietats) -> dict:
    return {"id": nou_id(), "tipus": tipus, "x": x, "y": y, "w": w, "h": h, "rotacio": 0, "opacitat": 1, **propietats}


def mestres() -> list[dict]:
    """Pàgina mestra per defecte: número de pàgina a la cantonada exterior."""
    return [{
        "id": "estandard",
        "nom": "Estàndard",
        "parell": {"elements": [_el("numero", 11, 197, 30, 6, estil="numero", alineacio="left")]},
        "senar": {"elements": [_el("numero", 107, 197, 30, 6, estil="numero", alineacio="right")]},
    }]


def pagina(elements: list[dict], mestra: str | None = "estandard", fons: str = "#ffffff") -> dict:
    return {"id": nou_id(), "mestra": mestra, "fons": fons, "elements": elements}


def especials() -> dict:
    """Portada, índex, acords i contraportada per defecte."""
    return {
        "portada": pagina([
            _el("forma", 0, 0, 6, ALT, fons="#b3261e", radi=0, forma="rectangle"),
            _el("text", 18, 62, 112, 40, text="{titol}", estil="titol", alineacio="center", format={"mida": 30}),
            _el("text", 18, 106, 112, 10, text="{subtitol}", estil="text", alineacio="center",
                format={"mida": 13, "pes": 500, "color": "#3a3832"}),
            _el("text", 18, 180, 112, 8, text="{any}", estil="text", alineacio="center",
                format={"mida": 11, "pes": 600, "color": "#8a8478", "espaiat": 0.2}),
        ], mestra=None),
        "index": pagina([
            _el("text", 13, 14, 122, 12, text="Índex", estil="titol", alineacio="left"),
            _el("index", 13, 32, 122, 160, estil="index"),
        ]),
        "acords": pagina([
            _el("text", 13, 14, 122, 12, text="Acords", estil="titol", alineacio="left"),
            _el("diagrames", 13, 32, 122, 160),
        ]),
        "contraportada": pagina([
            _el("text", 20, 150, 108, 30, text="{contraportada}", estil="text", alineacio="center"),
        ], mestra=None),
    }


def pagina_canco(doc: dict, amb_capcalera: bool = True) -> dict:
    """Pàgina de cançó: títol, autor, acords i un marc de lletra que s'ajusta sol."""
    if not amb_capcalera:
        return pagina([_el("lletra", 13, 13, 122, 179, doc=doc, estil="lletra", ajusta=True, columnes=1)])
    return pagina([
        _el("text", 13, 12, 122, 10, text="{titol}", estil="titol", alineacio="left"),
        _el("text", 13, 22.5, 122, 6, text="{autor}", estil="autor", alineacio="left"),
        _el("text", 13, 29, 122, 5, text="{acords}", estil="llista_acords", alineacio="left"),
        _el("lletra", 13, 37, 122, 155, doc=doc, estil="lletra", ajusta=True, columnes=1),
    ])


def canco_nova() -> dict:
    return {"format": 2, "pagines": [pagina_canco(document.buit())]}


def _linies(doc: dict) -> int:
    return len(doc.get("content", []))


def de_document(doc: dict) -> dict:
    """Converteix una cançó del format anterior (un sol document) a pàgines.

    Si és llarga, es reparteix en dues pàgines (la doble pàgina del llibret obert), tallant per
    una estrofa a prop de la meitat. Els marcs s'ajusten sols perquè tot hi càpiga.
    """
    if _linies(doc) <= 34:
        return {"format": 2, "pagines": [pagina_canco(doc)]}
    blocs = doc["content"]
    meitat = len(blocs) // 2
    # Busca la línia buida (separació d'estrofes) més propera a la meitat.
    talls = [i for i, b in enumerate(blocs) if b.get("type") == "linia" and not b.get("content")] or [meitat]
    tall = min(talls, key=lambda i: abs(i - meitat))
    primera = {"type": "doc", "content": blocs[:tall] or [{"type": "linia"}]}
    segona = {"type": "doc", "content": blocs[tall + 1:] or [{"type": "linia"}]}
    return {"format": 2, "pagines": [pagina_canco(primera), pagina_canco(segona, amb_capcalera=False)]}


def es_format_pagines(contingut: dict) -> bool:
    return isinstance(contingut, dict) and contingut.get("format") == 2 and isinstance(contingut.get("pagines"), list)


def normalitza_contingut(contingut: dict) -> dict:
    """Accepta tant el format de pàgines com un document Tiptap sol (format anterior)."""
    if es_format_pagines(contingut):
        return contingut
    if isinstance(contingut, dict) and contingut.get("type") == "doc":
        return de_document(contingut)
    return canco_nova()


def de_disseny_antic(pagina_antiga: dict | None, nom: str) -> dict:
    """Converteix una portada o contraportada de l'editor anterior."""
    if not pagina_antiga:
        return especials()[nom]
    elements = []
    for e in pagina_antiga.get("elements", []):
        nou = {k: v for k, v in e.items() if k not in ("font", "mida", "pes", "cursiva", "color", "interlineat", "espaiat")}
        if e.get("tipus") == "text":
            nou["estil"] = "text"
            nou["format"] = {k: e[k] for k in ("font", "mida", "pes", "cursiva", "color", "interlineat", "espaiat") if k in e}
        elements.append(nou)
    return pagina(elements, mestra=None, fons=pagina_antiga.get("fons", "#ffffff"))


def amb_valors_per_defecte(meta: dict) -> dict:
    """Completa el disseny d'un cançoner (estils, mestres i pàgines especials)."""
    meta = copy.deepcopy(meta)
    estils = copy.deepcopy(ESTILS)
    for clau, valors in (meta.get("estils") or {}).items():
        estils[clau] = {**estils.get(clau, ESTILS["text"]), **valors}
    meta["estils"] = estils
    if not meta.get("mestres"):
        meta["mestres"] = mestres()
    per_defecte = especials()
    antic = meta.get("disseny") or {}
    actuals = meta.get("especials") or {}
    meta["especials"] = {}
    for nom in ("portada", "index", "acords", "contraportada"):
        if actuals.get(nom):
            meta["especials"][nom] = actuals[nom]
        elif nom in ("portada", "contraportada") and antic.get(nom):
            meta["especials"][nom] = de_disseny_antic(antic[nom], nom)
        else:
            meta["especials"][nom] = per_defecte[nom]
    return meta
