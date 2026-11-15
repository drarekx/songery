"""Captures de pantalla del README (docs/imatges), a 2880 × 1800."""
import subprocess
import time

from nav import IMATGES, LLEST, RECTANGLE, TANCA_PANELL_ACORDS, TREBALL, Nav, boto, boto_conte, boto_titol, llegeix_id

n = Nav(1440, 900, 2)
populars = llegeix_id("populars")


def arrossega(x1, y1, x2, y2):
    n.ratoli("mouseMoved", x1, y1)
    time.sleep(.3)
    n.ratoli("mousePressed", x1, y1, "left", 1, clickCount=1)
    for i in range(1, 31):
        n.ratoli("mouseMoved", x1 + (x2 - x1) * i / 30, y1 + (y2 - y1) * i / 30, "left", 1)
        time.sleep(.05)
    n.ratoli("mouseReleased", x2, y2, "left", 0, clickCount=1)


def diagrames():
    return n.avalua(RECTANGLE.format(sel=".el-diagrames"))


try:
    # Inici: només la part de dalt (la resta és buida).
    n.obre("/")
    time.sleep(1.5)
    n.captura(TREBALL / "inici.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(TREBALL / "inici.png"), "-vf", "crop=2880:1180:0:0",
                    str(IMATGES / "inici.png")], check=True)

    n.obre("/biblioteca")
    time.sleep(2)
    n.captura(IMATGES / "biblioteca.png")

    # Editor: «Els segadors» amb els diagrames dels acords a la dreta de la lletra.
    n.obre(f"/canconer/{populars}", LLEST)
    n.espera("document.querySelectorAll('.capa-elements [data-id]').length > 0")
    time.sleep(1)
    n.clic(*n.centre(boto_titol("Diagrames d'acords")))
    time.sleep(.8)
    n.clic(*n.centre(boto_titol("Tots els acords")))   # un clic els afegeix al mig de la pàgina
    time.sleep(1)
    n.clic(*n.centre(TANCA_PANELL_ACORDS))
    time.sleep(1.2)
    d = diagrames()
    n.clic(d[0] + d[2] - 30, d[1] + d[3] - 12)   # selecciona'ls
    time.sleep(.6)
    d = diagrames()
    arrossega(d[0], d[1] + d[3] / 2, 462, d[1] + d[3] / 2)   # nansa esquerra: més estrets
    time.sleep(.6)
    d = diagrames()
    arrossega(d[0] + d[2] / 2, d[1] + d[3], d[0] + d[2] / 2, d[1] + d[3] + 110)   # nansa de baix: més alts
    time.sleep(.6)
    d = diagrames()
    arrossega(d[0] + d[2] - 20, d[1] + d[3] - 10, d[0] + d[2] - 20, d[1] + d[3] - 10 - (d[1] - 232))   # amunt
    time.sleep(1)
    n.captura(IMATGES / "editor.png")

    n.clic(*n.centre(boto_conte("Tot el llibret")))
    time.sleep(3)
    n.captura(IMATGES / "tot-el-llibret.png")

    n.obre(f"/canconer/{populars}/imprimir")
    time.sleep(4)
    n.captura(IMATGES / "imprimir.png")
    n.clic(*n.centre(boto("Llibret 3D")))
    time.sleep(4)
    for _ in range(2):
        n.clic(*n.centre(boto_titol("Pàgina següent")))
        time.sleep(2)
    n.captura(IMATGES / "llibret-3d.png")
finally:
    n.tanca()
