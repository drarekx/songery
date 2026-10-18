import json

from canconer import basedades, preferencies
from canconer.web import crea_app

import pytest


@pytest.fixture
def client():
    app = crea_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_per_defecte_i_desa():
    assert preferencies.carrega()["editor.amplePropietats"] == 320
    assert preferencies.desa({"editor.amplePropietats": 480})["editor.amplePropietats"] == 480
    assert json.loads((basedades.DIRECTORI / "preferencies.json").read_text())["editor.amplePropietats"] == 480
    assert preferencies.carrega()["editor.amplePropietats"] == 480


def test_ignora_valors_no_valids_i_claus_desconegudes():
    preferencies.desa({"editor.amplePropietats": 400})
    r = preferencies.desa({"editor.amplePropietats": 5000, "res": 1})
    assert r["editor.amplePropietats"] == 400 and "res" not in r
    assert preferencies.desa({"editor.amplePropietats": None})["editor.amplePropietats"] == 320


def test_fitxer_malmes_torna_als_valors_per_defecte():
    (basedades.DIRECTORI / "preferencies.json").write_text("{no és json")
    assert preferencies.carrega()["editor.amplePropietats"] == 320


def test_api_i_editor(client):
    assert client.get("/api/preferencies").get_json()["editor.amplePropietats"] == 320
    assert client.patch("/api/preferencies", json={"editor.amplePropietats": 500}).get_json()["editor.amplePropietats"] == 500
    assert client.patch("/api/preferencies", data="x", content_type="text/plain").status_code == 400
    id_canconer = basedades.crea_canconer("Prova")
    html = client.get(f"/canconer/{id_canconer}").get_data(as_text=True)
    assert "--ample-propietats: 500px" in html and 'id="preferencies"' in html
