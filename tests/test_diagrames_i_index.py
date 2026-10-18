"""Diagrames d'acords a les pàgines i índex opcional."""
import pytest

from canconer import basedades as bd
from canconer import disseny, maquetacio, plantilles
from canconer.document import de_text
from canconer.web import crea_app


def _canconer(transport=0, **extra):
    pagina = plantilles.pagina_canco(de_text("G   D/F#  Em\nlletra de prova"))
    pagina["elements"].append({"id": "d1", "tipus": "diagrama", "acord": "C", "x": 10, "y": 10, "w": 18, "h": 23.7})
    pagina["elements"].append({"id": "d2", "tipus": "diagrames", "canco": True, "mida": 14, "x": 10, "y": 40, "w": 120, "h": 26})
    canco = {"id": "c1", "titol": "Prova", "autor": "", "tipus": "canco", "inici": "esquerra", "transport": transport,
             "inclosa": True, "contingut": {"format": 2, "pagines": [pagina]}}
    return plantilles.amb_valors_per_defecte({"titol": "K", "subtitol": "", "any": "", "contraportada": "",
                                              "pagina_acords": False, "instrument": "guitarra",
                                              "cancons": [canco], **extra})


def _pagina_canco(pla):
    return next(p for p in pla["pagines"] if p["tipus"] == "canco")


def test_la_pagina_porta_els_diagrames_de_la_canco():
    p = _pagina_canco(maquetacio.pla(_canconer()))
    assert p["context"]["ordreAcords"] == ["G", "D", "Em"]  # sense el baix (D/F# → D) i en ordre
    assert set(p["context"]["diagrames"]) == {"G", "D", "Em", "C"}  # també el de l'element solt
    assert "<svg" in p["context"]["diagrames"]["C"]


def test_els_diagrames_es_transporten_amb_la_canco():
    p = _pagina_canco(maquetacio.pla(_canconer(transport=2)))
    assert p["context"]["ordreAcords"] == ["A", "E", "F#m"]
    assert next(e for e in p["elements"] if e["id"] == "d1")["acord"] == "D"


def test_validacio_dels_elements():
    e = disseny.element({"tipus": "diagrama", "acord": "Am7" * 10})
    assert e["acord"] == ("Am7" * 10)[:16]
    tots = disseny.element({"tipus": "diagrames", "canco": True, "mida": 200})
    assert tots["canco"] is True and tots["mida"] == 60
    assert "canco" not in disseny.element({"tipus": "diagrames"})


def test_index_opcional():
    amb = maquetacio.pla(_canconer())
    sense = maquetacio.pla(_canconer(pagina_index=False))
    assert "index" in [p["tipus"] for p in amb["pagines"]]
    assert "index" not in [p["tipus"] for p in sense["pagines"]]
    assert sense["total"] % 4 == 0


@pytest.fixture
def client():
    app = crea_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_web(client):
    svgs = client.post("/api/diagrames", json={"acords": ["G", "D/F#"], "instrument": "ukulele"}).get_json()
    assert set(svgs) == {"G", "D/F#"} and "<svg" in svgs["G"]
    k = bd.crea_canconer("Sense índex")
    assert bd.meta_canconer(k)["pagina_index"] is True
    client.post(f"/canconer/{k}/index", data={})
    assert bd.meta_canconer(k)["pagina_index"] is False
    assert "índex de cançons" in client.get(f"/canconer/{k}/imprimir").get_data(as_text=True)
