"""Genera les icones de l'app: icona.icns (Finder i Dock) i icona-menu.png (barra de menú).

    python eines/app/icones.py
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

AQUI = Path(__file__).resolve().parent
NEGRE = (20, 20, 20, 255)
BLANC = (255, 255, 255, 255)
GRIS = (166, 166, 166, 255)


def icona_app(mida: int = 1024) -> Image.Image:
    """Quadrat arrodonit negre amb un llibret obert (el logo), a l'estil de les icones de macOS.

    El dibuix segueix el logo de la web (viewBox de 64 × 64) dins el quadrat de 824 px de macOS."""
    k = mida / 1024
    u = 824 / 64  # una unitat del logo, en píxels de la icona de 1024

    def punt(x: float, y: float) -> tuple[float, float]:
        return ((100 + x * u) * k, (100 + y * u) * k)

    img = Image.new("RGBA", (mida, mida), (0, 0, 0, 0))
    # Ombra suau
    ombra = Image.new("RGBA", (mida, mida), (0, 0, 0, 0))
    ImageDraw.Draw(ombra).rounded_rectangle([100 * k, 118 * k, 924 * k, 942 * k], radius=185 * k, fill=(0, 0, 0, 90))
    img.alpha_composite(ombra.filter(ImageFilter.GaussianBlur(18 * k)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([100 * k, 100 * k, 924 * k, 924 * k], radius=185 * k, fill=NEGRE)
    # Llibret obert: dues pàgines lleugerament inclinades, amb línies de lletra
    d.polygon([punt(13, 18.5), punt(30.5, 22), punt(30.5, 47), punt(13, 43.5)], fill=BLANC)
    d.polygon([punt(33.5, 22), punt(51, 18.5), punt(51, 43.5), punt(33.5, 47)], fill=BLANC)
    gruix = max(1, int(1.6 * u * k))
    for (x1, y1, x2, y2) in [(17, 27.5, 26.5, 29.4), (17, 32.3, 26.5, 34.2), (17, 37.1, 23.5, 38.4),
                             (37.5, 29.4, 47, 27.5), (37.5, 34.2, 47, 32.3), (37.5, 39, 44, 37.7)]:
        d.line([punt(x1, y1), punt(x2, y2)], fill=GRIS, width=gruix)
    return img


def icona_menu(mida: int = 44) -> Image.Image:
    """Icona de plantilla (negre amb transparència) per a la barra de menú: un llibret obert."""
    img = Image.new("RGBA", (mida, mida), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = mida / 44
    negre = (0, 0, 0, 255)
    d.polygon([(4 * k, 9 * k), (21 * k, 12 * k), (21 * k, 38 * k), (4 * k, 35 * k)], fill=negre)
    d.polygon([(23 * k, 12 * k), (40 * k, 9 * k), (40 * k, 35 * k), (23 * k, 38 * k)], fill=negre)
    return img


def main() -> None:
    icona_menu().save(AQUI / "icona-menu.png")
    conjunt = AQUI / "icona.iconset"
    shutil.rmtree(conjunt, ignore_errors=True)
    conjunt.mkdir()
    gran = icona_app(1024)
    for mida in (16, 32, 128, 256, 512):
        gran.resize((mida, mida), Image.LANCZOS).save(conjunt / f"icon_{mida}x{mida}.png")
        gran.resize((mida * 2, mida * 2), Image.LANCZOS).save(conjunt / f"icon_{mida}x{mida}@2x.png")
    subprocess.run(["iconutil", "-c", "icns", str(conjunt), "-o", str(AQUI / "icona.icns")], check=True)
    shutil.rmtree(conjunt)
    gran.resize((256, 256), Image.LANCZOS).save(AQUI / "icona.png")
    print("Icones generades a", AQUI)


if __name__ == "__main__":
    main()
