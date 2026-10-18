"""Validació del disseny de pàgines que envia el navegador (elements, estils i pàgines mestres).

Tot el que arriba de l'editor passa per aquí abans de desar-se: es limiten els valors numèrics,
es comproven els colors i es descarten els tipus desconeguts.
"""

from __future__ import annotations

import re
import uuid

from . import colors, plantilles, videos

AMPLE = plantilles.AMPLE
ALT = plantilles.ALT
TIPUS = ("text", "lletra", "imatge", "forma", "numero", "index", "diagrames", "qr", "index_qr", "diagrama")
_CLAU = re.compile(r"^[a-z0-9_]{1,32}$")
_FONT = re.compile(r"^[a-z0-9-]{1,48}$")
_GRUP = re.compile(r"^[a-z0-9]{1,16}$")


def _id() -> str:
    return uuid.uuid4().hex[:8]


def _num(valor, defecte: float, minim: float, maxim: float) -> float:
    try:
        return round(max(minim, min(maxim, float(valor))), 3)
    except (TypeError, ValueError):
        return defecte


def _color(valor, defecte: str = "") -> str:
    """«#rrggbb» o, per a impremta, «cmyk(c,m,y,k)» en %."""
    return colors.normalitza(valor, defecte)


def _format(valor) -> dict:
    """Propietats d'estil sobreescrites en un element."""
    if not isinstance(valor, dict):
        return {}
    net = {}
    # Clau de tipografia: les de base, les del catàleg o les importades (u-...). Si no existeix, es
    # dibuixa amb la tipografia de reserva.
    if isinstance(valor.get("font"), str) and _FONT.match(valor["font"]):
        net["font"] = valor["font"]
    if "mida" in valor:
        net["mida"] = _num(valor["mida"], 10, 3, 300)
    if "pes" in valor:
        net["pes"] = int(_num(valor["pes"], 400, 100, 900))
    for clau in ("cursiva", "majuscules"):
        if clau in valor:
            net[clau] = bool(valor[clau])
    if _color(valor.get("color")):
        net["color"] = valor["color"]
    if "interlineat" in valor:
        net["interlineat"] = _num(valor["interlineat"], 1.2, 0.6, 4)
    if "espaiat" in valor:
        net["espaiat"] = _num(valor["espaiat"], 0, -0.3, 2)
    return net


def _doc(valor) -> dict:
    if isinstance(valor, dict) and valor.get("type") == "doc" and isinstance(valor.get("content", []), list):
        return valor
    return {"type": "doc", "content": [{"type": "linia"}]}


def element(e: dict) -> dict | None:
    if not isinstance(e, dict) or e.get("tipus") not in TIPUS:
        return None
    net = {
        "id": str(e.get("id") or _id())[:16],
        "tipus": e["tipus"],
        "x": _num(e.get("x"), 10, -AMPLE, 2 * AMPLE),
        "y": _num(e.get("y"), 10, -ALT, 2 * ALT),
        "w": _num(e.get("w"), 50, 1, 3 * AMPLE),
        "h": _num(e.get("h"), 20, 1, 3 * ALT),
        "rotacio": _num(e.get("rotacio"), 0, -360, 360),
        "opacitat": _num(e.get("opacitat"), 1, 0, 1),
    }
    if e.get("bloquejat"):
        net["bloquejat"] = True
    if isinstance(e.get("grup"), str) and _GRUP.match(e["grup"]):
        net["grup"] = e["grup"]  # els elements amb el mateix grup es seleccionen i es mouen junts
    if isinstance(e.get("estil"), str) and _CLAU.match(e["estil"]):
        net["estil"] = e["estil"]
    if e.get("format"):
        net["format"] = _format(e["format"])
    if e["tipus"] in ("text", "numero", "index", "index_qr"):
        net["alineacio"] = e.get("alineacio") if e.get("alineacio") in ("left", "center", "right", "justify") else "left"
    if e["tipus"] == "text":
        net["text"] = str(e.get("text", ""))[:4000]
    elif e["tipus"] == "lletra":
        net["doc"] = _doc(e.get("doc"))
        net["ajusta"] = e.get("ajusta") is not False
        net["columnes"] = int(_num(e.get("columnes"), 1, 1, 4))
        net["separacio"] = _num(e.get("separacio"), 6, 0, 40)
    elif e["tipus"] == "imatge":
        net["src"] = str(e.get("src", ""))[:32]
        net["ajust"] = "contain" if e.get("ajust") == "contain" else "cover"
        net["radi"] = _num(e.get("radi"), 0, 0, 200)
    elif e["tipus"] == "forma":
        net["forma"] = "elipse" if e.get("forma") == "elipse" else "rectangle"
        net["fons"] = "" if e.get("fons") == "" else _color(e.get("fons"), "#b3261e")
        net["radi"] = _num(e.get("radi"), 0, 0, 200)
        net["vora"] = _color(e.get("vora"))
        net["gruix"] = _num(e.get("gruix"), 0, 0, 30)
    elif e["tipus"] == "qr":
        net["video"] = str(e.get("video") or "")[:16]
        net["peu"] = bool(e.get("peu", True))
        net["color"] = _color(e.get("color"), "cmyk(0,0,0,100)")
    elif e["tipus"] == "diagrama":
        net["acord"] = str(e.get("acord") or "")[:16]
    elif e["tipus"] == "diagrames":
        # Amb "canco", tots els acords de la cançó (a la pàgina d'acords, els de tot el cançoner).
        if e.get("canco"):
            net["canco"] = True
        if e.get("mida") or e.get("canco"):
            net["mida"] = _num(e.get("mida"), 16, 8, 60)  # amplada de cada diagrama, en mm
    return net


def elements(llista) -> list[dict]:
    return [n for n in (element(e) for e in (llista or [])[:200]) if n]


COSTATS = ("esquerra", "dreta")


def pagina(p: dict | None) -> dict:
    if not isinstance(p, dict):
        return plantilles.pagina([])
    mestra = p.get("mestra")
    net = {
        "id": str(p.get("id") or _id())[:16],
        "mestra": mestra if isinstance(mestra, str) and _CLAU.match(mestra) else None,
        "fons": _color(p.get("fons"), "#ffffff"),
        "elements": elements(p.get("elements")),
    }
    # Costat de la mestra forçat ("esquerra" o "dreta"); si no hi és, segueix la paritat de la pàgina.
    if p.get("costat") in COSTATS:
        net["costat"] = p["costat"]
    return net


def contingut(c: dict) -> dict:
    """Contingut d'una cançó (format de pàgines)."""
    pagines = c.get("pagines") if isinstance(c, dict) else None
    if not isinstance(pagines, list) or not pagines:
        raise ValueError("La cançó ha de tenir com a mínim una pàgina.")
    net = {"format": 2, "pagines": [pagina(p) for p in pagines[:40]]}
    if c.get("videos"):
        net["videos"] = videos.normalitza(c["videos"])
    return net


def estils(valor) -> dict:
    if not isinstance(valor, dict):
        return {}
    net = {}
    for clau, e in list(valor.items())[:60]:
        if not _CLAU.match(str(clau)) or not isinstance(e, dict):
            continue
        base = plantilles.ESTILS.get(clau, plantilles.ESTILS["text"])
        net[clau] = {**base, **_format({**base, **e}), "nom": str(e.get("nom") or base["nom"])[:60]}
    return net


def mestres(valor) -> list[dict]:
    if not isinstance(valor, list):
        return []
    net = []
    for m in valor[:20]:
        if not isinstance(m, dict) or not _CLAU.match(str(m.get("id", ""))):
            continue
        net.append({
            "id": m["id"],
            "nom": str(m.get("nom") or "Mestra")[:60],
            "parell": {"elements": elements((m.get("parell") or {}).get("elements"))},
            "senar": {"elements": elements((m.get("senar") or {}).get("elements"))},
        })
    return net


def especials(valor) -> dict:
    if not isinstance(valor, dict):
        return {}
    return {nom: pagina(valor[nom]) for nom in plantilles.ESPECIALS if nom in valor}
