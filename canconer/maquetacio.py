"""Pla del llibret: quines pàgines hi ha i en quin ordre.

Les pàgines de cada cançó les dissenya l'usuari (vegeu plantilles.py); aquí només es munta la
seqüència i es resolen les dades que cada pàgina necessita per dibuixar-se:
  1            portada
  2..          índex (tantes pàgines com calgui), pàgina d'acords i índex de QR dels vídeos, si van
               al principi
  ...          cançons i pàgines lliures en ordre. Una cançó comença a l'esquerra (pàgina parella),
               amb una pàgina en blanc al davant si cal, tret que s'hagi marcat «on toqui».
  ...          pàgines en blanc fins arribar a un múltiple de 4 (o de 2 si els fulls van solts, amb
               anelles: vegeu marges.fulls_solts)
  ...          pàgina d'acords i índex de QR, si van al final
  N            contraportada
"""

from __future__ import annotations

import copy
import math

from . import colors, diagrames, document, marges, parser, plantilles, videos


def marge_de(canconer: dict) -> dict | None:
    """Mestra de marges del cançoner: la que ja porta (canconer["marge"]) o la desada a la base de dades."""
    if "marge" in canconer:
        return canconer["marge"]
    if not canconer.get("marges"):
        return None
    from . import basedades  # aquí per evitar una importació circular
    return basedades.carrega_marge(canconer["marges"])


def _transporta_pagines(pagines: list[dict], semitons: int) -> list[dict]:
    pagines = copy.deepcopy(pagines)
    if semitons % 12:
        for p in pagines:
            for e in p.get("elements", []):
                if e.get("tipus") == "lletra" and e.get("doc"):
                    e["doc"] = document.transporta(e["doc"], semitons)
                elif e.get("tipus") == "diagrama" and e.get("acord"):
                    e["acord"] = parser.transporta_acord(e["acord"], semitons)
    return pagines


def base_acord(acord: str) -> str:
    """El diagrama d'un acord amb baix (G/B) és el de l'acord (G)."""
    return acord.split("/")[0]


def diagrames_pagines(pagines: list[dict], instrument: str) -> tuple[list[str], dict[str, str]]:
    """Acords d'una cançó (sense repetir, en ordre) i el SVG de cada diagrama, també dels elements
    «diagrama» que hi hagi a les pàgines."""
    ordre: list[str] = []
    for a in acords_pagines(pagines):
        if base_acord(a) not in ordre:
            ordre.append(base_acord(a))
    solts = [base_acord(e["acord"]) for p in pagines for e in p.get("elements", [])
             if e.get("tipus") == "diagrama" and e.get("acord")]
    return ordre, {a: diagrames.svg(a, instrument) for a in dict.fromkeys(ordre + solts)}


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
    instrument = diagrames.instrument_valid(canconer.get("instrument"))

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
    # Amb guitarra i ukulele, la pàgina d'acords és una altra («acords_dos»): un bloc per a cada instrument,
    # amb els mateixos acords a cada pàgina.
    # Els blocs de diagrames poden triar l'instrument (element «instrument»): es donen els de tots dos.
    dos = instrument == "tots"
    per_instrument = ({i: [diagrames.svg(a, i) for a in tots_acords] for i in ("guitarra", "ukulele")}
                      if canconer.get("pagina_acords") else {"guitarra": [], "ukulele": []})
    svgs = per_instrument["guitarra" if dos else instrument]
    per_pagina = plantilles.DIAGRAMES_PER_INSTRUMENT if dos else plantilles.DIAGRAMES_PER_PAGINA
    pagines_acords = math.ceil(len(svgs) / per_pagina) if canconer.get("pagina_acords") and svgs else 0

    n_cancons = sum(1 for e in entrades if e.get("tipus", "canco") == "canco")
    pagines_index = (math.ceil(n_cancons / plantilles.ENTRADES_PER_PAGINA_INDEX)
                     if n_cancons and canconer.get("pagina_index", True) else 0)
    for i in range(pagines_index):
        afegeix("index", especials["index"], tros_index=i)

    def afegeix_acords():
        for i in range(pagines_acords):
            tros = slice(i * per_pagina, (i + 1) * per_pagina)
            tipus = "acords_dos" if dos else "acords"
            afegeix(tipus, especials[tipus], diagrames=svgs[tros],
                    diagrames_instrument={nom: llista[tros] for nom, llista in per_instrument.items()})

    # Vídeos marcats per a l'índex de QR, de les cançons que surten.
    videos_qr = []
    for e in entrades:
        contingut = e.get("contingut") or {}
        for v in videos.normalitza(contingut.get("videos") if isinstance(contingut, dict) else None):
            if v["inclou_qr"]:
                videos_qr.append({"entrada": e["id"], "canco": e.get("titol") or "Sense títol",
                                  "titol": v["titol"], "url": videos.url_curta(v)})
    pagines_qr = math.ceil(len(videos_qr) / plantilles.QR_PER_PAGINA_INDEX) if canconer.get("pagina_qr") else 0

    def afegeix_qr():
        for i in range(pagines_qr):
            afegeix("index_qr", especials["index_qr"], tros_qr=i)

    if canconer.get("posicio_acords") != "final":
        afegeix_acords()
    if canconer.get("posicio_qr") == "inici":
        afegeix_qr()

    inici_entrada: dict[str, int] = {}
    for e in entrades:
        pagines = pagines_per_entrada[e["id"]]
        if not pagines:
            continue
        if e.get("inici", "esquerra") == "esquerra" and (len(seq) + 1) % 2 == 1:
            afegeix("blanc", {"mestra": "estandard", "elements": []})
        acords = acords_pagines(pagines)
        contingut = e.get("contingut") if isinstance(e.get("contingut"), dict) else {}
        ordre_acords, svgs_canco = diagrames_pagines(pagines, instrument)
        context = {"titol": e.get("titol") or "", "autor": e.get("autor") or "", "acords": " · ".join(acords),
                   "videos": videos.per_al_dibuix(contingut.get("videos")),
                   "ordreAcords": ordre_acords, "diagrames": svgs_canco}
        inici = len(seq) + 1
        for i, model in enumerate(pagines):
            afegeix("canco" if e.get("tipus", "canco") == "canco" else "lliure", model, context,
                    entrada=e["id"], index_dins=i)
        inici_entrada[e["id"]] = inici
        if e.get("tipus", "canco") == "canco":
            cancons.append({"id": e["id"], "titol": e.get("titol") or "Sense títol", "autor": e.get("autor", ""),
                            "pagina_inici": inici, "pagines": len(pagines), "acords": acords})

    finals = (1 + (pagines_acords if canconer.get("posicio_acords") == "final" else 0)
              + (pagines_qr if canconer.get("posicio_qr") != "inici" else 0))
    solts = marges.fulls_solts(marge_de(canconer))
    while (len(seq) + finals) % (2 if solts else 4):
        afegeix("blanc", {"mestra": "estandard", "elements": []})
    if canconer.get("posicio_acords") == "final":
        afegeix_acords()
    if canconer.get("posicio_qr") != "inici":
        afegeix_qr()
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
        if "tros_qr" in p:
            t = p.pop("tros_qr")
            tros = videos_qr[t * plantilles.QR_PER_PAGINA_INDEX:(t + 1) * plantilles.QR_PER_PAGINA_INDEX]
            p["qrs"] = [{**{k: v for k, v in q.items() if k != "entrada"}, "pagina": inici_entrada.get(q["entrada"], "")}
                        for q in tros]

    return {
        "pagines": seq,
        "total": len(seq),
        "fulls": math.ceil(len(seq) / 4),
        "fulls_solts": solts,
        "cancons": cancons,
        "estils": canconer["estils"],
        "instrument": instrument,
        # RGB testimoni de cada color CMYK (per poder-los posar exactes al PDF per a impremta).
        "colors": colors.taula_testimonis(colors.recull([canconer["estils"], canconer.get("mestres"), seq])),
    }
