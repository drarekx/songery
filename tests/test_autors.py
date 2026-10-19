"""Autors com a taula pròpia (#14): migració, vinculació, gestió, API i filtre de la biblioteca."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from canconer import basedades as bd
from canconer import intercanvi
from canconer.web import crea_app

ESQUEMA_5 = Path(__file__).parent / "fixtures" / "esquemes" / "esquema-5.sql"


@pytest.fixture
def client():
    return crea_app().test_client()


def test_la_migracio_fusiona_variants_sense_tocar_el_text(tmp_path, monkeypatch):
    monkeypatch.setattr(bd, "DIRECTORI", tmp_path)
    bd._inicialitzades.discard(tmp_path / "canconers.sqlite3")
    con = sqlite3.connect(tmp_path / "canconers.sqlite3")
    con.executescript(ESQUEMA_5.read_text())
    con.execute("PRAGMA user_version = 5")
    for i, autor in enumerate(["Popular", "popular", "  Pópular ", "Algú", ""]):
        con.execute("INSERT INTO canco (id, titol, autor, doc, creada, actualitzada) VALUES (?, ?, ?, '{}', ?, ?)",
                    (f"c{i}", f"Cançó {i}", autor, f"2026-01-0{i + 1}T10:00:00", "2026-01-01T10:00:00"))
    con.commit()
    con.close()
    autors = {a["nom"]: a for a in bd.autors()}
    assert set(autors) == {"Popular", "Algú"} and autors["Popular"]["cancons"] == 3
    with bd.connexio() as con:
        files = {f["id"]: (f["autor"], f["autor_id"]) for f in con.execute("SELECT id, autor, autor_id FROM canco")}
    assert files["c1"] == ("popular", autors["Popular"]["id"])  # el text no es toca
    assert files["c2"][1] == autors["Popular"]["id"] and files["c4"] == ("", None)


def test_crear_i_desar_vinculen_l_autor_amb_el_nom_unificat():
    a = bd.crea_canco("Una", "Popular catalana")
    b = bd.crea_canco("Dues", "  popular   CATALANA ")
    assert bd.carrega_canco(b)["autor"] == "Popular catalana"
    assert [x["cancons"] for x in bd.autors("popular")] == [2]
    bd.desa_esborrany(a, autor="Joan Alcover")
    assert {x["nom"] for x in bd.autors()} == {"Popular catalana", "Joan Alcover"}
    bd.desa_esborrany(a, autor="")
    assert bd.carrega_canco(a)["autor"] == ""


def test_reanomenar_fusionar_i_esborrar(client):
    a = bd.crea_canco("Una", "Guimera")
    b = bd.crea_canco("Dues", "Àngel Guimerà")
    errat = next(x for x in bd.autors() if x["nom"] == "Guimera")
    # Reanomenar amb el nom (sense accents, igual) d'un altre: es fusionen.
    r = client.put(f"/api/autors/{errat['id']}", json={"nom": "angel guimera"}).get_json()
    assert r["nom"] == "Àngel Guimerà" and bd.carrega_canco(a)["autor"] == "Àngel Guimerà"
    assert [x["nom"] for x in bd.autors()] == ["Àngel Guimerà"]
    # Reanomenar canvia el nom a totes les cançons.
    client.put(f"/api/autors/{r['id']}", json={"nom": "Àngel Guimerà i Jorge"})
    assert bd.carrega_canco(b)["autor"] == "Àngel Guimerà i Jorge"
    # No s'esborra mentre té cançons.
    assert client.delete(f"/api/autors/{r['id']}").status_code == 409
    sol = client.post("/api/autors", json={"nom": "Sense cançons"}).get_json()
    assert client.delete(f"/api/autors/{sol['id']}").status_code == 200
    assert client.put("/api/autors/noexisteix", json={"nom": "x"}).status_code == 404
    assert client.post("/api/autors", json={"nom": "  "}).status_code == 400


def test_cerca_sense_accents_i_filtre_de_la_biblioteca(client):
    bd.crea_canco("El cant dels ocells", "Popular")
    bd.crea_canco("La Balanguera", "Joan Alcover")
    alcover = client.get("/api/autors?q=alcover").get_json()
    assert [a["nom"] for a in alcover] == ["Joan Alcover"]
    assert [a["nom"] for a in client.get("/api/autors?q=JOAN").get_json()] == ["Joan Alcover"]
    html = client.get(f"/biblioteca?autor={alcover[0]['id']}").get_data(as_text=True)
    assert "La Balanguera" in html and "El cant dels ocells" not in html
    assert f'href="/biblioteca?autor={alcover[0]["id"]}' in client.get("/biblioteca").get_data(as_text=True)
    assert "Joan Alcover" in client.get("/autors").get_data(as_text=True)


def test_duplicar_un_canconer_vincula_els_autors():
    k = bd.crea_canconer("Original")
    bd.afegeix_entrada(k, bd.crea_canco("Una", "Popular"))
    nou = intercanvi.duplica(k, duplicar_cancons=True)
    id_copia = bd.carrega_canconer(nou)["cancons"][0]["id"]
    with bd.connexio() as con:
        assert con.execute("SELECT autor_id FROM canco WHERE id = ?", (id_copia,)).fetchone()[0]
    assert bd.autors()[0]["cancons"] == 2
