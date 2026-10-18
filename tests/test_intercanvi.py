import io
import json
import zipfile
from pathlib import Path

import pytest

from canconer import basedades as bd
from canconer import document, intercanvi, maquetacio, plantilles

FONT = next((Path(__file__).parent.parent / "canconer/static/fonts/cataleg").glob("lora-*.woff2")).read_bytes()


def _canconer_complet() -> str:
    """Cançoner amb dues cançons (una amb versió fixada), imatges i una tipografia importada."""
    k = bd.crea_canconer("Trobada", subtitol="Esplai", pagina_acords=True)
    imatge = bd.desa_imatge(b"\x89PNG imatge", "image/png", "foto.png")
    bd.desa_tipografia(FONT, "woff2", "Meva Lletra", 400, "normal")
    meta = bd.meta_canconer(k)
    portada = meta["especials"]["portada"]
    portada["elements"].append({"id": "img1", "tipus": "imatge", "x": 10, "y": 10, "w": 50, "h": 40, "src": imatge})
    estils = meta["estils"]
    estils["titol"]["font"] = "u-meva-lletra"
    bd.desa_meta(k, {"especials": {**meta["especials"], "portada": portada}, "estils": estils})

    a = bd.crea_canco("Primera", "Jo", document.de_text("C   G\nhola"))
    b = bd.crea_canco("Segona", "", document.de_text("D\nadeu"))
    contingut = bd.carrega_canco(b)["contingut"]
    contingut["pagines"][0]["elements"].append({"id": "img2", "tipus": "imatge", "x": 0, "y": 150, "w": 30, "h": 30, "src": imatge})
    bd.desa_esborrany(b, contingut=contingut)
    bd.afegeix_entrada(k, a)
    v = bd.ultima_versio(b)
    bd.afegeix_entrada(k, b, versio_id=v["id"])
    bd.actualitza_entrada(k, a, transport=2, inclosa=0, inici="qualsevol")
    bd.desa_esborrany(b, contingut=plantilles.normalitza_contingut(document.de_text("E\ncanviada")))  # l'esborrany ja no és la v1
    return k


def _sense_ids(pla):
    """Pla comparable entre instal·lacions: les imatges tenen ids nous i, en importar, els elements
    passen pel validador (que hi posa els valors per defecte que el dibuix ja suposa)."""
    import re

    from canconer import disseny
    pla = json.loads(json.dumps(pla))
    for p in pla["pagines"]:
        p["elements"] = disseny.elements(p["elements"])
        if p.get("mestra"):
            p["mestra"]["elements"] = disseny.elements(p["mestra"]["elements"])
    text = re.sub(r'"src": "[a-z0-9]+"', '"src": "IMG"', json.dumps(pla, sort_keys=True))
    return json.loads(text, parse_int=float)  # 30 i 30.0 es dibuixen igual


def test_duplicar_es_independent():
    k = _canconer_complet()
    copia = intercanvi.duplica(k)
    original, nou = bd.carrega_canconer(k), bd.carrega_canconer(copia)
    assert nou["titol"] == "Trobada (còpia)"
    camps = lambda c: [(e["id"], e["versio_id"], e["transport"], e["inclosa"], e["inici"]) for e in c["cancons"]]
    assert camps(nou) == camps(original)
    # Canviar el disseny o l'ordre de la còpia no toca l'original.
    bd.desa_meta(copia, {"subtitol": "Canviat"})
    bd.ordena_entrades(copia, list(reversed([e["id"] for e in nou["cancons"]])))
    assert bd.meta_canconer(k)["subtitol"] == "Esplai"
    assert [e["id"] for e in bd.carrega_canconer(k)["cancons"]] == [e["id"] for e in original["cancons"]]


def test_duplicar_tambe_les_cancons():
    k = _canconer_complet()
    copia = intercanvi.duplica(k, duplicar_cancons=True)
    originals = {e["id"] for e in bd.carrega_canconer(k)["cancons"]}
    noves = bd.carrega_canconer(copia)["cancons"]
    assert not originals & {e["id"] for e in noves}
    # Conserva el contingut que feia servir (també el de la versió fixada).
    assert maquetacio.acords_pagines(noves[1]["contingut"]["pagines"]) == ["D"]


def test_exportar_i_importar_en_una_base_de_dades_buida(tmp_path, monkeypatch):
    k = _canconer_complet()
    pla_original = maquetacio.pla(bd.carrega_canconer(k))
    fitxer = intercanvi.exporta(k)
    with zipfile.ZipFile(io.BytesIO(fitxer)) as z:
        dades = json.loads(z.read("canconer.json"))
        assert dades["format"] == intercanvi.FORMAT and len(dades["imatges"]) == 1 and len(dades["tipografies"]) == 1

    altra = tmp_path / "altra"
    monkeypatch.setattr(bd, "DIRECTORI", altra)
    nou = intercanvi.importa(fitxer)
    importat = bd.carrega_canconer(nou)
    assert _sense_ids(maquetacio.pla(importat)) == _sense_ids(pla_original)
    # Imatges i tipografies conservades.
    src = next(e["src"] for e in importat["especials"]["portada"]["elements"] if e["tipus"] == "imatge")
    cami, _ = bd.imatge(src)
    assert cami.read_bytes() == b"\x89PNG imatge"
    assert bd.tipografies_importades()[0]["nom"] == "Meva Lletra"
    # Historial i versió fixada.
    fixada = importat["cancons"][1]
    assert fixada["versio_numero"] == 1 and len(bd.versions(fixada["id"])) == 1


def test_importar_a_la_mateixa_instal_lacio_reutilitza_les_cancons():
    k = _canconer_complet()
    abans = {c["id"] for c in bd.biblioteca()}
    nou = intercanvi.importa(intercanvi.exporta(k))
    assert nou != k
    assert {c["id"] for c in bd.biblioteca()} == abans  # cap cançó duplicada
    assert len(bd.tipografies_importades()) == 1  # la tipografia tampoc es duplica


@pytest.mark.parametrize("dolent", [
    b"no soc un zip",
    "zip-sense-json",
    "aplicacio-estranya",
    "format-futur",
    "cancons-malmeses",
])
def test_fitxers_invalids_no_deixen_res(dolent, tmp_path):
    if isinstance(dolent, str):
        sortida = io.BytesIO()
        with zipfile.ZipFile(sortida, "w") as z:
            if dolent != "zip-sense-json":
                dades = {"format": 1, "aplicacio": "canconers", "canconer": {"titol": "X"}, "entrades": [], "cancons": [],
                         "imatges": [{"id": "a", "fitxer": "a.png", "tipus": "image/png"}], "tipografies": []}
                if dolent == "aplicacio-estranya":
                    dades["aplicacio"] = "altra"
                if dolent == "format-futur":
                    dades["format"] = 99
                if dolent == "cancons-malmeses":
                    dades["cancons"] = ["no és un diccionari"]
                z.writestr("canconer.json", json.dumps(dades))
                z.writestr("imatges/a.png", b"png")
        dolent = sortida.getvalue()
    abans = len(bd.llista_canconers())
    with pytest.raises(ValueError):
        intercanvi.importa(dolent)
    assert len(bd.llista_canconers()) == abans
    assert not list((tmp_path / "imatges").glob("*")) if (tmp_path / "imatges").exists() else True


def test_mida_maxima(monkeypatch):
    monkeypatch.setattr(intercanvi, "MIDA_MAXIMA", 10)
    with pytest.raises(intercanvi.ImportacioInvalida, match="MB"):
        intercanvi.importa(b"x" * 11)


def test_rutes_web(tmp_path):
    from canconer.web import crea_app
    client = crea_app().test_client()
    k = _canconer_complet()
    r = client.get(f"/canconer/{k}/exporta")
    assert r.status_code == 200 and r.headers["Content-Disposition"].endswith('trobada.canconer"')
    r2 = client.post("/canconer/importa", data={"fitxer": (io.BytesIO(r.data), "trobada.canconer")})
    assert r2.status_code == 302 and "/canconer/" in r2.headers["Location"]
    r3 = client.post("/canconer/importa", data={"fitxer": (io.BytesIO(b"dolent"), "x.canconer")})
    assert "error=" in r3.headers["Location"]
    r4 = client.post(f"/canconer/{k}/duplica")
    assert r4.status_code == 302 and len(bd.llista_canconers()) == 3
