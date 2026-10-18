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
