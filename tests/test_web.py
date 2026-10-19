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
    assert [e.get("text") for e in r["especials"]["portada"]["elements"]] == ["{titol}"]  # la per defecte: només el títol


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


def test_sense_navegador_dona_un_error_clar(client, canconer, monkeypatch):
    from canconer import motor_pdf
    monkeypatch.setattr(pdf, "GOTENBERG", "")
    monkeypatch.setattr(motor_pdf, "troba_navegador", lambda: None)

    def sense_xarxa():
        raise motor_pdf.MotorNoDisponible("No hi ha cap navegador Chrome o Edge.")
    monkeypatch.setattr(motor_pdf, "descarrega_motor", sense_xarxa)
    r = client.get(f"/canconer/{canconer}/pdf/a5")
    assert r.status_code == 503 and "Chrome" in r.get_data(as_text=True)


def _gotenberg_actiu() -> bool:
    try:
        return requests.get("http://127.0.0.1:3000/health", timeout=2).ok
    except requests.RequestException:
        return False


def _navegador_local() -> bool:
    from canconer import motor_pdf
    return bool(motor_pdf.troba_navegador())


@pytest.mark.parametrize("motor", [
    pytest.param("local", marks=pytest.mark.skipif(not _navegador_local(), reason="No hi ha cap Chrome/Edge instal·lat")),
    pytest.param("gotenberg", marks=pytest.mark.skipif(not _gotenberg_actiu(), reason="Gotenberg no està en marxa")),
])
def test_acceptacio_pdf(motor, monkeypatch):
    """4 cançons de 2 pàgines → PDF A5 de 12 pàgines i A4 de 6 cares en l'ordre de cavallet."""
    monkeypatch.setattr(pdf, "GOTENBERG", "http://127.0.0.1:3000" if motor == "gotenberg" else "")
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


def _canconer_amb_acords(client):
    id_canconer = client.post("/canconer/nou", data={"titol": "Acords"}).headers["Location"].rsplit("/", 1)[-1]
    client.post(f"/canconer/{id_canconer}/opcions", data={"titol": "Acords", "pagina_acords": "on", "instrument": "guitarra"})
    client.post(f"/api/canconer/{id_canconer}/canco", json={"titol": "C", "text": "C   G   Am\nhola"})
    return id_canconer


def test_instrument_a_l_hora_d_imprimir(client):
    """#1: l'instrument es tria a Imprimir i no canvia el cançoner desat."""
    import re
    from canconer import maquetacio
    id_canconer = _canconer_amb_acords(client)
    html = client.get(f"/canconer/{id_canconer}/imprimir?instrument=ukulele").get_data(as_text=True)
    assert re.search(r'instrument=ukulele"[^>]*\n?[^>]*aria-pressed="true"', html)
    assert "instrument=ukulele" in html
    assert bd.meta_canconer(id_canconer)["instrument"] == "guitarra"  # no s'ha desat res

    c = bd.carrega_canconer(id_canconer)
    def cordes(instrument):
        pla = maquetacio.pla({**c, "instrument": instrument})
        svg = next(p for p in pla["pagines"] if p["tipus"] == "acords")["diagrames"][0]
        return len([m for m in re.finditer(r'<line x1="([\d.]+)" y1="[\d.]+" x2="([\d.]+)"', svg) if m[1] == m[2]])
    assert (cordes("guitarra"), cordes("ukulele")) == (6, 4)
    assert pdf.empremta({**c, "instrument": "guitarra"}) != pdf.empremta({**c, "instrument": "ukulele"})


@pytest.mark.skipif(not _navegador_local(), reason="No hi ha cap Chrome/Edge instal·lat")
def test_pdf_per_instrument(monkeypatch):
    """#1: cada instrument genera el seu PDF (sense barrejar la memòria cau) i el nom ho indica."""
    monkeypatch.setattr(pdf, "GOTENBERG", "")
    app = crea_app()
    servidor = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    try:
        client = app.test_client()
        id_canconer = _canconer_amb_acords(client)
        base = f"http://127.0.0.1:{servidor.server_port}/canconer/{id_canconer}/pdf/a5"
        guitarra = requests.get(f"{base}?instrument=guitarra", timeout=120)
        ukulele = requests.get(f"{base}?instrument=ukulele&baixa=1", timeout=120)
        assert guitarra.content != ukulele.content
        assert "ukulele.pdf" in ukulele.headers["Content-Disposition"]
    finally:
        servidor.shutdown()


def test_els_errors_es_desen_i_s_expliquen(client, monkeypatch, dades_temporals):
    def falla(*a, **k):
        raise RuntimeError("base de dades trencada")
    monkeypatch.setattr(bd, "llista_canconers", falla)
    client.application.config["TESTING"] = False  # que l'error arribi al gestor com a l'app real
    r = client.get("/")
    assert r.status_code == 500 and "base de dades trencada" in r.get_data(as_text=True)
    assert "RuntimeError: base de dades trencada" in (dades_temporals / "errors.log").read_text()


def test_pagina_lliure_abans_d_una_entrada_omple_la_pagina_en_blanc():
    """La pàgina 3 (en blanc, perquè la primera cançó comenci a l'esquerra) es pot omplir amb una
    pàgina lliure posada davant de la primera cançó."""
    from canconer import basedades as bd, exemple, maquetacio
    from canconer.web import crea_app

    k = exemple.crea_exemple()
    tipus = [p["tipus"] for p in maquetacio.pla(bd.carrega_canconer(k))["pagines"]]
    assert tipus[:4] == ["portada", "index", "blanc", "canco"]
    primera = bd.carrega_canconer(k)["cancons"][0]["id"]
    client = crea_app().test_client()
    r = client.post(f"/api/canconer/{k}/canco", json={"tipus": "pagina", "abans_de": primera})
    pla = maquetacio.pla(bd.carrega_canconer(k))["pagines"]
    assert [p["tipus"] for p in pla[:4]] == ["portada", "index", "lliure", "canco"]
    assert pla[2]["entrada"] == r.get_json()["id"] and pla[3]["numero"] == 4


def test_l_index_de_qr_torna_a_imprimir():
    """L'índex de QR es tria a Imprimir i hi torna (amb l'instrument triat)."""
    from canconer import basedades as bd
    from canconer.web import crea_app

    k = bd.crea_canconer("Prova")
    client = crea_app().test_client()
    r = client.post(f"/canconer/{k}/qr", data={"pagina_qr": "on", "posicio_qr": "final", "instrument": "ukulele"})
    assert f"/canconer/{k}/imprimir" in r.headers["Location"] and "instrument=ukulele" in r.headers["Location"]


def test_l_index_es_tria_a_opcions():
    from canconer import basedades as bd
    from canconer.web import crea_app

    k = bd.crea_canconer("Prova")
    client = crea_app().test_client()
    assert 'name="pagina_index" checked' in client.get(f"/canconer/{k}/opcions").get_data(as_text=True)
    client.post(f"/canconer/{k}/opcions", data={"titol": "Prova"})  # interruptor desmarcat
    assert bd.meta_canconer(k)["pagina_index"] is False
    assert "Índex de cançons: no" in client.get(f"/canconer/{k}/imprimir").get_data(as_text=True)
    client.post(f"/canconer/{k}/opcions", data={"titol": "Prova", "pagina_index": "on"})
    assert bd.meta_canconer(k)["pagina_index"] is True


def test_desactivar_l_index_no_n_esborra_el_disseny():
    """Desactivar l'índex l'amaga del llibret; tornar-lo a activar el fa sortir amb el disseny que tenia."""
    from canconer import basedades as bd, exemple, maquetacio
    from canconer.web import crea_app

    k = exemple.crea_exemple()
    especials = bd.meta_canconer(k)["especials"]
    especials["index"]["elements"].append({"id": "meu", "tipus": "text", "text": "Retoc a mà", "x": 10, "y": 10,
                                           "w": 50, "h": 8, "estil": "text", "rotacio": 0, "opacitat": 1})
    bd.desa_meta(k, {"especials": especials})
    client = crea_app().test_client()
    client.post(f"/canconer/{k}/opcions", data={"titol": "Cançoner d'exemple"})  # sense índex
    assert "index" not in [p["tipus"] for p in maquetacio.pla(bd.carrega_canconer(k))["pagines"]]
    client.post(f"/canconer/{k}/opcions", data={"titol": "Cançoner d'exemple", "pagina_index": "on"})
    index = next(p for p in maquetacio.pla(bd.carrega_canconer(k))["pagines"] if p["tipus"] == "index")
    assert any(e.get("id") == "meu" for e in index["elements"])


def test_descarta_nomes_pagines_lliures_buides():
    from canconer import basedades as bd, exemple, plantilles
    from canconer.web import crea_app

    k = exemple.crea_exemple()
    client = crea_app().test_client()
    primera = bd.carrega_canconer(k)["cancons"][0]["id"]
    buida = client.post(f"/api/canconer/{k}/canco", json={"tipus": "pagina", "abans_de": primera}).get_json()["id"]
    plena = client.post(f"/api/canconer/{k}/canco", json={"tipus": "pagina"}).get_json()["id"]
    contingut = {"format": 2, "pagines": [plantilles.pagina([{"id": "t", "tipus": "text", "text": "Hola", "x": 1, "y": 1,
                                                               "w": 20, "h": 5, "rotacio": 0, "opacitat": 1}])]}
    bd.desa_esborrany(plena, contingut=contingut)
    descarta = lambda id_: client.post(f"/api/canconer/{k}/entrada/{id_}/descarta-buida").get_json()["esborrada"]
    assert descarta(plena) is False and descarta(primera) is False  # té contingut / és una cançó
    altre = bd.crea_canconer("Altre")
    bd.afegeix_entrada(altre, buida)
    assert descarta(buida) is False  # també és en un altre cançoner
    bd.treu_entrada(altre, buida)
    assert descarta(buida) is True
    assert buida not in [c["id"] for c in bd.carrega_canconer(k)["cancons"]]
    try:
        bd.carrega_canco(buida)
        raise AssertionError("no s'ha esborrat")
    except KeyError:
        pass


def test_portada_per_defecte_nomes_amb_el_titol():
    """Issue #10: un cançoner nou porta només el títol a la portada; els existents i l'exemple no canvien."""
    import json as json_
    from canconer import basedades as bd, exemple, plantilles

    nou = bd.carrega_canconer(bd.crea_canconer("Nou"))
    assert [e.get("text") for e in nou["especials"]["portada"]["elements"]] == ["{titol}"]
    assert len(bd.carrega_canconer(exemple.crea_exemple())["especials"]["portada"]["elements"]) == 4
    # Migració: un cançoner antic que agafava la portada per defecte es queda la completa; un amb la
    # portada retocada no es toca.
    antic, retocat = bd.crea_canconer("Antic"), bd.crea_canconer("Retocat")
    propia = plantilles.pagina([{"id": "x", "tipus": "text", "text": "Meva", "x": 1, "y": 1, "w": 9, "h": 9}], mestra=None)
    bd.desa_meta(retocat, {"especials": {"portada": propia}})
    with bd.connexio() as con:
        bd._fixa_portades(con)
    assert len(bd.carrega_canconer(antic)["especials"]["portada"]["elements"]) == 4
    assert bd.carrega_canconer(retocat)["especials"]["portada"]["elements"][0]["text"] == "Meva"
    with bd.connexio() as con:
        dades = json_.loads(con.execute("SELECT dades FROM canconer WHERE id = ?", (antic,)).fetchone()["dades"])
    sense_ids = lambda pagina: [{k: v for k, v in e.items() if k != "id"} for e in pagina["elements"]]
    assert sense_ids(dades["especials"]["portada"]) == sense_ids(plantilles.portada_completa())
