"""Colors CMYK exactes per a impremta."""
from io import BytesIO

import pytest
from pypdf import PageObject, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from canconer import cmyk, colors, disseny, imposicio, maquetacio, pdf, plantilles


def test_validacio_i_forma_canonica():
    assert colors.normalitza("cmyk( 0, 100 ,100,0 )") == "cmyk(0,100,100,0)"
    assert colors.normalitza("cmyk(12.5,0,80,3)") == "cmyk(12.5,0,80,3)"
    assert colors.normalitza("cmyk(150,-1,0,0)") == ""  # el «-» no és vàlid
    assert colors.normalitza("#ABCDEF") == "#abcdef"
    assert colors.normalitza("red", "#000000") == "#000000"
    assert disseny.element({"tipus": "forma", "fons": "cmyk(0,0,0,100)", "vora": "cmyk(10,0,0,0)"})["fons"] == "cmyk(0,0,0,100)"
    assert disseny.estils({"titol": {"color": "cmyk(0,85,90,25)"}})["titol"]["color"] == "cmyk(0,85,90,25)"


def test_testimonis_unics_i_deterministes():
    llista = ["cmyk(0,0,0,100)", "cmyk(60,40,40,100)", "cmyk(30,30,30,100)", "cmyk(0,100,100,0)"]
    taula = colors.taula_testimonis(llista)
    assert len(set(taula.values())) == 4
    assert taula["cmyk(0,0,0,100)"] == "#{:02x}{:02x}{:02x}".format(*colors.a_rgb(0, 0, 0, 100))
    assert colors.taula_testimonis(reversed(llista)) == taula


def test_el_pla_porta_la_taula_de_colors():
    c = plantilles.amb_valors_per_defecte({"titol": "K", "cancons": [], "pagina_acords": False})
    pla = maquetacio.pla(c)
    assert "cmyk(0,0,0,100)" in pla["colors"]  # el color per defecte de la lletra
    assert all(v.startswith("#") for v in pla["colors"].values())


def _pdf_amb_colors(taula, extra=""):
    def rgb(h):
        return " ".join(f"{int(h[i:i + 2], 16) / 255:.4f}" for i in (1, 3, 5))
    ops = "".join(f"{rgb(h)} rg {10 + i * 60} 10 50 50 re f " for i, h in enumerate(taula.values())) + extra
    escriptor = PdfWriter()
    for _ in range(4):
        pagina = PageObject.create_blank_page(width=imposicio.A5_AMPLE, height=imposicio.A5_ALT)
        contingut = DecodedStreamObject()
        contingut.set_data(ops.encode())
        pagina[NameObject("/Contents")] = contingut
        escriptor.add_page(pagina)
    sortida = BytesIO()
    escriptor.write(sortida)
    return sortida.getvalue()


def test_substitucio_dels_testimonis():
    taula = colors.taula_testimonis(["cmyk(0,100,100,0)", "cmyk(60,40,40,100)"])
    nou, canvis = cmyk.substitueix_testimonis(_pdf_amb_colors(taula, "0.2 0.6 0.9 rg 0 0 5 5 re f"), taula)
    trobats = cmyk.colors_del_pdf(nou)
    assert canvis == 8 and trobats["k"] == {(0.0, 1.0, 1.0, 0.0), (0.6, 0.4, 0.4, 1.0)}
    assert trobats["rg"] == {(0.2, 0.6, 0.9)}  # els colors RGB que no són testimonis no es toquen


@pytest.mark.skipif(not cmyk.ghostscript(), reason="cal Ghostscript (eines/app/ghostscript.sh)")
def test_pdf_cmyk_amb_els_valors_exactes(monkeypatch, tmp_path):
    taula = colors.taula_testimonis(["cmyk(0,100,100,0)", "cmyk(60,40,40,100)", "cmyk(12.5,0,80,3)"])
    monkeypatch.setattr(pdf, "genera_a5", lambda *a, **k: _pdf_amb_colors(taula, "0.2 0.6 0.9 rg 0 0 5 5 re f"))
    monkeypatch.setattr(pdf, "_directori_cau", lambda: tmp_path)
    c = {"titol": "K"}
    for tipus in ("a5-cmyk", "a4-cmyk"):
        trobats = cmyk.colors_del_pdf(pdf.genera(c, tipus, "", colors_cmyk=taula))
        assert not trobats["rg"], tipus  # res en RGB
        assert {(0.0, 1.0, 1.0, 0.0), (0.6, 0.4, 0.4, 1.0), (0.125, 0.0, 0.8, 0.03)} <= trobats["k"], tipus
    assert len(list(tmp_path.glob("*-a5-cmyk.pdf"))) == 1  # la conversió es fa un sol cop


def test_sense_ghostscript_s_explica(monkeypatch):
    monkeypatch.setattr(cmyk, "ghostscript", lambda: None)
    with pytest.raises(cmyk.GhostscriptNoDisponible):
        cmyk.converteix(b"%PDF", {})
