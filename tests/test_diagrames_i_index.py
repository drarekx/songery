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
    client.post(f"/canconer/{k}/opcions", data={"titol": "Sense índex"})  # l'índex es tria a Opcions
    assert bd.meta_canconer(k)["pagina_index"] is False
    assert "Índex de cançons: no" in client.get(f"/canconer/{k}/imprimir").get_data(as_text=True)


def test_l_instrument_de_la_impressio_canvia_tots_els_diagrames():
    """L'instrument del cançoner canvia la pàgina d'acords i també els diagrames de dins les cançons."""
    from canconer import diagrames, exemple, maquetacio

    k = exemple.crea_exemple()
    entrada = bd.carrega_canconer(k)["cancons"][0]
    contingut = bd.carrega_canco(entrada["id"])["contingut"]
    contingut["pagines"][0]["elements"].append({"id": "dg", "tipus": "diagrama", "acord": "G", "x": 10, "y": 150,
                                                "w": 18, "h": 23.7, "rotacio": 0, "opacitat": 1})
    bd.desa_esborrany(entrada["id"], contingut=contingut)
    bd.desa_meta(k, {"pagina_acords": True})
    for instrument in ("guitarra", "ukulele", "tots"):
        pla = maquetacio.pla({**bd.carrega_canconer(k), "instrument": instrument})
        canco = next(p for p in pla["pagines"] if p.get("entrada") == entrada["id"])
        acords = next(p for p in pla["pagines"] if p["tipus"] == "acords")
        assert canco["context"]["diagrames"]["G"] == diagrames.svg("G", instrument)
        assert diagrames.svg("G", instrument) in acords["diagrames"]



def test_amb_els_dos_instruments_cada_acord_porta_guitarra_i_ukulele():
    from canconer import diagrames, maquetacio, plantilles

    svg = diagrames.svg("Am", "tots")
    assert 'class="diagrama doble"' in svg and ">guitarra<" in svg and ">ukulele<" in svg
    assert svg.count(">Am<") == 1  # el nom de l'acord, un sol cop
    assert diagrames.instrument_valid("tots") == "tots" and diagrames.instrument_valid("violí") == "guitarra"
    # Són més amples: a la pàgina d'acords n'hi caben menys.
    acords = [f"{n}{q}" for n in "CDEFGAB" for q in ("", "m", "7")]
    canco = {"id": "c", "titol": "T", "autor": "", "tipus": "canco", "inici": "esquerra", "transport": 0, "inclosa": True,
             "contingut": {"format": 2, "pagines": [plantilles.pagina_canco(__import__("canconer.document", fromlist=["x"]).de_text(" ".join(acords) + "\nla"))]}}
    base = plantilles.amb_valors_per_defecte({"titol": "P", "subtitol": "", "any": "", "contraportada": "", "pagina_acords": True,
                                               "posicio_acords": "inici", "cancons": [canco]})
    def pagines_acords(instrument):
        return [p for p in maquetacio.pla({**base, "instrument": instrument})["pagines"] if p["tipus"] == "acords"]
    una, dues = pagines_acords("guitarra"), pagines_acords("tots")
    assert len(una) == 2 and len(dues) == 2
    assert len(dues[0]["diagrames"]) == plantilles.DIAGRAMES_DOBLES_PER_PAGINA
