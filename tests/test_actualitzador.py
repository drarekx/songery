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
    with pytest.raises(actualitzador.ErrorActualitzacio, match="no és vàlid"):
        actualitzador.verifica(zip2, tmp_path / "dolenta")


def test_baixada_ignora_una_compressio_http_falsa(tmp_path):
    """Una xarxa que marca la resposta com a gzip sense ser-ho donava «Error -3 while decompressing
    data: incorrect header check». Ara el paquet es desa tal com arriba i se'n comprova la mida."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    import requests

    from canconer import actualitzador

    contingut = b"PK\x03\x04" + bytes(range(256)) * 400

    class Servidor(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Encoding", "gzip")  # mentida: no està comprimit
            self.send_header("Content-Length", str(len(contingut)))
            self.end_headers()
            self.wfile.write(contingut)

        def log_message(self, *a):
            pass

    servidor = HTTPServer(("127.0.0.1", 0), Servidor)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{servidor.server_port}/Canconers.zip"
    try:
        with pytest.raises(requests.exceptions.ContentDecodingError):  # el que passava abans
            with requests.get(url, stream=True) as r:
                for _ in r.iter_content(1024):
                    pass
        desti = tmp_path / "Canconers.zip"
        actualitzador.baixa(url, desti, len(contingut))
        assert desti.read_bytes() == contingut
        with pytest.raises(actualitzador.ErrorActualitzacio):
            actualitzador.baixa(url, tmp_path / "b.zip", len(contingut) + 1)
    finally:
        servidor.shutdown()
