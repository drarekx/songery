"""PDF per a impremta, en CMYK.

1. Els colors CMYK triats a l'editor es dibuixen amb un RGB testimoni únic (colors.taula_testimonis).
   Aquí, a cada pàgina (i als formularis que hi hagi a dins), les ordres de color RGB d'aquests
   testimonis («r g b rg» / «RG») es canvien per les CMYK exactes («c m y k k» / «K»).
2. Ghostscript converteix a CMYK tota la resta (colors RGB, imatges) amb el seu perfil, i deixa
   com estan els colors que ja són CMYK.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ContentStream, FloatObject

from . import colors


class GhostscriptNoDisponible(RuntimeError):
    """No hi ha Ghostscript per convertir el PDF a CMYK."""


def ghostscript() -> str | None:
    """Camí de Ghostscript: el de l'app, el compilat per a l'app (desenvolupament) o el del sistema."""
    candidats = [os.environ.get("CANCONER_GS")]
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidats.append(str(Path(base) / "eines" / "ghostscript" / "gs"))
    candidats += [str(Path(__file__).resolve().parent.parent / "eines" / "ghostscript" / "gs"),
                  shutil.which("gs"), "/opt/homebrew/bin/gs", "/usr/local/bin/gs"]
    return next((c for c in candidats if c and os.path.isfile(c) and os.access(c, os.X_OK)), None)


def _rgb_255(operands) -> tuple[int, int, int] | None:
    try:
        return tuple(round(float(v) * 255) for v in operands)  # type: ignore[return-value]
    except (TypeError, ValueError):
        return None


def _transforma(pdf: bytes, canvi) -> tuple[bytes, int]:
    """Aplica canvi(operands, operador) → (operands, operador) | None a totes les ordres de les pàgines
    i dels formularis que contenen. Retorna el PDF i el nombre d'ordres canviades."""
    escriptor = PdfWriter(clone_from=BytesIO(pdf))
    canvis = 0
    vistos: set[int] = set()

    def aplica(contingut: ContentStream) -> int:
        n = 0
        for i, (operands, operador) in enumerate(contingut.operations):
            nou = canvi(operands, operador)
            if nou:
                contingut.operations[i] = nou
                n += 1
        return n

    def formularis(recursos):
        xobjectes = recursos.get("/XObject") if recursos else None
        for ref in (xobjectes or {}).values():
            objecte = ref.get_object()
            if objecte.get("/Subtype") == "/Form" and id(objecte) not in vistos:
                vistos.add(id(objecte))
                yield objecte

    def processa_formulari(formulari):
        nonlocal canvis
        contingut = ContentStream(formulari, escriptor)
        n = aplica(contingut)
        if n:
            formulari.set_data(contingut.get_data())
            canvis += n
        for intern in formularis(formulari.get("/Resources")):
            processa_formulari(intern)

    for pagina in escriptor.pages:
        if pagina.get_contents() is not None:
            contingut = ContentStream(pagina.get_contents(), escriptor)
            n = aplica(contingut)
            if n:
                pagina.replace_contents(contingut)
                canvis += n
        for formulari in formularis(pagina.get("/Resources")):
            processa_formulari(formulari)
    if not canvis:
        return pdf, 0
    sortida = BytesIO()
    escriptor.write(sortida)
    return sortida.getvalue(), canvis


def _operands_cmyk(valors) -> list:
    return [FloatObject(round(v / 100, 4)) for v in valors]


def substitueix_testimonis(pdf: bytes, taula: dict[str, str]) -> tuple[bytes, int]:
    """Canvia els colors RGB testimoni pels CMYK exactes. Retorna el PDF i el nombre de canvis."""
    if not taula:
        return pdf, 0
    testimonis = {tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)): colors.llegeix_cmyk(c) for c, h in taula.items()}

    def canvi(operands, operador):
        if operador in (b"rg", b"RG") and len(operands) == 3:
            valors = testimonis.get(_rgb_255(operands))
            if valors:
                return _operands_cmyk(valors), b"k" if operador == b"rg" else b"K"
        return None
    return _transforma(pdf, canvi)


def ajusta_cmyk(pdf: bytes, taula: dict[str, str], tolerancia: float = 0.0015) -> tuple[bytes, int]:
    """Ghostscript arrodoneix els CMYK internament (0,8 → 0,8008): els que queden a tocar d'un color
    triat es tornen a posar exactes."""
    objectius = [tuple(v / 100 for v in colors.llegeix_cmyk(c)) for c in taula]
    if not objectius:
        return pdf, 0

    def canvi(operands, operador):
        if operador in (b"k", b"K") and len(operands) == 4:
            try:
                actual = [float(v) for v in operands]
            except (TypeError, ValueError):
                return None
            for objectiu in objectius:
                if all(abs(a - o) <= tolerancia for a, o in zip(actual, objectiu)) and actual != list(objectiu):
                    return _operands_cmyk([v * 100 for v in objectiu]), operador
        return None
    return _transforma(pdf, canvi)


def converteix(pdf: bytes, taula: dict[str, str]) -> bytes:
    """PDF en CMYK per a impremta: colors triats en CMYK exactes i la resta convertida amb Ghostscript."""
    gs = ghostscript()
    if not gs:
        raise GhostscriptNoDisponible("No hi ha Ghostscript per fer el PDF en CMYK. "
                                      "L'app de Mac el porta a dins; des del codi font, executa eines/app/ghostscript.sh.")
    pdf, _ = substitueix_testimonis(pdf, taula)
    with tempfile.TemporaryDirectory() as temporal:
        entrada, sortida = Path(temporal) / "rgb.pdf", Path(temporal) / "cmyk.pdf"
        entrada.write_bytes(pdf)
        r = subprocess.run([gs, "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
                            "-sColorConversionStrategy=CMYK", "-sProcessColorModel=DeviceCMYK",
                            "-dAutoRotatePages=/None", "-dCompatibilityLevel=1.6",
                            "-dDownsampleColorImages=false", "-dDownsampleGrayImages=false",
                            "-dDownsampleMonoImages=false",
                            f"-sOutputFile={sortida}", str(entrada)], capture_output=True, text=True, timeout=600)
        if r.returncode or not sortida.exists():
            raise RuntimeError(f"Ghostscript no ha pogut convertir el PDF a CMYK: {(r.stderr or r.stdout)[-500:]}")
        return ajusta_cmyk(sortida.read_bytes(), taula)[0]


def colors_del_pdf(pdf: bytes) -> dict[str, set]:
    """Per a les proves: ordres de color de totes les pàgines ({"rg": {...}, "k": {...}})."""
    lector = PdfReader(BytesIO(pdf))
    trobats: dict[str, set] = {"rg": set(), "k": set()}
    for pagina in lector.pages:
        if pagina.get_contents() is None:
            continue
        for operands, operador in ContentStream(pagina.get_contents(), lector).operations:
            if operador in (b"rg", b"RG"):
                trobats["rg"].add(tuple(round(float(v), 4) for v in operands))
            elif operador in (b"k", b"K"):
                trobats["k"].add(tuple(round(float(v), 4) for v in operands))
    return trobats

