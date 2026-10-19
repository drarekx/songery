import json
from datetime import datetime, timedelta

from canconer import basedades as bd
from canconer import document, maquetacio


def _acords(contingut):
    return maquetacio.acords_pagines(contingut["pagines"])


def _doc(text):
    return document.de_text(text)


def test_canconer_i_entrades():
    k = bd.crea_canconer("Trobada")
    a = bd.crea_canco("A", "", _doc("C\nla"))
    b = bd.crea_canco("B")
    bd.afegeix_entrada(k, a)
    bd.afegeix_entrada(k, b)
    assert [c["titol"] for c in bd.carrega_canconer(k)["cancons"]] == ["A", "B"]
    assert bd.ordena_entrades(k, [b, a])
    assert not bd.ordena_entrades(k, [a])
    bd.actualitza_entrada(k, a, inclosa=0, transport=3)
    c = bd.carrega_canconer(k)["cancons"][1]
    assert (c["id"], c["inclosa"], c["transport"]) == (a, False, 3)
    bd.treu_entrada(k, a)
    assert len(bd.carrega_canconer(k)["cancons"]) == 1
    assert bd.carrega_canco(a)["titol"] == "A"  # continua a la biblioteca


def test_versions_fixades_entre_canconers():
    k1, k2 = bd.crea_canconer("Un"), bd.crea_canconer("Dos")
    s = bd.crea_canco("Cançó", "", _doc("C\nprimera"))
    bd.afegeix_entrada(k1, s)  # segueix l'esborrany
    v1 = bd.ultima_versio(s)  # en importar es fixa l'última versió
    bd.afegeix_entrada(k2, s, versio_id=v1["id"])

    bd.desa_esborrany(s, contingut=_doc("D\nsegona"))
    c1 = bd.carrega_canconer(k1)["cancons"][0]
    c2 = bd.carrega_canconer(k2)["cancons"][0]
    assert _acords(c1["contingut"]) == ["D"]
    assert _acords(c2["contingut"]) == ["C"]  # fixada: no canvia
    assert c2["versio_numero"] == 1 and c2["esborrany_modificat"]
    assert c1["usos"] == 2


def test_crea_versio_nomes_si_hi_ha_canvis_i_restaura():
    s = bd.crea_canco("X", "", _doc("C\nu"))
    v1 = bd.crea_versio(s, "primera")
    assert v1["numero"] == 1
    assert bd.crea_versio(s) is None  # sense canvis
    bd.desa_esborrany(s, titol="X2", contingut=_doc("G\ndos"))
    bd.restaura_versio(s, v1["id"])
    canco = bd.carrega_canco(s)
    assert canco["titol"] == "X" and _acords(canco["contingut"]) == ["C"]
    versions = bd.versions(s)
    assert [v["numero"] for v in versions] == [2, 1]  # l'estat anterior s'ha desat com a v2
    assert versions[0]["titol"] == "X2"


def test_versio_automatica_si_fa_estona(monkeypatch):
    s = bd.crea_canco("Y", "", _doc("C\nu"))
    bd.crea_versio(s)
    bd.desa_esborrany(s, contingut=_doc("D\nu"))
    assert len(bd.versions(s)) == 1
    monkeypatch.setattr(bd, "INTERVAL_VERSIO_AUTOMATICA", timedelta(seconds=-1))
    bd.desa_esborrany(s, contingut=_doc("E\nu"))
    assert len(bd.versions(s)) == 2


def test_biblioteca_i_cerca():
    k = bd.crea_canconer("Llibre")
    s = bd.crea_canco("Muntanyes del Canigó", "Popular")
    bd.crea_canco("Una altra")
    bd.afegeix_entrada(k, s)
    resultats = bd.biblioteca("canigó")
    assert [r["titol"] for r in resultats] == ["Muntanyes del Canigó"]
    assert resultats[0]["canconers"] == [{"id": k, "titol": "Llibre"}]


def test_migra_els_json_antics(tmp_path):
    antic = {"id": "abc123", "titol": "Vell", "any": "2020",
             "cancons": [{"id": "s1", "titol": "U", "autor": "", "cos": "G\nhola", "transport": 2}]}
    (tmp_path / "canconers").mkdir()
    (tmp_path / "canconers" / "abc123.json").write_text(json.dumps(antic), "utf-8")
    bd._inicialitzades.clear()
    k = bd.carrega_canconer("abc123")
    assert k["titol"] == "Vell" and k["cancons"][0]["transport"] == 2
    assert _acords(k["cancons"][0]["contingut"]) == ["G"]
    assert (tmp_path / "canconers-migrats" / "abc123.json").exists()
    assert not list((tmp_path / "canconers").glob("*.json"))


def test_imatges(tmp_path):
    i = bd.desa_imatge(b"\x89PNG", "image/png", "foto.png")
    cami, tipus = bd.imatge(i)
    assert cami.read_bytes() == b"\x89PNG" and tipus == "image/png"


def test_pagines_lliures_i_elements_de_biblioteca():
    k = bd.crea_canconer("K")
    p = bd.crea_canco("Dedicatòria", tipus="pagina")
    bd.afegeix_entrada(k, p)
    bd.actualitza_entrada(k, p, inici="qualsevol")
    entrada = bd.carrega_canconer(k)["cancons"][0]
    assert entrada["tipus"] == "pagina" and entrada["inici"] == "qualsevol"
    assert bd.biblioteca() == []  # les pàgines lliures no són a la biblioteca de cançons
    i = bd.desa_element("Segell", [{"tipus": "forma", "x": 1, "y": 1, "w": 5, "h": 5}])
    assert bd.elements_desats()[0]["nom"] == "Segell"
    bd.esborra_element(i)
    assert bd.elements_desats() == []


def test_disseny_per_defecte_del_canconer():
    meta = bd.meta_canconer(bd.crea_canconer("K"))
    assert set(meta["especials"]) == {"portada", "index", "acords", "acords_dos", "index_qr", "contraportada"}
    assert meta["mestres"][0]["id"] == "estandard" and "lletra" in meta["estils"]
