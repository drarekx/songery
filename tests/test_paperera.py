"""Paperera de cançoners: s'hi envien, es recuperen i s'esborren per sempre en buidar-la."""
import sqlite3

import pytest

from canconer import basedades as bd
from canconer.web import crea_app


@pytest.fixture
def client():
    app = crea_app()
    app.config["TESTING"] = True
    return app.test_client()


def _ids(paperera=False):
    return [c["id"] for c in bd.llista_canconers(paperera=paperera)]


def test_enviar_desfer_i_recuperar(client):
    k = bd.crea_canconer("Vell")
    r = client.post(f"/canconer/{k}/paperera")
    assert r.status_code == 302 and f"paperera={k}" in r.headers["Location"]
    assert k not in _ids() and k in _ids(paperera=True)
    html = client.get(f"/?paperera={k}").get_data(as_text=True)
    assert "és a la paperera" in html and "Desfés" in html
    client.post(f"/canconer/{k}/recupera")
    assert k in _ids() and k not in _ids(paperera=True)


def test_nomes_s_esborra_per_sempre_des_de_la_paperera(client, dades_temporals):
    k = bd.crea_canconer("Esborrable")
    c = bd.crea_canco("Una cançó")
    bd.afegeix_entrada(k, c)
    assert client.post(f"/canconer/{k}/esborra").status_code == 400  # encara no és a la paperera
    client.post(f"/canconer/{k}/paperera")
    assert "Esborrable" in client.get("/paperera").get_data(as_text=True)
    client.post(f"/canconer/{k}/esborra")
    with pytest.raises(KeyError):
        bd.meta_canconer(k)
    assert bd.carrega_canco(c)["titol"] == "Una cançó"  # la cançó es queda a la biblioteca


def test_buidar_la_paperera(client):
    queda = bd.crea_canconer("Es queda")
    for titol in ("A", "B"):
        client.post(f"/canconer/{bd.crea_canconer(titol)}/paperera")
    client.post("/paperera/buida")
    assert _ids(paperera=True) == [] and queda in _ids()
    assert "La paperera és buida" in client.get("/paperera").get_data(as_text=True)


def test_la_migracio_afegeix_la_columna(dades_temporals):
    bd.crea_canconer("K")
    con = sqlite3.connect(dades_temporals / "canconers.sqlite3")
    assert "paperera" in {f[1] for f in con.execute("PRAGMA table_info(canconer)")}
    assert con.execute("PRAGMA user_version").fetchone()[0] == len(bd.MIGRACIONS)
    con.close()


# ---------------------------------------------------------------- Cançons


def test_eliminar_una_canco_des_del_canconer_la_porta_a_la_paperera(client):
    k = bd.crea_canconer("Prova")
    c = bd.crea_canco("Una prova")
    bd.afegeix_entrada(k, c)
    assert client.post(f"/api/canconer/{k}/entrada/{c}/paperera").get_json() == {"ok": True}
    assert bd.carrega_canconer(k)["cancons"] == []
    assert c not in [x["id"] for x in bd.biblioteca()]
    assert [x["id"] for x in bd.cancons_paperera()] == [c]
    assert "Una prova" in client.get("/paperera").get_data(as_text=True)
    # Recuperar-la la torna al cançoner d'on s'havia eliminat.
    client.post(f"/canco/{c}/recupera")
    assert [x["id"] for x in bd.carrega_canconer(k)["cancons"]] == [c]


def test_no_es_pot_eliminar_si_es_en_un_altre_canconer(client):
    k1, k2 = bd.crea_canconer("Un"), bd.crea_canconer("Dos")
    c = bd.crea_canco("Compartida")
    bd.afegeix_entrada(k1, c)
    bd.afegeix_entrada(k2, c)
    r = client.post(f"/api/canconer/{k1}/entrada/{c}/paperera")
    assert r.status_code == 409 and "«Dos»" in r.get_json()["error"]
    assert [x["id"] for x in bd.carrega_canconer(k1)["cancons"]] == [c]
    # Un cançoner que ja és a la paperera no compta.
    bd.envia_a_paperera(k2)
    assert client.post(f"/api/canconer/{k1}/entrada/{c}/paperera").status_code == 200


def test_des_de_la_biblioteca_nomes_si_no_es_a_cap_canconer(client):
    c = bd.crea_canco("Sola")
    k = bd.crea_canconer("K")
    d = bd.crea_canco("En un cançoner")
    bd.afegeix_entrada(k, d)
    r = client.post(f"/biblioteca/{d}/paperera")
    assert "error=" in r.headers["Location"]
    client.post(f"/biblioteca/{c}/paperera")
    assert [x["id"] for x in bd.cancons_paperera()] == [c]
    assert bd.recupera_canco(c) is None  # no venia de cap cançoner: torna a la biblioteca


def test_esborrar_per_sempre_i_buidar(client):
    c = bd.crea_canco("Fora")
    assert client.post(f"/canco/{c}/esborra").status_code == 400  # encara no és a la paperera
    bd.canco_a_paperera(c)
    client.post(f"/canco/{c}/esborra")
    with pytest.raises(KeyError):
        bd.carrega_canco(c)
    d = bd.crea_canco("Fora 2")
    bd.canco_a_paperera(d)
    k = bd.crea_canconer("K")
    bd.envia_a_paperera(k)
    client.post("/paperera/buida")
    assert bd.cancons_paperera() == [] and bd.llista_canconers(paperera=True) == []


def test_nova_canco_des_de_la_biblioteca(client):
    r = client.post("/biblioteca/nova", data={"titol": "Nova de la biblioteca", "autor": "Jo"})
    assert "/biblioteca/" in r.headers["Location"]
    nova = next(x for x in bd.biblioteca() if x["titol"] == "Nova de la biblioteca")
    assert nova["autor"] == "Jo" and nova["canconers"] == []
    k = bd.crea_canconer("On editar-la")
    r = client.post("/biblioteca/nova", data={"titol": "Per editar", "canconer": k})
    assert f"/canconer/{k}" in r.headers["Location"]
    assert [x["titol"] for x in bd.carrega_canconer(k)["cancons"]] == ["Per editar"]
