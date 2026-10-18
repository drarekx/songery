"""Mestres de marges per a l'enquadernació (issue #7)."""
import re
from io import BytesIO

import pytest
from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from canconer import basedades as bd
from canconer import imposicio, marges, pdf
from canconer.web import crea_app


def _pdf_a5(n=4) -> bytes:
    escriptor = PdfWriter()
    for _ in range(n):
        pagina = PageObject.create_blank_page(width=imposicio.A5_AMPLE, height=imposicio.A5_ALT)
        contingut = DecodedStreamObject()
        contingut.set_data(b"0 0 419.53 595.28 re f")
        pagina[NameObject("/Contents")] = contingut
        escriptor.add_page(pagina)
    sortida = BytesIO()
    escriptor.write(sortida)
    return sortida.getvalue()


def _desplacament(pagina) -> tuple[float, float, float]:
    """Escala i desplaçament (x, y) de la primera transformació «cm» del contingut."""
    a, _b, _c, _d, e, f = map(float, re.search(rb"([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) cm",
                                                 pagina.get_contents().get_data()).groups())
    return a, e, f


def _marge(**camps):
    return marges.normalitza({**marges.PREDEFINIDES[0], **camps}, "prova")


def test_sense_marges_no_toca_el_pdf():
    original = _pdf_a5()
    assert marges.aplica(original, marges.normalitza(marges.PREDEFINIDES[0])) is original
    assert not marges.actiu(_marge())


def test_el_marge_interior_queda_sempre_al_plec():
    m = _marge(interior=10)
    lector = PdfReader(BytesIO(marges.aplica(_pdf_a5(), m)))
    assert len(lector.pages) == 4
    s = marges.escala(m)
    for i, pagina in enumerate(lector.pages):
        assert float(pagina.mediabox.width) == pytest.approx(imposicio.A5_AMPLE, abs=0.01)
        escala, x, _y = _desplacament(pagina)
        assert escala == pytest.approx(s, abs=1e-3)
        dreta = x + imposicio.A5_AMPLE * s
        if (i + 1) % 2 == 0:  # esquerra: el plec és a la dreta
            assert imposicio.A5_AMPLE - dreta == pytest.approx(10 * marges.PT_MM, abs=0.1)
        else:  # dreta: el plec és a l'esquerra
            assert x == pytest.approx(10 * marges.PT_MM, abs=0.1)


def test_forats_i_validacio():
    m = _marge(interior=14, forats=2, separacio=80)
    assert marges.posicions_forats(m) == [65, 145]
    dades = PdfReader(BytesIO(marges.aplica(_pdf_a5(2), m))).pages[0].get_contents().get_data()
    assert dades.count(b"c\nS") == 2
    net = marges.normalitza({"interior": "-3", "exterior": "99", "superior": "2,5", "forats": "9", "nom": ""})
    assert (net["interior"], net["exterior"], net["superior"], net["forats"], net["nom"]) == (0, 40, 2.5, 4, "Marges")


def test_la_cau_distingeix_les_mestres(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf, "genera_a5", lambda *a, **k: _pdf_a5())
    monkeypatch.setattr(pdf, "_directori_cau", lambda: tmp_path)
    c = {"titol": "Prova", "marge": _marge()}
    assert pdf.clau(c) == pdf.empremta(c)
    sense = pdf.genera(c, "a4", "")
    cosit = {**c, "marge": _marge(interior=4)}
    encolat = {**c, "marge": _marge(interior=9)}
    assert pdf.empremta(cosit) == pdf.empremta(c)  # el dibuix de les pàgines no canvia
    assert len({pdf.clau(c), pdf.clau(cosit), pdf.clau(encolat)}) == 3
    a4_cosit, a4_encolat = pdf.genera(cosit, "a4", ""), pdf.genera(encolat, "a4", "")
    assert len({sense, a4_cosit, a4_encolat}) == 3
    assert pdf.genera(c, "a4", "") == sense
    assert sense == imposicio.imposa(_pdf_a5())


@pytest.fixture
def client():
    app = crea_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_gestio_de_mestres_de_marges(client):
    ids = [m["id"] for m in bd.llista_marges()]
    assert ids[:1] == ["cap"] and {"cosit", "encolat", "anelles"} <= set(ids)
    assert client.get("/marges").status_code == 200
    client.post("/marges", data={"nom": "Espiral"})
    nova = next(m for m in bd.llista_marges() if m["nom"] == "Espiral")
    client.post(f"/marges/{nova['id']}", data={"nom": "Espiral", "interior": "12", "forats": "3"})
    assert (bd.carrega_marge(nova["id"])["interior"], bd.carrega_marge(nova["id"])["forats"]) == (12, 3)
    assert client.post("/marges/cap", data={"interior": "5"}).status_code == 400
    assert client.post("/marges/cap", data={"accio": "esborra"}).status_code == 400
    client.post(f"/marges/{nova['id']}", data={"accio": "esborra"})
    assert nova["id"] not in [m["id"] for m in bd.llista_marges()]
    # Una mestra que ja no existeix es llegeix com «Sense marges».
    assert bd.carrega_marge(nova["id"])["id"] == "cap"


def test_triar_marges_a_imprimir(client):
    k = bd.crea_canconer("Enquadernat")
    assert "Sense marges" in client.get(f"/canconer/{k}/imprimir").get_data(as_text=True)
    r = client.post(f"/canconer/{k}/marges", data={"marges": "encolat", "instrument": "ukulele"})
    assert r.status_code == 302 and "instrument=ukulele" in r.headers["Location"]
    assert bd.meta_canconer(k)["marges"] == "encolat"
    html = client.get(f"/canconer/{k}/imprimir").get_data(as_text=True)
    assert "9 mm al plec" in html and "-m" in html  # la v dels PDF porta la mestra
    assert '"marge": {' in client.get(f"/canconer/{k}").get_data(as_text=True)
    client.post(f"/canconer/{k}/marges", data={"marges": "noexisteix"})
    assert bd.meta_canconer(k)["marges"] == "cap"
