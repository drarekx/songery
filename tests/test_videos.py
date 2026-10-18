"""Vídeos de YouTube a les cançons, codis QR i índex de QR (issue #9)."""
import pytest

from canconer import basedades as bd
from canconer import disseny, maquetacio, pdf, plantilles, videos
from canconer.web import crea_app

ID = "dQw4w9WgXcQ"


@pytest.mark.parametrize("url, inici", [
    (f"https://www.youtube.com/watch?v={ID}", 0),
    (f"https://youtube.com/watch?v={ID}&t=1m30s", 90),
    (f"youtu.be/{ID}?t=42", 42),
    (f"https://youtu.be/{ID}", 0),
    (f"https://www.youtube.com/shorts/{ID}", 0),
    (f"https://m.youtube.com/watch?feature=share&v={ID}", 0),
    (f"https://www.youtube.com/embed/{ID}?start=10", 10),
    (f"https://music.youtube.com/watch?v={ID}&list=x", 0),
])
def test_analitza_adreces(url, inici):
    assert videos.analitza(url) == {"video": ID, "inici": inici}


@pytest.mark.parametrize("url", ["", "hola", "https://vimeo.com/123", "https://youtube.com/watch?v=curt",
                                 "https://www.youtube.com/@canal", "https://evil.com/watch?v=" + ID])
def test_adreces_no_valides(url):
    with pytest.raises(videos.UrlInvalida):
        videos.analitza(url)


def test_url_curta_i_normalitzacio():
    assert videos.url_curta({"video": ID, "inici": 0}) == f"https://youtu.be/{ID}"
    assert videos.url_curta({"video": ID, "inici": 42}) == f"https://youtu.be/{ID}?t=42"
    net = videos.normalitza([{"video": ID, "titol": "x" * 300, "inici": "-5"}, {"video": "dolent"}, "res",
                             {"id": "a1", "video": ID}, {"id": "a1", "video": ID}])
    assert len(net) == 3 and len(net[0]["titol"]) == 200 and net[0]["inici"] == 0 and net[0]["inclou_qr"] is True
    assert net[1]["id"] == "a1" and net[2]["id"] != "a1"


def test_els_videos_es_desen_amb_el_contingut():
    c = disseny.contingut({"pagines": [{"elements": []}], "videos": [{"video": ID, "titol": "Vídeo"}]})
    assert c["videos"][0]["video"] == ID
    assert "videos" not in disseny.contingut({"pagines": [{"elements": []}]})
    e = disseny.element({"tipus": "qr", "video": "a1", "peu": False, "color": "nocolor"})
    assert (e["video"], e["peu"], e["color"]) == ("a1", False, "#1b1a17")


def _canco(i, n_videos, inclosa=True, marcats=True):
    contingut = {"format": 2, "pagines": [plantilles.pagina([])],
                 "videos": [{"id": f"v{i}{j}", "video": ID, "titol": f"Vídeo {i}.{j}", "inclou_qr": marcats}
                            for j in range(n_videos)]}
    return {"id": f"c{i}", "titol": f"Cançó {i}", "autor": "", "contingut": contingut, "tipus": "canco",
            "inici": "esquerra", "transport": 0, "inclosa": inclosa}


def _canconer(cancons, **extra):
    return plantilles.amb_valors_per_defecte({"titol": "Prova", "subtitol": "", "any": "", "contraportada": "",
                                              "pagina_acords": False, "posicio_acords": "inici",
                                              "instrument": "guitarra", "cancons": cancons, **extra})


def test_index_de_qr():
    cancons = [_canco(0, 4), _canco(1, 4), _canco(2, 3, inclosa=False), _canco(3, 2, marcats=False)]
    sense = maquetacio.pla(_canconer(cancons))
    assert not any(p["tipus"] == "index_qr" for p in sense["pagines"])

    pla = maquetacio.pla(_canconer(cancons, pagina_qr=True))
    qr = [p for p in pla["pagines"] if p["tipus"] == "index_qr"]
    assert len(qr) == 2 and pla["total"] % 4 == 0  # 8 vídeos marcats de cançons incloses, 6 per pàgina
    files = [f for p in qr for f in p["qrs"]]
    assert len(files) == 8 and {f["canco"] for f in files} == {"Cançó 0", "Cançó 1"}
    inici = {c["titol"]: c["pagina_inici"] for c in pla["cancons"]}
    assert all(f["pagina"] == inici[f["canco"]] for f in files)
    assert files[0]["url"] == f"https://youtu.be/{ID}"
    assert pla["pagines"][-1]["tipus"] == "contraportada" and pla["pagines"][-2]["tipus"] == "index_qr"

    al_principi = maquetacio.pla(_canconer(cancons, pagina_qr=True, posicio_qr="inici"))
    tipus = [p["tipus"] for p in al_principi["pagines"]]
    assert tipus[:4] == ["portada", "index", "index_qr", "index_qr"] and al_principi["total"] % 4 == 0
    # Els QR de les pàgines de cançó saben a quins vídeos apunten.
    pagina = next(p for p in al_principi["pagines"] if p["tipus"] == "canco")
    assert pagina["context"]["videos"][0] == {"id": "v00", "titol": "Vídeo 0.0", "url": f"https://youtu.be/{ID}"}


def test_l_opcio_canvia_la_memoria_cau():
    c = _canconer([_canco(0, 1)])
    assert pdf.empremta(c) != pdf.empremta({**c, "pagina_qr": True})


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(videos, "informacio", lambda v, **k: {"titol": "Never Gonna", "canal": "Rick"})
    app = crea_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_api_video(client):
    r = client.post("/api/video", json={"url": f"https://youtu.be/{ID}?t=5"})
    d = r.get_json()
    assert r.status_code == 200 and d["video"]["video"] == ID and d["video"]["inici"] == 5
    assert d["video"]["titol"] == "Never Gonna" and d["url"] == f"https://youtu.be/{ID}?t=5"
    r = client.post("/api/video", json={"url": "https://vimeo.com/1"})
    assert r.status_code == 400 and "YouTube" in r.get_json()["error"]


def test_sense_connexio_no_hi_ha_titol(monkeypatch):
    import requests

    def falla(*a, **k):
        raise requests.ConnectionError("sense xarxa")
    monkeypatch.setattr(videos.requests, "get", falla)
    assert videos.informacio({"video": ID}) == {}


def test_triar_l_index_de_qr(client):
    k = bd.crea_canconer("QR")
    client.post(f"/canconer/{k}/qr", data={"pagina_qr": "on", "posicio_qr": "inici"})
    assert (bd.meta_canconer(k)["pagina_qr"], bd.meta_canconer(k)["posicio_qr"]) == (True, "inici")
    client.post(f"/canconer/{k}/qr", data={})  # desactivar-lo no en perd la posició
    assert (bd.meta_canconer(k)["pagina_qr"], bd.meta_canconer(k)["posicio_qr"]) == (False, "inici")
    assert "Inclou l'índex de vídeos" in client.get(f"/canconer/{k}/imprimir").get_data(as_text=True)
