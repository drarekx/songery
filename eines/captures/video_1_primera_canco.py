"""Vídeo 1: crear un cançoner, afegir-hi una cançó i escriure'n la lletra amb acords."""
import time

from gravador import Gravador
from nav import LLEST, RECTANGLE, VIDEOS, boto, boto_conte, desa_id

g = Gravador("primera-canco")
try:
    g.obre("/")
    g.superposa()
    g.retol("1 · Crea un cançoner nou", 1.6)
    g.clica("document.querySelector('input[name=titol]')")
    g.tecleja("Cançons de foc de camp", 0.05)
    g.pausa(.5)
    g.clica(boto("Crea'l"), despres=0.1)
    g.sense_gravar(lambda: (time.sleep(1), g.espera(LLEST), time.sleep(1)))
    desa_id("foc-de-camp", g.avalua("location.pathname.split('/')[2]"))
    g.retol("S'obre l'editor, a la portada", 1.8)

    g.retol("2 · Afegeix-hi la primera cançó", 1.0)
    g.clica(boto("+ Cançó"), despres=1.2)   # deixa el cursor al camp del títol
    g.retol("Posa-li títol i autor", .6)
    g.tecleja("La lluna, la pruna", 0.06)
    g.pausa(.6)
    g.clica("document.querySelector('input[placeholder=\"Sense autor\"]')")
    g.tecleja("Popular catalana", 0.06)
    g.pausa(.6)
    g.tecla("Enter", "Enter", 13)
    g.pausa(1.0)

    g.retol("3 · Doble clic al marc de lletra per escriure-hi", 1.2)
    r = g.avalua(RECTANGLE.format(sel=".marc-lletra"))
    x, y = r[0] + 120, r[1] + 40
    g.clica((x, y), despres=0.15)
    # El doble clic simulat amb DevTools només selecciona el marc: s'envia l'esdeveniment, com als tests e2e.
    g.avalua(f"""(async () => {{ document.activeElement.blur(); const m = document.querySelector('.marc-lletra');
      m.dispatchEvent(new MouseEvent('dblclick', {{ bubbles: true, clientX: {x}, clientY: {y} }}));
      await new Promise((r) => setTimeout(r, 400)); m._editor.commands.focus('end'); }})()""")
    g.avalua(f"gvOna({x}, {y})")
    g.pausa(.8)
    g.retol("Escriu <kbd>[G]</kbd> just abans de la síl·laba per posar-hi un acord", 1.5)
    g.tecleja("[G]La lluna, la [D7]pruna,\nves[D7]tida de [G]dol,\n", 0.07)
    g.retol("L'acord queda ancorat a la síl·laba", .8)
    g.tecleja("son [G]pare la [D7]crida,\nsa [D7]mare no [G]vol.", 0.07)
    g.pausa(1.0)
    g.retol("Quan acabis, clica «Fet»", .8)
    g.clica(boto("Fet"), despres=1.0)
    g.retol("Ja tens la primera cançó: es desa sola", 1.2)
    g.clica(boto_conte("Tot el llibret"), despres=2.2)
    g.retol("«Tot el llibret» ensenya totes les pàgines, tal com sortiran al PDF", 3.0)
    g.munta(VIDEOS / "1-primera-canco.mp4", VIDEOS / "1-primera-canco.gif")
finally:
    g.tanca()
