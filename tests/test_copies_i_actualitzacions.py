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


def test_es_conserven_les_recents_i_les_dels_ultims_30_dies(dades_temporals):
    """Es conserven sempre les 10 més recents i totes les dels últims 30 dies; les velles, no."""
    from datetime import datetime, timedelta

    _amb_dades(dades_temporals)
    for i in range(12):  # velles (fa anys): de sobres per passar de les 10 més recents
        (copies.directori() / f"2020-01-{i + 1:02d}_1200_v1.0.0.zip").write_bytes(b"")
    fa_poc = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    for i in range(12):  # dels últims dies: totes es queden
        (copies.directori() / f"{fa_poc}_12{i:02d}_v1.0.0.zip").write_bytes(b"")
    copies.fes_copia("1.0.0")
    noms = [c.name for c in copies.llista()]
    assert sum(n.startswith(fa_poc) for n in noms) == 12
    assert not any(n.startswith("2020-") for n in noms)  # més de 30 dies i fora de les 10 més recents
    assert noms[0] > fa_poc  # la nova és la primera


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


def test_si_les_dades_desapareixen_l_inici_ofereix_la_copia_que_en_te():
    """Protecció: amb la base de dades buida i una còpia amb dades, l'inici ho diu i la restaura."""
    from canconer import basedades as bd, copies, exemple
    from canconer.web import crea_app

    exemple.crea_exemple()
    copia = copies.fes_copia("1.4.5", "abans-d-actualitzar")
    with bd.connexio() as con:  # «desapareixen» les dades
        con.execute("DELETE FROM entrada")
        con.execute("DELETE FROM canconer")
        con.execute("DELETE FROM canco")
    # Les còpies que es facin ara (buides) no han de fer fora la que té dades.
    for i in range(copies.CONSERVADES + 2):
        copies.fes_copia("1.4.5", f"buida-{i}")
    assert copia in copies.llista() and copies.ultima_amb_dades() == copia
    assert copies.resum(copia)["canconers"] == 1

    client = crea_app().test_client()
    html = client.get("/").get_data(as_text=True)
    assert "hi ha una còpia de seguretat amb les teves dades" in html and copia.name in html
    assert client.post("/copies/restaura", data={"copia": "no-existeix.zip"}).status_code == 404
    client.post("/copies/restaura", data={"copia": copia.name})
    assert [k["titol"] for k in bd.llista_canconers()] == ["Cançoner d'exemple"]
    assert "hi ha una còpia de seguretat amb les teves dades" not in client.get("/").get_data(as_text=True)


def test_sense_dades_ni_copies_no_surt_cap_avis():
    from canconer.web import crea_app

    assert "còpia de seguretat amb les teves dades" not in crea_app().test_client().get("/").get_data(as_text=True)


def test_restaurador_llista_previsualitza_i_restaura():
    from canconer import basedades as bd, copies, exemple
    from canconer.web import crea_app

    exemple.crea_exemple()
    client = crea_app().test_client()
    r = client.post("/copies/nova")
    feta = r.headers["Location"].split("feta=")[1]
    html = client.get("/copies").get_data(as_text=True)
    assert feta in html and "Feta a mà" in html and "1 cançoner, 4 cançons" in html
    d = client.get(f"/api/copies/{feta}").get_json()
    assert d["canconers"][0]["titol"] == "Cançoner d'exemple" and len(d["canconers"][0]["cancons"]) == 4
    assert client.get("/api/copies/no-existeix.zip").status_code == 404
    bd.crea_canconer("Nou després de la còpia")
    r = client.post("/copies/restaura", data={"copia": feta})
    assert "restaurada=" in r.headers["Location"]
    assert [k["titol"] for k in bd.llista_canconers()] == ["Cançoner d'exemple"]
    assert any(copies.descripcio(c)["motiu"] == "Abans de restaurar una còpia" for c in copies.llista())


def test_identitat_del_servidor():
    from canconer import basedades as bd
    from canconer.web import crea_app

    d = crea_app().test_client().get("/api/identitat").get_json()
    assert d["app"] == "canconers" and d["dades"] == str(bd.DIRECTORI.resolve()) and isinstance(d["pid"], int)
