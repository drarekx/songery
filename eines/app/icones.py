"""Genera les icones de l'app: icona.icns (Finder i Dock) i icona-menu.png (barra de menú).

    python eines/app/icones.py
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

AQUI = Path(__file__).resolve().parent
VERMELLO = (196, 50, 31, 255)


def icona_app(mida: int = 1024) -> Image.Image:
    """Quadrat arrodonit vermelló amb un llibret obert, a l'estil de les icones de macOS."""
    k = mida / 1024
    img = Image.new("RGBA", (mida, mida), (0, 0, 0, 0))
    # Ombra suau
    ombra = Image.new("RGBA", (mida, mida), (0, 0, 0, 0))
    ImageDraw.Draw(ombra).rounded_rectangle([100 * k, 118 * k, 924 * k, 942 * k], radius=185 * k, fill=(0, 0, 0, 90))
    img.alpha_composite(ombra.filter(ImageFilter.GaussianBlur(18 * k)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([100 * k, 100 * k, 924 * k, 924 * k], radius=185 * k, fill=VERMELLO)
    # Llibret obert: dues pàgines amb el plec al mig i línies de lletra
    blanc = (255, 255, 255, 255)
    d.polygon([(250 * k, 300 * k), (500 * k, 340 * k), (500 * k, 760 * k), (250 * k, 720 * k)], fill=blanc)
    d.polygon([(524 * k, 340 * k), (774 * k, 300 * k), (774 * k, 720 * k), (524 * k, 760 * k)], fill=blanc)
    for i in range(5):
        y = 410 + i * 62
        d.line([(300 * k, (y - 8) * k), (450 * k, (y + 16) * k)], fill=(*VERMELLO[:3], 200), width=int(14 * k))
        d.line([(574 * k, (y + 16) * k), (724 * k, (y - 8) * k)], fill=(210, 205, 196, 255), width=int(14 * k))
    return img


def icona_menu(mida: int = 44) -> Image.Image:
    """Icona de plantilla (negre amb transparència) per a la barra de menú: un llibret obert."""
    img = Image.new("RGBA", (mida, mida), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = mida / 44
    negre = (0, 0, 0, 255)
    d.polygon([(4 * k, 9 * k), (21 * k, 12 * k), (21 * k, 38 * k), (4 * k, 35 * k)], outline=negre, width=int(3 * k))
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
