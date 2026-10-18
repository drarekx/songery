"""Imposició per a enquadernació a cavallet (fulls plegats un dins l'altre i cosits pel plec).

Cada full A4 horitzontal té dues cares i cada cara porta dues pàgines A5 una al costat de l'altra.
Amb N pàgines (múltiple de 4) hi ha F = N/4 fulls. Per al full i (0..F-1):
  - cara davantera: esquerra = N - 2i,   dreta = 1 + 2i
  - cara del darrere: esquerra = 2 + 2i, dreta = N - 1 - 2i
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from pypdf import PageObject, PdfReader, PdfWriter, Transformation

# Mides en punts PostScript.
A5_AMPLE = 419.53
A5_ALT = 595.28
A4_AMPLE = 841.89  # A4 en horitzontal
A4_ALT = 595.28


@dataclass(frozen=True)
class Cara:
    full: int  # 1..F
    costat: str  # "davant" o "darrere"
    esquerra: int  # número de pàgina (1..N)
    dreta: int


def ordre_imposicio(n: int) -> list[Cara]:
    """Retorna les cares en l'ordre d'impressió (davant full 1, darrere full 1, davant full 2...)."""
    if n <= 0 or n % 4 != 0:
        raise ValueError(f"El nombre de pàgines ha de ser múltiple de 4 (és {n}).")
    cares: list[Cara] = []
    for i in range(n // 4):
        cares.append(Cara(i + 1, "davant", n - 2 * i, 1 + 2 * i))
        cares.append(Cara(i + 1, "darrere", 2 + 2 * i, n - 1 - 2 * i))
    return cares


def parelles(n: int) -> list[tuple[int, int]]:
    """Només les parelles (esquerra, dreta), p. ex. N=12: (12,1), (2,11), (10,3)..."""
    return [(c.esquerra, c.dreta) for c in ordre_imposicio(n)]


def _cara_a4(lector: PdfReader, esquerra: int, dreta: int, girada: bool = False) -> PageObject:
    """Munta una cara A4 horitzontal amb dues pàgines A5 a escala 1:1.

    girada=True gira tota la cara 180° (per a impressores que fan la doble cara per la vora llarga).
    """
    cara = PageObject.create_blank_page(width=A4_AMPLE, height=A4_ALT)
    for numero, desplacament in ((esquerra, 0), (dreta, A4_AMPLE / 2)):
        origen = lector.pages[numero - 1]
        caixa = origen.mediabox
        # Centra la pàgina dins la seva meitat per si la mida no és exactament A5.
        dx = desplacament + (A4_AMPLE / 2 - float(caixa.width)) / 2 - float(caixa.left)
        dy = (A4_ALT - float(caixa.height)) / 2 - float(caixa.bottom)
        cara.merge_transformed_page(origen, Transformation().translate(dx, dy))
    if girada:
        cara.add_transformation(Transformation().rotate(180).translate(A4_AMPLE, A4_ALT))
    return cara


def _escriu(lector: PdfReader, cares: list[Cara], gira_darrere: bool = False) -> bytes:
    escriptor = PdfWriter()
    for c in cares:
        escriptor.add_page(_cara_a4(lector, c.esquerra, c.dreta, girada=gira_darrere and c.costat == "darrere"))
    sortida = BytesIO()
    escriptor.write(sortida)
    return sortida.getvalue()


def imposa(pdf_a5: bytes, costat: str | None = None, invers: bool = False, gira_darrere: bool = False) -> bytes:
    """Genera el PDF A4 imposat a partir del PDF A5 en ordre de lectura.

    costat=None: totes les cares (per imprimir a doble cara girant per la vora curta).
    costat="davant" o "darrere": només aquestes cares (impressores sense doble cara).
    invers=True: inverteix l'ordre dels fulls (útil per a les cares del darrere segons la impressora).
    gira_darrere=True: gira 180° les cares del darrere. Serveix quan la impressora fa la doble cara
    per la vora llarga (en lloc de la curta) i les pàgines del darrere surten del revés.
    """
    lector = PdfReader(BytesIO(pdf_a5))
    cares = ordre_imposicio(len(lector.pages))
    if costat:
        cares = [c for c in cares if c.costat == costat]
    if invers:
        cares = list(reversed(cares))
    return _escriu(lector, cares, gira_darrere)
