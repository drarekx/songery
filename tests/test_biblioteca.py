from canconer import basedades as bd
from canconer.web import crea_app

import pytest


@pytest.fixture
def client():
    app = crea_app()
    app.config["TESTING"] = True
    return app.test_client()


def _canco(titol, autor=""):
    id_canco = bd.crea_canco(titol, autor)
    return id_canco


def test_llista_inclou_cancons_soltes_i_ordena(client):
    a = _canco("Zebra", "Anna")
    b = _canco("abella", "Zoe")
    k = bd.crea_canconer("Llibret")
    bd.afegeix_entrada(k, a)
    files = {c["id"]: c for c in bd.biblioteca()}
    assert files[b]["canconers"] == [] and files[a]["canconers"] == [{"id": k, "titol": "Llibret"}]
    titols = [c["titol"] for c in bd.biblioteca(ordre="titol") if c["id"] in (a, b)]
    assert titols == ["abella", "Zebra"]
    autors = [c["autor"] for c in bd.biblioteca(ordre="autor") if c["id"] in (a, b)]
    assert autors == ["Anna", "Zoe"]
    assert bd.biblioteca(ordre="inexistent")  # cau a l'ordre per defecte
    html = client.get("/biblioteca?ordre=autor").get_data(as_text=True)
    assert "abella" in html and f"/biblioteca/{b}" in html


def test_versions_i_canvis_sense_versio():
    a = _canco("Una")
    assert bd.biblioteca("Una")[0]["n_versions"] == 0
    bd.crea_versio(a, "primera")
    fila = next(c for c in bd.biblioteca() if c["id"] == a)
    assert (fila["n_versions"], fila["modificat"]) == (1, False)
    bd.desa_esborrany(a, titol="Una (nova)")
    fila = next(c for c in bd.biblioteca() if c["id"] == a)
    assert fila["modificat"] is True


def test_fitxa_usos_nota_i_afegeix(client):
    a = _canco("Fitxa")
    v = bd.crea_versio(a, "")
    segueix = bd.crea_canconer("Segueix")
    fixat = bd.crea_canconer("Fixat")
    altre = bd.crea_canconer("Altre")
    bd.afegeix_entrada(segueix, a)
    bd.afegeix_entrada(fixat, a, versio_id=v["id"])
    usos = {u["titol"]: u for u in bd.usos_canco(a)}
    assert usos["Segueix"]["versio_id"] is None
    assert usos["Fixat"]["versio_numero"] == 1

    html = client.get(f"/biblioteca/{a}").get_data(as_text=True)
    assert "Segueix" in html and "fixada a Fixat" in html
    assert client.get("/biblioteca/noexisteix").status_code == 404

    r = client.put(f"/api/versio/{v['id']}/nota", json={"nota": "  per la trobada "})
    assert r.get_json()["nota"] == "per la trobada"
    assert bd.versions(a)[0]["nota"] == "per la trobada"

    r = client.post(f"/biblioteca/{a}/afegeix", data={"canconer": altre})
    assert r.status_code == 302 and f"/canconer/{altre}" in r.headers["Location"]
    assert any(u["id"] == altre and u["versio_id"] is None for u in bd.usos_canco(a))


def test_restaurar_afecta_nomes_els_que_segueixen_l_esborrany(client):
    a = _canco("Original")
    v1 = bd.crea_versio(a, "")
    segueix = bd.crea_canconer("Segueix")
    fixat = bd.crea_canconer("Fixat")
    bd.afegeix_entrada(segueix, a)
    bd.desa_esborrany(a, titol="Canviada")
    v2 = bd.crea_versio(a, "")
    bd.afegeix_entrada(fixat, a, versio_id=v2["id"])

    assert client.post(f"/api/canco/{a}/restaura", json={"versio_id": v1["id"]}).status_code == 200
    assert bd.carrega_canconer(segueix)["cancons"][0]["titol"] == "Original"
    assert bd.carrega_canconer(fixat)["cancons"][0]["titol"] == "Canviada"
