"""Còpies de seguretat, migracions d'esquema i comprovació de versions (issue #5)."""
import io
import json
import sqlite3
import zipfile

import pytest

from canconer import actualitzacions, basedades as bd, copies


def _amb_dades(directori):
    k = bd.crea_canconer("Original")
    (directori / "imatges").mkdir(exist_ok=True)
    (directori / "imatges" / "foto.png").write_bytes(b"png")
    (directori / "tipografies").mkdir(exist_ok=True)
    (directori / "tipografies" / "lletra.woff2").write_bytes(b"woff2")
    return k


def test_la_copia_conte_tot_i_es_consistent(dades_temporals):
    _amb_dades(dades_temporals)
    copia = copies.fes_copia("1.2.3", "manual")
    assert copia.parent == dades_temporals / "copies" and "_v1.2.3_manual" in copia.name
    with zipfile.ZipFile(copia) as z:
        assert {"canconers.sqlite3", "imatges/foto.png", "tipografies/lletra.woff2", "COPIA.txt"} <= set(z.namelist())
        bd_copia = dades_temporals / "llegida.sqlite3"
        bd_copia.write_bytes(z.read("canconers.sqlite3"))
    con = sqlite3.connect(bd_copia)
    assert con.execute("SELECT count(*) FROM canconer").fetchone()[0] == 1
    con.close()


def test_es_conserven_les_ultimes(dades_temporals):
    _amb_dades(dades_temporals)
    for i in range(7):
        (copies.directori() / f"2020-01-0{i + 1}_1200_v1.0.0.zip").write_bytes(b"")
    copies.fes_copia("1.0.0")
    noms = [c.name for c in copies.llista()]
    assert len(noms) == copies.CONSERVADES and noms[0].startswith(tuple("23456789"))  # la nova és la primera
    assert "2020-01-01_1200_v1.0.0.zip" not in noms


def test_restaurar_torna_les_dades_i_guarda_l_estat_actual(dades_temporals):
    k = _amb_dades(dades_temporals)
    copia = copies.fes_copia("1.0.0")
    bd.esborra_canconer(k)
    bd.crea_canconer("Nou")
    (dades_temporals / "imatges" / "foto.png").unlink()
    (dades_temporals / "imatges" / "nova.png").write_bytes(b"x")

    abans = copies.restaura(copia, "1.0.0")
    assert [c["titol"] for c in bd.llista_canconers()] == ["Original"]
    assert (dades_temporals / "imatges" / "foto.png").exists()
    assert not (dades_temporals / "imatges" / "nova.png").exists()
    with zipfile.ZipFile(abans) as z:
        assert "imatges/nova.png" in z.namelist()


def test_no_es_restaura_un_fitxer_que_no_es_una_copia(dades_temporals):
    _amb_dades(dades_temporals)
    dolent = dades_temporals / "dolent.zip"
    with zipfile.ZipFile(dolent, "w") as z:
        z.writestr("res.txt", "hola")
    with pytest.raises(copies.CopiaInvalida):
        copies.restaura(dolent)
    (dades_temporals / "trencat.zip").write_bytes(b"no soc un zip")
    with pytest.raises(copies.CopiaInvalida):
        copies.restaura(dades_temporals / "trencat.zip")
    assert [c["titol"] for c in bd.llista_canconers()] == ["Original"]


def test_migracions_amb_copia_previa(dades_temporals, monkeypatch):
    _amb_dades(dades_temporals)
    con = sqlite3.connect(dades_temporals / "canconers.sqlite3")
    assert con.execute("PRAGMA user_version").fetchone()[0] == len(bd.MIGRACIONS)
    con.close()

    # Una migració nova: abans es fa una còpia i després queda aplicada.
    afegeix = lambda con: con.execute("CREATE TABLE prova_migracio (x)")  # noqa: E731
    monkeypatch.setattr(bd, "MIGRACIONS", [*bd.MIGRACIONS, afegeix])
    bd._inicialitzades.clear()
    bd.llista_canconers()
    assert any("abans-de-migrar" in c.name for c in copies.llista())
    con = sqlite3.connect(dades_temporals / "canconers.sqlite3")
    assert con.execute("PRAGMA user_version").fetchone()[0] == len(bd.MIGRACIONS)
    con.close()

    # Una migració que falla no deixa res a mitges.
    def trencada(con):
        con.execute("CREATE TABLE a_mitges (x)")
        raise ValueError("ui")
    monkeypatch.setattr(bd, "MIGRACIONS", [*bd.MIGRACIONS, trencada])
    bd._inicialitzades.clear()
    with pytest.raises(RuntimeError, match="No s'ha canviat res"):
        bd.llista_canconers()
    con = sqlite3.connect(dades_temporals / "canconers.sqlite3")
    assert con.execute("SELECT 1 FROM sqlite_master WHERE name = 'a_mitges'").fetchone() is None
    assert con.execute("PRAGMA user_version").fetchone()[0] == len(bd.MIGRACIONS) - 1
    con.close()


def test_comparacio_de_versions(monkeypatch):
    assert actualitzacions.es_mes_nova("1.10.0", "1.9.9")
    assert actualitzacions.es_mes_nova("v1.0.1", "1.0")
    assert not actualitzacions.es_mes_nova("1.0", "1.0.0")
    assert not actualitzacions.es_mes_nova("0.9", "1.0.0")
    assert actualitzacions.versio_actual() == open("eines/app/VERSIO").read().strip()

    resposta = io.BytesIO(json.dumps({"tag_name": "v99.0.0", "html_url": "u", "body": "notes"}).encode())
    resposta.__enter__ = lambda *a: resposta
    resposta.__exit__ = lambda *a: None
    monkeypatch.setattr(actualitzacions.urllib.request, "urlopen", lambda *a, **k: resposta)
    assert actualitzacions.comprova() == {"versio": "99.0.0", "url": "u", "notes": "notes"}


def test_context_ssl_fa_servir_els_certificats_de_certifi():
    """Dins l'app empaquetada, urllib no troba els certificats del sistema (CERTIFICATE_VERIFY_FAILED):
    les peticions HTTPS amb urllib han de fer servir els de certifi."""
    import ssl

    from canconer import actualitzacions

    ctx = actualitzacions.context_ssl()
    assert isinstance(ctx, ssl.SSLContext) and ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.cert_store_stats()["x509_ca"] > 50  # el paquet de certifi, no un magatzem buit
