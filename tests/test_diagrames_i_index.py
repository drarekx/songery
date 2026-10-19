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
        acords = next(p for p in pla["pagines"] if p["tipus"].startswith("acords"))
        assert canco["context"]["diagrames"]["G"] == diagrames.svg("G", instrument)
        if instrument == "tots":  # a la pàgina d'acords, un bloc per a cada instrument
            assert acords["tipus"] == "acords_dos"
            assert all(diagrames.svg("G", i) in acords["diagrames_instrument"][i] for i in ("guitarra", "ukulele"))
        else:
            assert diagrames.svg("G", instrument) in acords["diagrames"]



def test_amb_els_dos_instruments_la_pagina_d_acords_te_un_bloc_per_instrument():
    """Amb guitarra i ukulele, la pàgina d'acords és la «acords_dos»: dos blocs (amb el seu títol), un per
    instrument, amb els mateixos acords a cada pàgina. Té el seu disseny, que es pot editar."""
    from canconer import diagrames, document, maquetacio, plantilles

    assert diagrames.instrument_valid("tots") == "tots" and diagrames.instrument_valid("violí") == "guitarra"
    disseny = plantilles.especials()["acords_dos"]["elements"]
    assert [e.get("text") for e in disseny if e["tipus"] == "text"] == ["Guitarra", "Ukulele"]
    assert [e.get("instrument") for e in disseny if e["tipus"] == "diagrames"] == ["guitarra", "ukulele"]

    acords = [f"{n}{q}" for n in "CDEFGAB" for q in ("", "m", "7")]  # 21 acords
    canco = {"id": "c", "titol": "T", "autor": "", "tipus": "canco", "inici": "esquerra", "transport": 0, "inclosa": True,
             "contingut": {"format": 2, "pagines": [plantilles.pagina_canco(document.de_text(" ".join(acords) + "\nla"))]}}
    base = plantilles.amb_valors_per_defecte({"titol": "P", "subtitol": "", "any": "", "contraportada": "", "pagina_acords": True,
                                               "posicio_acords": "inici", "cancons": [canco]})
    def pagines(instrument):
        return [p for p in maquetacio.pla({**base, "instrument": instrument})["pagines"] if p["tipus"].startswith("acords")]
    una, dues = pagines("guitarra"), pagines("tots")
    assert [p["tipus"] for p in una] == ["acords", "acords"]
    assert [p["tipus"] for p in dues] == ["acords_dos"] * 3  # 10 de cada instrument per pàgina
    primera = dues[0]["diagrames_instrument"]
    assert len(primera["guitarra"]) == len(primera["ukulele"]) == plantilles.DIAGRAMES_PER_INSTRUMENT
    assert primera["guitarra"][0] == diagrames.svg("C", "guitarra") and primera["ukulele"][0] == diagrames.svg("C", "ukulele")
    # Un bloc d'un sol instrument també pot triar-ne un altre.
    assert una[0]["diagrames_instrument"]["ukulele"][0] == diagrames.svg("C", "ukulele")


def test_el_disseny_accepta_l_instrument_dels_blocs_de_diagrames():
    from canconer import disseny

    e = disseny.element({"id": "d", "tipus": "diagrames", "x": 1, "y": 1, "w": 50, "h": 50, "instrument": "ukulele"})
    assert e["instrument"] == "ukulele"
    assert "instrument" not in disseny.element({"id": "d", "tipus": "diagrames", "x": 1, "y": 1, "w": 50, "h": 50, "instrument": "violí"})
