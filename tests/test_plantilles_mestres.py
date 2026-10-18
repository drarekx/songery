"""Plantilles (pàgines mestres) per cançó i per pàgina, amb el costat forçat (issue #2)."""
import pytest

from canconer import basedades as bd
from canconer import disseny, maquetacio, plantilles
from canconer.web import crea_app


def _mestra(id_mestra, text_esquerra, text_dreta):
    text = lambda t: {"id": t, "tipus": "text", "x": 10, "y": 10, "w": 50, "h": 10, "text": t, "estil": "text"}
    return {"id": id_mestra, "nom": id_mestra.upper(), "parell": {"elements": [text(text_esquerra)]},
            "senar": {"elements": [text(text_dreta)]}}


def _canconer(pagines):
    canco = {"id": "c1", "titol": "Cançó", "autor": "", "tipus": "canco", "inici": "esquerra", "transport": 0,
             "inclosa": True, "contingut": {"format": 2, "pagines": pagines}}
    return plantilles.amb_valors_per_defecte({
        "titol": "Prova", "subtitol": "", "any": "", "contraportada": "", "pagina_acords": False,
        "posicio_acords": "inici", "instrument": "guitarra", "cancons": [canco],
        "mestres": plantilles.mestres() + [_mestra("x", "x-esq", "x-dre"), _mestra("y", "y-esq", "y-dre")]})


def _textos_mestra(pla):
    return [p["mestra"]["elements"][0]["text"] for p in pla["pagines"] if p["tipus"] == "canco"]


def test_sense_costat_segueix_la_paritat():
    pla = maquetacio.pla(_canconer([plantilles.pagina([], mestra="x"), plantilles.pagina([], mestra="x")]))
    assert _textos_mestra(pla) == ["x-esq", "x-dre"]


def test_barrejar_mestres_i_costats():
    pagines = [{**plantilles.pagina([], mestra="x"), "costat": "dreta"},
               {**plantilles.pagina([], mestra="y"), "costat": "esquerra"}]
    assert _textos_mestra(maquetacio.pla(_canconer(pagines))) == ["x-dre", "y-esq"]


def test_el_costat_es_valida_i_es_opcional():
    assert "costat" not in disseny.pagina({"mestra": "x"})
    assert "costat" not in disseny.pagina({"mestra": "x", "costat": "amunt"})
    assert disseny.pagina({"mestra": "x", "costat": "esquerra"})["costat"] == "esquerra"


@pytest.fixture
def client():
    app = crea_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_canco_nova_amb_plantilla(client):
    k = bd.crea_canconer("Amb plantilles")
    bd.desa_meta(k, {"mestres": plantilles.mestres() + [_mestra("x", "a", "b")]})
    for tipus in ("canco", "pagina"):
        id_canco = client.post(f"/api/canconer/{k}/canco", json={"tipus": tipus, "mestra": "x"}).get_json()["id"]
        assert {p["mestra"] for p in bd.carrega_canco(id_canco)["contingut"]["pagines"]} == {"x"}
    # Una mestra que no és del cançoner s'ignora; sense mestra, la de sempre.
    id_canco = client.post(f"/api/canconer/{k}/canco", json={"mestra": "noexisteix"}).get_json()["id"]
    assert bd.carrega_canco(id_canco)["contingut"]["pagines"][0]["mestra"] == "estandard"
    id_canco = client.post(f"/api/canconer/{k}/canco", json={"mestra": None}).get_json()["id"]
    assert bd.carrega_canco(id_canco)["contingut"]["pagines"][0]["mestra"] == "estandard"


def test_el_costat_es_desa_amb_la_canco(client):
    k = bd.crea_canconer("Costats")
    id_canco = client.post(f"/api/canconer/{k}/canco", json={}).get_json()["id"]
    contingut = bd.carrega_canco(id_canco)["contingut"]
    contingut["pagines"][0]["costat"] = "dreta"
    assert client.put(f"/api/canco/{id_canco}", json={"contingut": contingut}).status_code == 200
    assert bd.carrega_canco(id_canco)["contingut"]["pagines"][0]["costat"] == "dreta"
    pla = client.get(f"/api/canconer/{k}/pla").get_json()
    primera = next(p for p in pla["pagines"] if p["tipus"] == "canco")
    # Pàgina 4 (parell = esquerra) però amb la mestra de la dreta: número a la cantonada dreta.
    assert primera["numero"] % 2 == 0
    assert primera["mestra"]["elements"][0]["x"] == plantilles.mestres()[0]["senar"]["elements"][0]["x"]


def test_copiar_mestres_d_un_altre_canconer(client):
    origen = bd.crea_canconer("Origen")
    estil = {**plantilles.ESTILS["text"], "nom": "Especial", "mida": 30}
    m = _mestra("estandard", "a", "b")  # mateix id que una del destí: se n'ha de crear un de nou
    m["parell"]["elements"][0]["estil"] = "especial"
    bd.desa_meta(origen, {"mestres": [m, _mestra("x", "c", "d")],
                          "estils": {**bd.meta_canconer(origen)["estils"], "especial": estil}})
    desti = bd.crea_canconer("Destí")

    altres = client.get(f"/api/canconer/{desti}/mestres/altres").get_json()["canconers"]
    assert origen in [k["id"] for k in altres] and desti not in [k["id"] for k in altres]

    r = client.post(f"/api/canconer/{desti}/mestres/copia", json={"de": origen, "mestres": ["estandard", "x"]}).get_json()
    ids = [m["id"] for m in r["mestres"]]
    assert len(r["noves"]) == 2 and "x" in r["noves"] and ids.count("estandard") == 1
    assert r["estils"]["especial"]["mida"] == 30
    assert client.post(f"/api/canconer/{desti}/mestres/copia", json={"de": "noexisteix", "mestres": []}).status_code == 404
