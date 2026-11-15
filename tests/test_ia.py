"""Intel·ligència artificial: configuració, clauer i cançó a partir d'una foto (sense cridar cap proveïdor)."""

import io
import json
from types import SimpleNamespace

import pytest

from canconer import basedades, clauer, ia, plantilles, preferencies
from canconer.web import crea_app

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


@pytest.fixture
def client():
    app = crea_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture(autouse=True)
def clauer_fals(monkeypatch):
    """Un clauer en memòria: els tests no toquen mai el clauer del Mac ni llegeixen claus de l'entorn."""
    claus = {}
    monkeypatch.setattr(clauer, "disponible", lambda: True)
    monkeypatch.setattr(clauer, "llegeix", lambda compte: claus.get(compte))
    monkeypatch.setattr(clauer, "esborra", lambda compte: claus.pop(compte, None))

    def desa(compte, clau):
        if len(clau) < 8:
            raise clauer.ErrorClauer("Aquesta clau no sembla una clau d'API.")
        claus[compte] = clau
    monkeypatch.setattr(clauer, "desa", desa)
    for p in ia.PROVEIDORS.values():
        monkeypatch.delenv(p["entorn"], raising=False)
    return claus


def test_configuracio_per_defecte_i_desa(client, clauer_fals):
    c = client.get("/api/ia").get_json()
    assert c["proveidor"] == "anthropic" and [p["id"] for p in c["proveidors"]] == ["anthropic", "openai", "openrouter"]
    assert not any(p["te_clau"] for p in c["proveidors"])

    r = client.put("/api/ia", json={"proveidor": "openrouter", "models": {"openrouter": "un/model"}, "claus": {"openrouter": "sk-or-12345678"}})
    c = r.get_json()
    assert r.status_code == 200 and c["proveidor"] == "openrouter"
    assert next(p for p in c["proveidors"] if p["id"] == "openrouter") == {
        **next(p for p in c["proveidors"] if p["id"] == "openrouter"), "model": "un/model", "te_clau": True}
    # La clau és al clauer i enlloc més: ni a la resposta ni a la carpeta de dades.
    assert clauer_fals == {"openrouter": "sk-or-12345678"}
    assert "sk-or-12345678" not in r.get_data(as_text=True)
    assert "sk-or-12345678" not in (basedades.DIRECTORI / "preferencies.json").read_text()
    assert "sk-or-12345678" not in client.get("/ia").get_data(as_text=True)

    assert client.put("/api/ia", json={"claus": {"openrouter": ""}}).get_json()["proveidors"][2]["te_clau"] is False
    assert client.put("/api/ia", json={"proveidor": "altre"}).status_code == 400
    assert client.put("/api/ia", json={"claus": {"openai": "curta"}}).status_code == 400


def test_clau_de_la_variable_d_entorn(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-de-l-entorn")
    assert ia.clau("openai") == "sk-de-l-entorn" and ia.clau("anthropic") is None


def test_clau_no_valida_no_arriba_al_clauer(monkeypatch):
    monkeypatch.undo()  # el clauer de debò, però sense arribar a cridar `security`
    monkeypatch.setattr(clauer, "_security", lambda *a, **k: pytest.fail("no s'ha de cridar"))
    for dolenta in ('sk-"; delete-generic-password', "amb espais dins", "curta", "línia\nnova-12345"):
        with pytest.raises(clauer.ErrorClauer):
            clauer.desa("openai", dolenta)
    with pytest.raises(ValueError):
        clauer.llegeix("../compte")


def test_sense_configurar_diu_que_cal_fer(client):
    r = client.post("/api/ia/canco-de-foto", data={"foto": (io.BytesIO(JPEG), "f.jpg")}, headers={"X-Requested-With": "canconers"})
    assert r.status_code == 409 and "configurat" in r.get_json()["error"]


def test_la_lectura_nomes_des_de_l_app(client):
    assert client.post("/api/ia/canco-de-foto", data={"foto": (io.BytesIO(JPEG), "f.jpg")}).status_code == 403


RESPOSTA = {
    "titol": "La lluna, la pruna", "autor": "Popular catalana",
    "text": "G              D7\nLa lluna, la pruna,\n      G\nvestida de dol",
    "partitures": [{"x": 50, "y": 100, "ample": 900, "alt": 300}, {"x": 0, "y": 0, "ample": 5, "alt": 5}, {"x": "?"}],
}


def _anthropic_fals(monkeypatch, text, stop="end_turn", vist=None):
    import anthropic

    def create(**parametres):
        if vist is not None:
            vist.append(parametres)
        return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)])
    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    monkeypatch.setattr(ia, "_client_anthropic", lambda clau: (anthropic, client))


def test_canco_de_foto_amb_anthropic(client, monkeypatch, clauer_fals):
    clauer_fals["anthropic"] = "sk-ant-12345678"
    vist = []
    _anthropic_fals(monkeypatch, json.dumps(RESPOSTA), vist=vist)
    r = client.post("/api/ia/canco-de-foto", data={"foto": (io.BytesIO(JPEG), "f.jpg")}, headers={"X-Requested-With": "canconers"})
    d = r.get_json()
    assert r.status_code == 200 and d["titol"] == "La lluna, la pruna" and d["autor"] == "Popular catalana"
    assert d["text"].startswith("G              D7\nLa lluna")
    # Un sol retall vàlid, en fraccions de la imatge i amb una mica de marge.
    assert len(d["partitures"]) == 1
    p = d["partitures"][0]
    assert 0.03 < p["x"] < 0.05 and 0.08 < p["y"] < 0.1 and 0.9 < p["ample"] <= 0.93 and 0.3 < p["alt"] < 0.33
    # El que s'ha enviat: el model triat, la imatge i la sortida estructurada.
    enviat = vist[0]
    assert enviat["model"] == "claude-opus-5-5" and enviat["output_config"]["format"]["type"] == "json_schema"
    assert enviat["messages"][0]["content"][0]["source"]["media_type"] == "image/jpeg"


def test_canco_de_foto_amb_openai_i_openrouter(monkeypatch, clauer_fals):
    import openai
    vist = []

    def create(**parametres):
        vist.append(parametres)
        missatge = SimpleNamespace(content="```json\n" + json.dumps(RESPOSTA) + "\n```", refusal=None)
        return SimpleNamespace(choices=[SimpleNamespace(message=missatge, finish_reason="stop")])
    fals = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(ia, "_client_openai", lambda proveidor, clau: (openai, fals))
    for proveidor in ("openai", "openrouter"):
        clauer_fals[proveidor] = "sk-12345678"
        preferencies.desa({"ia.proveidor": proveidor, f"ia.model.{proveidor}": "model-x"})
        d = ia.canco_de_foto(JPEG, "image/jpeg")
        assert d["titol"] == "La lluna, la pruna" and len(d["partitures"]) == 1
    assert vist[0]["model"] == "model-x" and vist[0]["messages"][1]["content"][0]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_respostes_que_no_serveixen(monkeypatch, clauer_fals):
    clauer_fals["anthropic"] = "sk-ant-12345678"
    _anthropic_fals(monkeypatch, "No ho sé llegir.")
    with pytest.raises(ia.ErrorIA, match="format"):
        ia.canco_de_foto(JPEG, "image/jpeg")
    _anthropic_fals(monkeypatch, json.dumps({"titol": "", "autor": "", "text": "", "partitures": []}))
    with pytest.raises(ia.ErrorIA, match="cap cançó"):
        ia.canco_de_foto(JPEG, "image/jpeg")
    _anthropic_fals(monkeypatch, "", stop="refusal")
    with pytest.raises(ia.ErrorIA, match="negat"):
        ia.canco_de_foto(JPEG, "image/jpeg")
    with pytest.raises(ia.ErrorIA, match="JPG"):
        ia.canco_de_foto(b"GIF89a", "image/gif")


def test_errors_del_proveidor_en_catala(monkeypatch, clauer_fals):
    import anthropic
    import httpx2
    clauer_fals["anthropic"] = "sk-ant-12345678"
    resposta = httpx2.Response(401, request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))

    def create(**_):
        raise anthropic.AuthenticationError("invalid x-api-key", response=resposta, body=None)
    monkeypatch.setattr(ia, "_client_anthropic", lambda clau: (anthropic, SimpleNamespace(messages=SimpleNamespace(create=create))))
    with pytest.raises(ia.ErrorIA, match="no accepta la clau") as e:
        ia.canco_de_foto(JPEG, "image/jpeg")
    assert e.value.codi == 401


def _imatge() -> str:
    return basedades.puja_imatge(JPEG, "partitura.jpg")


def test_canco_nova_amb_partitura_a_dalt_de_la_lletra(client):
    id_canconer = basedades.crea_canconer("Prova")
    src = _imatge()
    r = client.post(f"/api/canconer/{id_canconer}/canco", json={
        "titol": "La lluna", "autor": "Popular", "text": RESPOSTA["text"], "partitures": [{"src": src, "proporcio": 0.3}, {"src": "no-existeix", "proporcio": 1}]})
    canco = basedades.carrega_canco(r.get_json()["id"])
    assert canco["titol"] == "La lluna" and len(canco["contingut"]["pagines"]) == 1
    lletra = next(e for e in canco["contingut"]["pagines"][0]["elements"] if e["tipus"] == "lletra")
    blocs = lletra["doc"]["content"]
    assert blocs[0] == {"type": "imatge", "attrs": {"src": src, "posicio": "centre", "amplada": 100}}
    assert [n["attrs"]["nom"] for b in blocs for n in b.get("content", []) if n["type"] == "acord"] == ["G", "D7", "G"]
    assert src in basedades.usos_imatges()  # la imatge es fa servir: no es pot esborrar de la mèdia


def test_partitura_alta_va_sola_a_la_primera_pagina():
    doc = {"type": "doc", "content": [{"type": "linia", "content": [{"type": "text", "text": "La lluna"}]}]}
    contingut = plantilles.de_document_amb_partitures(doc, [{"src": "abc", "proporcio": 1.6}])
    primera, segona = contingut["pagines"]
    imatge = next(e for e in primera["elements"] if e["tipus"] == "lletra")["doc"]["content"][0]
    assert imatge["type"] == "imatge" and imatge["attrs"]["amplada"] < 100  # reduïda perquè hi càpiga sencera
    assert [e["tipus"] for e in segona["elements"]] == ["lletra"]
    # Sense lletra, només la partitura; sense partitura, com sempre.
    assert len(plantilles.de_document_amb_partitures({"type": "doc", "content": [{"type": "linia"}]}, [{"src": "abc", "proporcio": 1.6}])["pagines"]) == 1
    sense = plantilles.de_document_amb_partitures(doc, [])["pagines"]
    assert len(sense) == 1 and next(e for e in sense[0]["elements"] if e["tipus"] == "lletra")["doc"] == doc


def test_canco_nova_a_la_biblioteca(client):
    r = client.post("/api/biblioteca/canco", json={"titol": "", "text": "Una lletra"}).get_json()
    assert basedades.carrega_canco(r["id"])["titol"] == "Nova cançó" and r["url"].endswith(f"/biblioteca/{r['id']}/edita")
    id_canconer = basedades.crea_canconer("Prova")
    r = client.post("/api/biblioteca/canco", json={"titol": "A", "text": "x", "canconer": id_canconer}).get_json()
    assert f"/canconer/{id_canconer}" in r["url"]
