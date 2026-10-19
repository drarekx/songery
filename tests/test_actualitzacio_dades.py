"""Actualitzar l'app no pot perdre mai cap dada.

Per a cada esquema de base de dades de les versions publicades (tests/fixtures/esquemes, només
l'estructura, sense dades), es crea una base de dades amb dades inventades, s'obre amb el codi actual
(que hi aplica les migracions) i es comprova que hi és tot: cançoners, cançons, versions, entrades,
portades retocades... i que les pàgines de l'app funcionen. Abans de migrar s'ha de fer una còpia.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from canconer import basedades as bd
from canconer import copies, document, maquetacio, plantilles
from canconer.web import crea_app

ESQUEMES = sorted((Path(__file__).parent / "fixtures" / "esquemes").glob("esquema-*.sql"))
ARA = "2026-01-01T10:00:00"


def _columnes(con, taula: str) -> set[str]:
    return {f[1] for f in con.execute(f"PRAGMA table_info({taula})")}


def _insereix(con, taula: str, fila: dict) -> None:
    """Insereix només les columnes que existeixen en aquell esquema."""
    fila = {k: v for k, v in fila.items() if k in _columnes(con, taula)}
    con.execute(f"INSERT INTO {taula} ({', '.join(fila)}) VALUES ({', '.join('?' * len(fila))})", list(fila.values()))


def _base_antiga(cami: Path, esquema: Path) -> dict:
    """Base de dades amb l'esquema antic i dades inventades. Torna què s'hi ha posat."""
    versio = int(esquema.stem.split("-")[1])
    con = sqlite3.connect(cami)
    con.executescript(esquema.read_text())
    con.execute(f"PRAGMA user_version = {versio}")
    doc = lambda text: json.dumps(plantilles.de_document(document.de_text(text)), ensure_ascii=False)
    cancons = {
        "c1": ("Primera", "Popular", doc("G   D\nHola món\n\n[Chorus]\nC\nla la")),
        "c2": ("Segona", "", doc("Am\nUna altra")),
        "c3": ("Solta", "Algú", doc("E\nNo és a cap cançoner")),
    }
    for id_, (titol, autor, d) in cancons.items():
        _insereix(con, "canco", {"id": id_, "titol": titol, "autor": autor, "doc": d, "creada": ARA, "actualitzada": ARA,
                                 "tipus": "canco"})
    _insereix(con, "versio", {"id": "v1", "canco_id": "c1", "numero": 1, "titol": "Primera", "autor": "Popular",
                              "doc": cancons["c1"][2], "nota": "Inicial", "creada": ARA})
    portada_propia = plantilles.pagina([{"id": "p1", "tipus": "text", "text": "La meva portada", "x": 10, "y": 10,
                                         "w": 100, "h": 20, "estil": "titol"}], mestra=None)
    canconers = {
        "k1": {"titol": "Amb portada pròpia", "subtitol": "Sub", "especials": {"portada": portada_propia}},
        "k2": {"titol": "Amb la de sempre", "any": "2025"},
    }
    for id_, dades in canconers.items():
        _insereix(con, "canconer", {"id": id_, "dades": json.dumps(dades, ensure_ascii=False), "creat": ARA, "actualitzat": ARA})
    for k, c, pos, v in (("k1", "c1", 0, "v1"), ("k1", "c2", 1, None), ("k2", "c2", 0, None)):
        _insereix(con, "entrada", {"canconer_id": k, "canco_id": c, "posicio": pos, "versio_id": v})
    con.commit()
    con.close()
    return {"cancons": cancons, "canconers": canconers}


@pytest.mark.parametrize("esquema", ESQUEMES, ids=lambda p: p.stem)
def test_actualitzar_des_d_una_versio_antiga_no_perd_res(tmp_path, monkeypatch, esquema):
    monkeypatch.setattr(bd, "DIRECTORI", tmp_path)
    bd._inicialitzades.discard(tmp_path / "canconers.sqlite3")
    posat = _base_antiga(tmp_path / "canconers.sqlite3", esquema)

    canconers = {k["id"]: k for k in bd.llista_canconers()}
    assert set(canconers) == set(posat["canconers"])
    assert {c["id"] for c in bd.biblioteca()} == set(posat["cancons"])
    for id_, (titol, autor, _doc) in posat["cancons"].items():
        canco = bd.carrega_canco(id_)
        assert (canco["titol"], canco["autor"]) == (titol, autor)
        assert canco["contingut"]["pagines"], id_
    assert [v["numero"] for v in bd.versions("c1")] == [1]

    k1, k2 = bd.carrega_canconer("k1"), bd.carrega_canconer("k2")
    assert [c["id"] for c in k1["cancons"]] == ["c1", "c2"] and [c["id"] for c in k2["cancons"]] == ["c2"]
    assert k1["cancons"][0]["versio_id"] == "v1"
    assert k1["especials"]["portada"]["elements"][0]["text"] == "La meva portada"
    assert len(k2["especials"]["portada"]["elements"]) == 4  # la portada que tenia (no la nova per defecte)
    assert maquetacio.pla(k1)["total"] >= 4

    with sqlite3.connect(tmp_path / "canconers.sqlite3") as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == len(bd.MIGRACIONS)
    assert any("abans-de-migrar" in c.name for c in copies.llista())  # còpia abans de migrar

    client = crea_app().test_client()
    html = client.get("/").get_data(as_text=True)
    assert "Amb portada pròpia" in html and "Amb la de sempre" in html
    for url in ("/biblioteca", "/canconer/k1", "/canconer/k1/opcions", "/canconer/k1/imprimir", "/canconer/k1/imprimible"):
        assert client.get(url).status_code == 200, url


def test_hi_ha_un_esquema_per_a_cada_salt_de_versio():
    """Si s'afegeix una migració, cal desar l'esquema de la versió publicada anterior (vegeu la skill
    publica-versio): així aquest test prova també l'actualització des d'aquella versió."""
    versions = sorted(int(e.stem.split("-")[1]) for e in ESQUEMES)
    assert versions[0] == 0 and versions[-1] == len(bd.MIGRACIONS) - 1
