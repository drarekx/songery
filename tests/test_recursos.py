from canconer import basedades as bd
from canconer import parser, recursos
from canconer.web import crea_app

import pytest


@pytest.fixture
def client():
    app = crea_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.mark.parametrize("clau", list(recursos.BASES))
def test_crea_canconer_base(client, clau):
    r = client.post(f"/canconer/base/{clau}")
    assert r.status_code == 302
    id_canconer = r.location.rsplit("/", 1)[-1]
    c = bd.carrega_canconer(id_canconer)
    base = recursos.BASES[clau]
    assert c["titol"] == base["titol"]
    titols = [e["titol"] for e in c["cancons"]]
    assert titols == [s["titol"] for s in base["cancons"]]


def test_les_cancons_tenen_acords_valids():
    for base in recursos.BASES.values():
        for c in base["cancons"]:
            linies = parser.analitza(c["cos"])
            assert any(l.tipus == "acords" for l in linies), c["titol"]


def test_base_inexistent_i_enllacos_a_l_inici(client):
    assert client.post("/canconer/base/noexisteix").status_code == 404
    html = client.get("/").get_data(as_text=True)
    assert "/canconer/base/nadales" in html and "/canconer/base/populars" in html
