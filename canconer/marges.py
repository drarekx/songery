"""Mestres de marges per a l'enquadernació (cosit, encolat, anelles…).

Una mestra de marges diu quant espai cal deixar a cada vora de la pàgina A5 impresa. El marge
interior és el del plec (o el llom): a les pàgines parells (esquerra) és la vora dreta i a les
senars (dreta), l'esquerra. Com que s'aplica al PDF A5 en ordre de lectura, abans de la
imposició, el marge interior queda sempre al costat del plec, tant a les cares de davant com a
les del darrere.

Les pàgines s'escalen (sense deformar-les) perquè hi càpiguen dins dels marges: no es retalla
res. La mestra «Sense marges» no toca el PDF, així que la sortida és idèntica a la de sempre.

Opcionalment es poden marcar els forats de les anelles al marge interior.
"""

from __future__ import annotations

import hashlib
import json
from io import BytesIO

from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from pypdf.generic import DecodedStreamObject, NameObject

PT_MM = 72 / 25.4
MARGE_MAXIM = 40  # mm
SENSE_MARGES = "cap"

PREDEFINIDES = [
    {"id": SENSE_MARGES, "nom": "Sense marges", "interior": 0, "exterior": 0, "superior": 0, "inferior": 0,
     "forats": 0, "diametre": 5, "distancia": 7, "separacio": 80},
    {"id": "cosit", "nom": "Cosit o grapat", "interior": 4, "exterior": 0, "superior": 0, "inferior": 0,
     "forats": 0, "diametre": 5, "distancia": 7, "separacio": 80},
    {"id": "encolat", "nom": "Encolat", "interior": 9, "exterior": 0, "superior": 0, "inferior": 0,
     "forats": 0, "diametre": 5, "distancia": 7, "separacio": 80},
    {"id": "anelles", "nom": "Anelles o volanderes", "interior": 14, "exterior": 3, "superior": 3, "inferior": 3,
     "forats": 2, "diametre": 6, "distancia": 7, "separacio": 80},
]


def _num(valor, defecte: float, minim: float, maxim: float) -> float:
    try:
        n = float(str(valor).replace(",", "."))
    except (TypeError, ValueError):
        return defecte
    if n != n:  # NaN
        return defecte
    return round(min(maxim, max(minim, n)), 1)


def normalitza(d: dict, id_marge: str | None = None) -> dict:
    """Valida una mestra de marges (ve d'un formulari o de la base de dades)."""
    d = d if isinstance(d, dict) else {}
    return {
        "id": id_marge or str(d.get("id") or ""),
        "nom": (str(d.get("nom") or "").strip() or "Marges")[:60],
        **{costat: _num(d.get(costat), 0, 0, MARGE_MAXIM) for costat in ("interior", "exterior", "superior", "inferior")},
        "forats": int(_num(d.get("forats"), 0, 0, 4)),
        "diametre": _num(d.get("diametre"), 5, 1, 12),
        "distancia": _num(d.get("distancia"), 7, 2, MARGE_MAXIM),
        "separacio": _num(d.get("separacio"), 80, 10, 190),
    }


def actiu(marge: dict | None) -> bool:
    """Si la mestra canvia el PDF (si no, la sortida és exactament la de sempre)."""
    return bool(marge) and (any(marge.get(c) for c in ("interior", "exterior", "superior", "inferior"))
                            or marge.get("forats", 0) > 0)


def empremta(marge: dict) -> str:
    """Hash de la mestra (sense el nom): per a la memòria cau dels PDF."""
    dades = {k: v for k, v in normalitza(marge).items() if k not in ("id", "nom")}
    return hashlib.sha256(json.dumps(dades, sort_keys=True).encode()).hexdigest()[:10]


def escala(marge: dict, ample_mm: float = 148, alt_mm: float = 210) -> float:
    """Escala a què queda la pàgina per deixar-hi els marges."""
    return min((ample_mm - marge["interior"] - marge["exterior"]) / ample_mm,
               (alt_mm - marge["superior"] - marge["inferior"]) / alt_mm)


def _cercle(cx: float, cy: float, r: float) -> str:
    k = 0.5523 * r
    return (f"{cx + r:.2f} {cy:.2f} m "
            f"{cx + r:.2f} {cy + k:.2f} {cx + k:.2f} {cy + r:.2f} {cx:.2f} {cy + r:.2f} c "
            f"{cx - k:.2f} {cy + r:.2f} {cx - r:.2f} {cy + k:.2f} {cx - r:.2f} {cy:.2f} c "
            f"{cx - r:.2f} {cy - k:.2f} {cx - k:.2f} {cy - r:.2f} {cx:.2f} {cy - r:.2f} c "
            f"{cx + k:.2f} {cy - r:.2f} {cx + r:.2f} {cy - k:.2f} {cx + r:.2f} {cy:.2f} c S ")


def posicions_forats(marge: dict, alt_mm: float = 210) -> list[float]:
    """Alçades (mm des de dalt) dels centres dels forats, repartits al voltant del mig."""
    n = marge.get("forats", 0)
    return [alt_mm / 2 + (i - (n - 1) / 2) * marge["separacio"] for i in range(n)]


def _forats(pagina: PageObject, marge: dict, esquerra: bool, ample: float, alt: float) -> None:
    """Dibuixa els forats (cercle gris i creueta) al marge interior."""
    r = marge["diametre"] / 2 * PT_MM
    x = ample - marge["distancia"] * PT_MM if esquerra else marge["distancia"] * PT_MM
    ordres = "q 0.55 G 0.4 w "
    for y_mm in posicions_forats(marge, alt / PT_MM):
        y = alt - y_mm * PT_MM
        ordres += _cercle(x, y, r)
        ordres += f"{x - r * 0.4:.2f} {y:.2f} m {x + r * 0.4:.2f} {y:.2f} l {x:.2f} {y - r * 0.4:.2f} m {x:.2f} {y + r * 0.4:.2f} l S "
    ordres += "Q"
    capa = PageObject.create_blank_page(width=ample, height=alt)
    contingut = DecodedStreamObject()
    contingut.set_data(ordres.encode())
    capa[NameObject("/Contents")] = contingut
    pagina.merge_page(capa)


def aplica(pdf_a5: bytes, marge: dict) -> bytes:
    """Retorna el PDF A5 amb els marges aplicats (cada pàgina escalada dins dels seus marges)."""
    if not actiu(marge):
        return pdf_a5
    lector = PdfReader(BytesIO(pdf_a5))
    escriptor = PdfWriter()
    for i, origen in enumerate(lector.pages):
        caixa = origen.mediabox
        ample, alt = float(caixa.width), float(caixa.height)
        esquerra = (i + 1) % 2 == 0  # pàgina parell: a l'esquerra, amb el plec a la dreta
        interior, exterior = marge["interior"] * PT_MM, marge["exterior"] * PT_MM
        superior, inferior = marge["superior"] * PT_MM, marge["inferior"] * PT_MM
        s = min((ample - interior - exterior) / ample, (alt - superior - inferior) / alt)
        x_zona = exterior if esquerra else interior
        x = x_zona + (ample - interior - exterior - ample * s) / 2
        y = inferior + (alt - superior - inferior - alt * s) / 2
        pagina = PageObject.create_blank_page(width=ample, height=alt)
        pagina.merge_transformed_page(origen, Transformation()
                                      .translate(-float(caixa.left), -float(caixa.bottom)).scale(s).translate(x, y))
        if marge.get("forats"):
            _forats(pagina, marge, esquerra, ample, alt)
        escriptor.add_page(pagina)
    sortida = BytesIO()
    escriptor.write(sortida)
    return sortida.getvalue()
