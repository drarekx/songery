"""Mèdia: imatges compartides per totes les cançons i cançoners, en carpetes. Només es poden pujar
PNG, JPEG, WEBP i GIF (mirant el contingut), i moure una imatge de carpeta no canvia cap cançó."""

import io

import pytest

from canconer import basedades as bd
from canconer import plantilles
from canconer.web import crea_app

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 40
JPEG = b"\xff\xd8\xff\xe0" + b"\0" * 40
GIF = b"GIF89a" + b"\0" * 40
WEBP = b"RIFF\0\0\0\0WEBPVP8 " + b"\0" * 40


@pytest.fixture
def client():
    app = crea_app()
    app.config["TESTING"] = True
    return app.test_client()


def puja(client, dades, nom, carpeta=None):
    form = {"imatge": (io.BytesIO(dades), nom)}
    if carpeta:
        form["carpeta"] = carpeta
    return client.post("/api/imatges", data=form, content_type="multipart/form-data")


def test_nomes_es_poden_pujar_imatges_estandard(client):
    for dades, nom in ((PNG, "a.png"), (JPEG, "b.jpg"), (JPEG, "c.JPEG"), (GIF, "d.gif"), (WEBP, "e.webp"), (PNG, "image.png")):
        assert puja(client, dades, nom).status_code == 200, nom
    # Un SVG, un fitxer que no és imatge o una imatge amb una extensió estranya: no.
    for dades, nom in ((b"<svg xmlns='http://www.w3.org/2000/svg'/>", "x.svg"), (b"%PDF-1.7", "x.png"),
                       (PNG, "x.exe"), (PNG, "x.svg"), (b"hola", "x.txt")):
        r = puja(client, dades, nom)
        assert r.status_code == 415 and "PNG, JPG, WEBP o GIF" in r.get_json()["error"], nom
    assert bd.media()["total"] == 6


def test_carpetes_moure_reanomenar_i_esborrar(client):
    ocells = client.post("/api/media/carpetes", json={"nom": "Ocells"}).get_json()["id"]
    a = puja(client, PNG, "oreneta.png", ocells).get_json()["id"]
    b = puja(client, JPEG, "pit-roig.jpg").get_json()["id"]
    m = client.get("/api/media").get_json()
    assert m["total"] == 2 and m["sense_carpeta"] == 1 and m["carpetes"] == [{"id": ocells, "nom": "Ocells", "n": 1}]
    assert [i["nom"] for i in client.get(f"/api/media?carpeta={ocells}").get_json()["imatges"]] == ["oreneta.png"]
    assert [i["id"] for i in client.get("/api/media?carpeta=").get_json()["imatges"]] == [b]
    assert [i["id"] for i in client.get("/api/media?q=pit").get_json()["imatges"]] == [b]

    assert client.put("/api/media/imatges", json={"ids": [b], "carpeta": ocells}).get_json()["mogudes"] == 1
    assert client.get("/api/media").get_json()["carpetes"][0]["n"] == 2
    assert client.put(f"/api/media/imatges/{a}", json={"nom": "oreneta en vol"}).status_code == 200
    assert client.put(f"/api/media/carpetes/{ocells}", json={"nom": "Aus"}).status_code == 200
    assert client.get("/api/media").get_json()["carpetes"][0]["nom"] == "Aus"
    # Esborrar la carpeta no esborra cap imatge: passen a «Sense carpeta».
    assert client.delete(f"/api/media/carpetes/{ocells}").status_code == 200
    m = client.get("/api/media").get_json()
    assert m["carpetes"] == [] and m["sense_carpeta"] == 2
    assert client.put("/api/media/imatges", json={"ids": [a], "carpeta": "noexisteix"}).status_code == 404


def test_moure_no_canvia_les_cancons_i_no_s_esborra_si_es_fa_servir(client):
    carpeta = bd.crea_carpeta_media("Portades")
    id_imatge = puja(client, PNG, "foto.png").get_json()["id"]
    contingut = {"format": 2, "pagines": [plantilles.pagina([{"id": "e", "tipus": "imatge", "src": id_imatge,
                                                              "x": 0, "y": 0, "w": 10, "h": 10}])]}
    id_canco = bd.crea_canco("La meva cançó", "", contingut)
    abans = bd.carrega_canco(id_canco)["contingut"]
    bd.mou_imatges([id_imatge], carpeta)
    assert bd.carrega_canco(id_canco)["contingut"] == abans
    assert client.get(f"/imatges/{id_imatge}").status_code == 200

    usos = client.get("/api/media").get_json()["imatges"][0]["usos"]
    assert usos == ["cançó «La meva cançó»"]
    r = client.delete(f"/api/media/imatges/{id_imatge}")
    assert r.status_code == 409 and r.get_json()["usos"] == usos
    sola = puja(client, PNG, "sola.png").get_json()["id"]
    assert client.delete(f"/api/media/imatges/{sola}").status_code == 200
    assert client.get(f"/imatges/{sola}").status_code == 404
