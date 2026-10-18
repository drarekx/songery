import io
import threading

import pytest
import requests
from pypdf import PdfReader
from werkzeug.serving import make_server

from canconer import basedades as bd
from canconer import document, exemple, pdf, plantilles
from canconer.web import crea_app


@pytest.fixture
def client():
    app = crea_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def canconer(client):
    resposta = client.post("/canconer/nou", data={"titol": "Prova"})
    return resposta.headers["Location"].rsplit("/", 1)[-1]


def test_pagines_principals(client, canconer):
    assert client.get("/").status_code == 200
    assert client.get("/biblioteca").status_code == 200
    for ruta in ("", "/opcions", "/imprimir", "/imprimible", "/instruccions"):
        assert client.get(f"/canconer/{canconer}{ruta}").status_code == 200, ruta
    assert client.get(f"/canconer/{canconer}/portada").status_code == 302
    assert client.get("/canconer/noexisteix").status_code == 404


def test_cancons_versions_i_importacio(client, canconer):
    a = client.post(f"/api/canconer/{canconer}/canco", json={}).get_json()["id"]
    contingut = client.get(f"/api/canco/{a}").get_json()["contingut"]
    contingut["pagines"][0]["elements"][-1]["doc"] = document.de_text("C   G\nhola que tal")
    assert client.put(f"/api/canco/{a}", json={"titol": "Primera", "contingut": contingut}).status_code == 200
    assert client.put(f"/api/canco/{a}", json={"contingut": {"pagines": []}}).status_code == 400
    v = client.post(f"/api/canco/{a}/versions", json={"nota": "trobada"}).get_json()["versio"]
    assert client.get(f"/api/versio/{v['id']}").get_json()["nota"] == "trobada"

    altre = bd.crea_canconer("Altre")
    assert client.post(f"/api/canconer/{altre}/importa", json={"cancons": [a]}).status_code == 200
    assert client.get(f"/api/canconer/{altre}").get_json()["cancons"][0]["versio_numero"] == 1

    client.patch(f"/api/canconer/{canconer}/entrada/{a}", json={"inclosa": False, "transport": 2, "inici": "qualsevol"})
    entrada = client.get(f"/api/canconer/{canconer}").get_json()["cancons"][0]
    assert (entrada["inclosa"], entrada["transport"], entrada["inici"]) == (False, 2, "qualsevol")
    assert client.get(f"/api/canconer/{canconer}/pla").get_json()["cancons"] == []
    assert client.delete(f"/api/canconer/{canconer}/entrada/{a}").status_code == 200


def test_pagina_lliure(client, canconer):
    p = client.post(f"/api/canconer/{canconer}/canco", json={"tipus": "pagina"}).get_json()["id"]
    entrada = client.get(f"/api/canconer/{canconer}").get_json()["cancons"][0]
    assert entrada["id"] == p and entrada["tipus"] == "pagina" and entrada["inici"] == "qualsevol"


def test_disseny_estils_mestres_i_especials(client, canconer):
    r = client.put(f"/api/canconer/{canconer}/disseny", json={"estils": {"lletra": {"mida": 13}}}).get_json()
    assert r["estils"]["lletra"]["mida"] == 13
    assert client.put(f"/api/canconer/{canconer}/disseny", json={"mestres": []}).status_code == 400
    portada = plantilles.pagina([{"tipus": "forma", "x": 0, "y": 0, "w": 148, "h": 210, "fons": "#000000"}], mestra=None)
    r = client.put(f"/api/canconer/{canconer}/disseny", json={"especials": {"portada": portada}}).get_json()
    assert r["especials"]["portada"]["elements"][0]["fons"] == "#000000"
    r = client.put(f"/api/canconer/{canconer}/disseny", json={"restableix": "portada"}).get_json()
    assert len(r["especials"]["portada"]["elements"]) == 4


def test_elements_i_imatges(client):
    r = client.post("/api/elements", json={"nom": "Sanefa", "elements": [{"tipus": "forma", "x": 0, "y": 0, "w": 9, "h": 9}]})
    assert r.status_code == 200
    assert client.get("/api/elements").get_json()["elements"][0]["nom"] == "Sanefa"
    assert client.post("/api/elements", json={"elements": []}).status_code == 400
    r = client.post("/api/imatges", data={"imatge": (io.BytesIO(b"\x89PNG"), "a.png", "image/png")})
    assert client.get(f"/imatges/{r.get_json()['id']}").data == b"\x89PNG"


def test_converteix_i_transporta(client):
    doc = client.post("/api/converteix", json={"text": "G\nhola"}).get_json()["doc"]
    contingut = {"pagines": [plantilles.pagina_canco(doc)]}
    nou = client.post("/api/transporta", json={"contingut": contingut, "semitons": 2}).get_json()["contingut"]
    assert document.acords(nou["pagines"][0]["elements"][-1]["doc"]) == ["A"]


def test_sense_gotenberg_dona_un_error_clar(client, canconer, monkeypatch):
    monkeypatch.setattr(pdf, "GOTENBERG", "http://127.0.0.1:9")
    r = client.get(f"/canconer/{canconer}/pdf/a5")
    assert r.status_code == 503 and "docker compose up" in r.get_data(as_text=True)


def _gotenberg_actiu() -> bool:
    try:
        return requests.get(f"{pdf.GOTENBERG}/health", timeout=2).ok
    except requests.RequestException:
        return False


@pytest.mark.skipif(not _gotenberg_actiu(), reason="Gotenberg no està en marxa (docker compose up -d)")
def test_acceptacio_pdf_amb_gotenberg():
    """4 cançons de 2 pàgines → PDF A5 de 12 pàgines i A4 de 6 cares en l'ordre de cavallet."""
    app = crea_app()
    servidor = make_server("0.0.0.0", 0, app, threaded=True)
    fil = threading.Thread(target=servidor.serve_forever, daemon=True)
    fil.start()
    try:
        id_canconer = exemple.crea_exemple()
        for c in bd.carrega_canconer(id_canconer)["cancons"]:
            contingut = bd.carrega_canco(c["id"])["contingut"]
            if len(contingut["pagines"]) == 1:  # assegura 2 pàgines per cançó
                contingut["pagines"].append(plantilles.pagina_canco(document.buit(), amb_capcalera=False))
                bd.desa_esborrany(c["id"], contingut=contingut)
        base = f"http://127.0.0.1:{servidor.server_port}/canconer/{id_canconer}"
        a5 = PdfReader(io.BytesIO(requests.get(f"{base}/pdf/a5", timeout=120).content))
        assert len(a5.pages) == 12
        assert round(float(a5.pages[0].mediabox.width)) == 420  # 148 mm
        assert "Cançoner d'exemple" in a5.pages[0].extract_text()
        assert "Camí de muntanya" in a5.pages[3].extract_text()
        a4 = PdfReader(io.BytesIO(requests.get(f"{base}/pdf/a4", timeout=120).content))
        assert len(a4.pages) == 6
        assert "Cançoner d'exemple" in a4.pages[0].extract_text()  # cara 1: 12 | 1
    finally:
        servidor.shutdown()


def test_crea_canco_a_partir_de_text_amb_acords(client, canconer):
    text = "[Verse 1]\nG          D/F#\nCamino pel sender de"
    id_canco = client.post(f"/api/canconer/{canconer}/canco", json={"titol": "Camí", "autor": "Jo", "text": text}).get_json()["id"]
    canco = client.get(f"/api/canco/{id_canco}").get_json()
    assert (canco["titol"], canco["autor"]) == ("Camí", "Jo")
    marc = next(e for e in canco["contingut"]["pagines"][0]["elements"] if e["tipus"] == "lletra")
    assert document.acords(marc["doc"]) == ["G", "D/F#"]


def test_tipografies_cataleg_i_importades(client):
    fonts = client.get("/api/fonts").get_json()["fonts"]
    claus = {f["clau"] for f in fonts}
    assert {"display", "sans", "mono", "lora", "pacifico"} <= claus and len(fonts) >= 50
    css = client.get("/fonts.css").get_data(as_text=True)
    assert '@font-face{font-family:"Lora"' in css

    from pathlib import Path
    woff2 = next((Path(__file__).parent.parent / "canconer/static/fonts/cataleg").glob("lora-*.woff2")).read_bytes()
    r = client.post("/api/fonts", data={"font": (io.BytesIO(woff2), "MevaLletra-BoldItalic.woff2"), "nom": "Meva Lletra", "pes": "700", "estil": "italic"})
    assert r.status_code == 200 and r.get_json()["clau"] == "u-meva-lletra"
    importades = client.get("/api/fonts").get_json()
    assert any(f["clau"] == "u-meva-lletra" and f["categoria"] == "importada" for f in importades["fonts"])
    id_font = importades["importades"][0]["id"]
    assert client.get(f"/tipografies/{id_font}").data == woff2
    assert '"Meva Lletra (importada)";font-style:italic;font-weight:700' in client.get("/fonts.css").get_data(as_text=True)

    dolent = client.post("/api/fonts", data={"font": (io.BytesIO(b"<html>no</html>"), "virus.ttf")})
    assert dolent.status_code == 415
    assert client.delete(f"/api/fonts/{id_font}").status_code == 200
    assert client.get("/api/fonts").get_json()["importades"] == []
