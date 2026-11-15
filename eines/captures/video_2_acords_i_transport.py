"""Vídeo 2: diagrames d'acords i transport, al cançoner que ha creat el vídeo 1."""
import time

from gravador import Gravador
from nav import LLEST, RECTANGLE, TANCA_PANELL_ACORDS, VIDEOS, boto, boto_conte, boto_titol, llegeix_id

g = Gravador("acords-i-transport")
try:
    g.obre(f"/canconer/{llegeix_id('foc-de-camp')}", LLEST)
    time.sleep(1)
    g.superposa()
    g.retol("Obre la cançó des de la llista", 1.2)
    g.clica(boto_conte("La lluna, la pruna"), despres=1.5)

    g.retol("1 · Diagrames d'acords: obre'ls a la barra d'eines", 1.0)
    g.clica(boto_titol("Diagrames d'acords"), despres=1.2)
    r = g.avalua(RECTANGLE.format(sel=".pagina-editor"))
    g.retol("Arrossega «Tots els acords» a la pàgina", .8)
    g.arrossega_v(boto_titol("Tots els acords"), (r[0] + r[2] * 0.5, r[1] + r[3] * 0.62))
    g.pausa(.8)
    g.clica(TANCA_PANELL_ACORDS, despres=1.2)
    g.retol("Els diagrames segueixen els acords de la lletra", 2.0)

    g.retol("2 · Transport: puja o baixa el to de la cançó", 1.0)
    g.clica(boto("Cançó"), despres=.9)   # amb el diagrama seleccionat, el panell és a «Disseny»
    for _ in range(2):
        g.clica(boto_titol("Puja un semitò"), despres=1.3)
    g.retol("Acords i diagrames canvien sols (de G a A)", 2.5)
    acords = g.avalua("document.querySelector('.estil-llista_acords').textContent")
    assert acords == "A · E7", f"El transport no s'ha aplicat: {acords}"

    g.retol("3 · Afegeix-hi text, imatges, formes o un codi QR des de la barra", 1.0)
    for nom in ("Text", "Imatge", "Rectangle", "Codi QR"):
        g.mou(*g.centre(boto_titol(nom)), .45)
        g.pausa(.45)
    g.pausa(1.2)
    g.munta(VIDEOS / "2-acords-i-transport.mp4", VIDEOS / "2-acords-i-transport.gif")
finally:
    g.tanca()
