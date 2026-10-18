"""Pla del llibret: quines pàgines hi ha i en quin ordre.

Les pàgines de cada cançó les dissenya l'usuari (vegeu plantilles.py); aquí només es munta la
seqüència i es resolen les dades que cada pàgina necessita per dibuixar-se:
  1            portada
  2..          índex (tantes pàgines com calgui) i pàgina d'acords, si va al principi
  ...          cançons i pàgines lliures en ordre. Una cançó comença a l'esquerra (pàgina parella),
               amb una pàgina en blanc al davant si cal, tret que s'hagi marcat «on toqui».
  ...          pàgines en blanc fins arribar a un múltiple de 4
  ...          pàgina d'acords, si va al final
  N            contraportada
"""

from __future__ import annotations

import copy
import math

from . import diagrames, document, plantilles


def _transporta_pagines(pagines: list[dict], semitons: int) -> list[dict]:
    pagines = copy.deepcopy(pagines)
    if semitons % 12:
        for p in pagines:
            for e in p.get("elements", []):
                if e.get("tipus") == "lletra" and e.get("doc"):
                    e["doc"] = document.transporta(e["doc"], semitons)
    return pagines


def acords_pagines(pagines: list[dict]) -> list[str]:
    """Acords diferents dels marcs de lletra, en ordre d'aparició."""
    vistos: list[str] = []
    for p in pagines:
        for e in p.get("elements", []):
            if e.get("tipus") == "lletra" and e.get("doc"):
                for a in document.acords(e["doc"]):
                    if a not in vistos:
                        vistos.append(a)
    return vistos


def entrades_incloses(canconer: dict) -> list[dict]:
    return [c for c in canconer.get("cancons", []) if c.get("inclosa", True)]


def pagines_entrada(entrada: dict) -> list[dict]:
    """Pàgines d'una cançó amb el transport del cançoner aplicat."""
    contingut = plantilles.normalitza_contingut(entrada.get("contingut") or document.de_canco(entrada))
    return _transporta_pagines(contingut["pagines"], int(entrada.get("transport") or 0))


def _mestra(canconer: dict, id_mestra: str | None, numero: int, costat: str | None = None) -> dict | None:
    """Costat de la mestra: el forçat a la pàgina ("esquerra"/"dreta") o, si no n'hi ha, el de la paritat."""
    if not id_mestra:
        return None
    esquerra = costat == "esquerra" if costat in ("esquerra", "dreta") else numero % 2 == 0
    for m in canconer.get("mestres", []):
        if m["id"] == id_mestra:
            return m["parell" if esquerra else "senar"]
    return None


def pla(canconer: dict) -> dict:
    """Seqüència completa de pàgines amb tot el que cal per dibuixar-les."""
    especials = canconer["especials"]
    entrades = entrades_incloses(canconer)
    instrument = canconer.get("instrument") or "guitarra"

    cancons: list[dict] = []  # per a l'índex i la interfície
    seq: list[dict] = []
    context_llibre = {k: canconer.get(k, "") for k in ("titol", "subtitol", "any", "contraportada")}

    def afegeix(tipus: str, model: dict, context: dict | None = None, **extra) -> dict:
        p = {"tipus": tipus, "fons": model.get("fons", "#ffffff"), "id_mestra": model.get("mestra"),
             "costat_mestra": model.get("costat"),
             "elements": copy.deepcopy(model.get("elements", [])), "id_pagina": model.get("id"),
             "context": {**context_llibre, **(context or {})}, **extra}
        seq.append(p)
        return p

    afegeix("portada", especials["portada"])

    # Acords de les cançons que surten (per a la pàgina de diagrames).
    pagines_per_entrada = {e["id"]: pagines_entrada(e) for e in entrades}
    tots_acords: list[str] = []
    for e in entrades:
        for a in acords_pagines(pagines_per_entrada[e["id"]]):
            base = a.split("/")[0]
            if base not in tots_acords:
                tots_acords.append(base)
    svgs = [diagrames.svg(a, instrument) for a in tots_acords]
    pagines_acords = math.ceil(len(svgs) / plantilles.DIAGRAMES_PER_PAGINA) if canconer.get("pagina_acords") and svgs else 0

    n_cancons = sum(1 for e in entrades if e.get("tipus", "canco") == "canco")
    pagines_index = math.ceil(n_cancons / plantilles.ENTRADES_PER_PAGINA_INDEX) if n_cancons else 0
    for i in range(pagines_index):
        afegeix("index", especials["index"], tros_index=i)

    def afegeix_acords():
        for i in range(pagines_acords):
            tros = svgs[i * plantilles.DIAGRAMES_PER_PAGINA:(i + 1) * plantilles.DIAGRAMES_PER_PAGINA]
            afegeix("acords", especials["acords"], diagrames=tros)

    if canconer.get("posicio_acords") != "final":
        afegeix_acords()

    for e in entrades:
        pagines = pagines_per_entrada[e["id"]]
        if not pagines:
            continue
        if e.get("inici", "esquerra") == "esquerra" and (len(seq) + 1) % 2 == 1:
            afegeix("blanc", {"mestra": "estandard", "elements": []})
        acords = acords_pagines(pagines)
        context = {"titol": e.get("titol") or "", "autor": e.get("autor") or "", "acords": " · ".join(acords)}
        inici = len(seq) + 1
        for i, model in enumerate(pagines):
            afegeix("canco" if e.get("tipus", "canco") == "canco" else "lliure", model, context,
                    entrada=e["id"], index_dins=i)
        if e.get("tipus", "canco") == "canco":
            cancons.append({"id": e["id"], "titol": e.get("titol") or "Sense títol", "autor": e.get("autor", ""),
                            "pagina_inici": inici, "pagines": len(pagines), "acords": acords})

    finals = 1 + (pagines_acords if canconer.get("posicio_acords") == "final" else 0)
    while (len(seq) + finals) % 4:
        afegeix("blanc", {"mestra": "estandard", "elements": []})
    if canconer.get("posicio_acords") == "final":
        afegeix_acords()
    afegeix("contraportada", especials["contraportada"])

    # Números de pàgina, mestres i contingut de l'índex (ja se sap on comença cada cançó).
    index = [{"titol": c["titol"], "autor": c["autor"], "pagina": c["pagina_inici"]} for c in cancons]
    for numero, p in enumerate(seq, start=1):
        p["numero"] = numero
        p["costat"] = "parell" if numero % 2 == 0 else "senar"
        p["context"]["pagina"] = numero
        p["mestra"] = _mestra(canconer, p.pop("id_mestra"), numero, p.pop("costat_mestra"))
        if "tros_index" in p:
            t = p.pop("tros_index")
            p["index"] = index[t * plantilles.ENTRADES_PER_PAGINA_INDEX:(t + 1) * plantilles.ENTRADES_PER_PAGINA_INDEX]

    return {
        "pagines": seq,
        "total": len(seq),
        "fulls": len(seq) // 4,
        "cancons": cancons,
        "estils": canconer["estils"],
        "instrument": instrument,
    }
