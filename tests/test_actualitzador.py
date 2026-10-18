"""Actualització des de l'app amb el progrés a la web."""
import subprocess
import sys
from pathlib import Path

import pytest

from canconer import actualitzador
from canconer.web import crea_app

APP = Path(__file__).resolve().parent.parent / "dist" / "Cançoners.app"


@pytest.fixture
def client():
    app = crea_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_en_desenvolupament_no_s_actualitza_sola(client):
    assert actualitzador.app_actual() is None
    assert "git pull" in client.get("/actualitzacio").get_data(as_text=True)
    r = client.post("/api/actualitzacio/inicia")
    assert r.status_code == 400
    assert client.get("/api/actualitzacio/estat").get_json()["fase"] is None


def test_l_app_es_detecta_dins_del_paquet(monkeypatch, tmp_path):
    executable = tmp_path / "Apps" / "Cançoners.app" / "Contents" / "MacOS" / "Canconers"
    executable.parent.mkdir(parents=True)
    executable.write_text("")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    assert actualitzador.app_actual() == tmp_path / "Apps" / "Cançoners.app"
    assert actualitzador.pot_actualitzar() == (True, "")


def test_un_error_atura_l_actualitzacio_i_es_mostra(monkeypatch):
    monkeypatch.setattr(actualitzador, "pot_actualitzar", lambda: (True, ""))
    monkeypatch.setattr(actualitzador.copies, "fes_copia", lambda *a, **k: (_ for _ in ()).throw(OSError("disc ple")))
    actualitzador.estat.update(fase=None, error=None, fet=False)
    actualitzador._executa()
    assert actualitzador.estat["fase"] == "copia" and "disc ple" in actualitzador.estat["error"]
    assert not actualitzador.estat["sortir"]


def test_el_script_d_instal_lacio_es_valid(monkeypatch, tmp_path):
    monkeypatch.setattr(actualitzador, "app_actual", lambda: tmp_path / "Cançoners.app")
    script = actualitzador._escriu_script(tmp_path, tmp_path / "nova" / "Cançoners.app", "1.0.0")
    assert subprocess.run(["bash", "-n", str(script)]).returncode == 0
    assert "TeamIdentifier" not in script.read_text()  # la verificació es fa abans, a Python


@pytest.mark.skipif(not APP.exists(), reason="cal haver construït l'app (eines/app/construeix.sh)")
def test_verifica_la_signatura(tmp_path):
    zip_ = tmp_path / "Canconers.zip"
    subprocess.run(["ditto", "-c", "-k", "--keepParent", str(APP), str(zip_)], check=True)
    assert actualitzador.verifica(zip_, tmp_path / "bona").name == "Cançoners.app"
    # Una app retocada després de signar-la no passa la verificació.
    retocada = tmp_path / "retocada"
    subprocess.run(["ditto", "-x", "-k", str(zip_), str(retocada)], check=True)
    (retocada / "Cançoners.app" / "Contents" / "Resources" / "intrus.txt").write_text("hola")
    zip2 = tmp_path / "retocada.zip"
    subprocess.run(["ditto", "-c", "-k", "--keepParent", str(retocada / "Cançoners.app"), str(zip2)], check=True)
    with pytest.raises(actualitzador.ErrorActualitzacio, match="signatura"):
        actualitzador.verifica(zip2, tmp_path / "dolenta")
