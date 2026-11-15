"""Vídeo 3: la pàgina Imprimir del cançoner «Cançons populars» (fulls A4, llibret A5, llibret 3D i PDF)."""
import time

from gravador import Gravador
from nav import VIDEOS, boto, boto_conte, boto_titol, llegeix_id

g = Gravador("imprimir")


def roda(vegades, pas):
    g.mou(1000, 520, .7)
    for _ in range(vegades):
        g.s.crida("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": 1000, "y": 520, "deltaX": 0, "deltaY": pas})
        g.pausa(.12)


try:
    g.obre(f"/canconer/{llegeix_id('populars')}/imprimir")
    time.sleep(4)
    g.superposa()
    g.retol("A «Imprimir» veus el cançoner tal com sortirà", 2.0)
    g.retol("Fulls A4: dues pàgines A5 per cara, ja ordenades per plegar", 1.0)
    roda(14, 60)
    g.pausa(1.0)

    g.retol("Llibret A5: en ordre de lectura", .6)
    g.clica(boto("Llibret A5"), despres=.2)
    g.sense_gravar(lambda: time.sleep(2.5))
    g.pausa(.8)
    roda(16, 70)
    g.pausa(.8)

    g.retol("Llibret 3D: passa les pàgines com si el tinguessis a les mans", .6)
    g.clica(boto("Llibret 3D"), despres=.2)
    g.sense_gravar(lambda: time.sleep(4))
    g.pausa(1.6)
    g.retol("", .4)   # el rètol taparia els botons de passar pàgina
    for i in range(5):
        g.clica(boto_titol("Pàgina següent"), despres=1.7, durada=.5 if i == 0 else .1)

    g.retol("Baixa el PDF A4, imprimeix a doble cara, plega i cus pel mig", .8)
    g.avalua("window.scrollTo({top: 0})")
    g.pausa(.5)
    g.mou(*g.centre(boto_conte("PDF A4 per imprimir")), 1.0)
    g.pausa(2.8)
    g.munta(VIDEOS / "3-imprimir.mp4", VIDEOS / "3-imprimir.gif")
finally:
    g.tanca()
