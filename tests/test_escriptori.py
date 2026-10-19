"""App d'escriptori: el port no va canviant i l'app s'obre en una finestra pròpia si es pot."""

from __future__ import annotations

import importlib
import json
import socket
import stat

import pytest


@pytest.fixture
def escriptori(tmp_path, monkeypatch):
    monkeypatch.setenv("CANCONER_DADES", str(tmp_path))
    modul = importlib.import_module("escriptori")
    monkeypatch.setattr(modul, "DADES", tmp_path)
    monkeypatch.setattr(modul, "CONFIGURACIO", tmp_path / "configuracio.json")
    monkeypatch.delenv("CANCONER_NO_OBRIS", raising=False)
    return modul


def _ocupa(port: int) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", port))
    s.listen()
    return s


def _lliure() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_el_port_de_l_ultima_vegada_si_es_lliure(escriptori):
    desat = _lliure()
    assert escriptori.tria_port(desat) == (desat, True)


def test_si_esta_ocupat_un_dels_fixos_i_mai_un_aleatori_desat(escriptori, monkeypatch):
    fixos = [_lliure(), _lliure(), _lliure()]
    monkeypatch.setattr(escriptori, "PORTS", tuple(fixos))
    ocupats = [_ocupa(fixos[0])]
    try:
        assert escriptori.tria_port(None) == (fixos[1], True)  # cançoner nou: el primer fix lliure
        ocupats.append(_ocupa(fixos[1]))
        desat = _lliure()
        ocupats.append(_ocupa(desat))
        assert escriptori.tria_port(desat) == (fixos[2], True)
        ocupats.append(_ocupa(fixos[2]))
        port, desa = escriptori.tria_port(desat)  # tots ocupats: un d'aleatori, que no es desa
        assert port not in fixos + [desat] and desa is False
    finally:
        for s in ocupats:
            s.close()


def test_s_obre_en_una_finestra_propia_o_al_navegador(escriptori, monkeypatch, tmp_path):
    crides = []
    monkeypatch.setattr(escriptori.subprocess, "Popen", lambda ordre, **_: crides.append(ordre))
    chrome = tmp_path / "Google Chrome"
    chrome.write_text("#!/bin/sh\n")
    chrome.chmod(chrome.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setattr(escriptori, "NAVEGADORS_APP", [str(chrome)])
    escriptori.obre_navegador("http://127.0.0.1:48650/")
    assert crides[-1][:2] == [str(chrome), "--app=http://127.0.0.1:48650/"]
    escriptori.desa_configuracio(finestra="navegador")  # l'usuari prefereix el navegador normal
    escriptori.obre_navegador("http://127.0.0.1:48650/")
    assert crides[-1] == ["open", "http://127.0.0.1:48650/"]
    monkeypatch.setattr(escriptori, "NAVEGADORS_APP", [str(tmp_path / "no-hi-és")])
    escriptori.desa_configuracio(finestra="app")
    escriptori.obre_navegador("http://127.0.0.1:48650/")
    assert crides[-1] == ["open", "http://127.0.0.1:48650/"]  # sense Chrome, Edge ni Brave
    assert json.loads((tmp_path / "configuracio.json").read_text())["finestra"] == "app"


def _servidor(resposta: dict | None):
    """Servidor HTTP de prova que respon /api/identitat amb `resposta` (None: 404, com una versió antiga
    o un altre programa)."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Gestor(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if resposta is None or self.path != "/api/identitat":
                self.send_response(404)
                self.end_headers()
                return
            cos = json.dumps(resposta).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(cos)

        def log_message(self, *a):
            pass

    s = HTTPServer(("127.0.0.1", 0), Gestor)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def test_no_es_confon_amb_un_altre_servidor_al_mateix_port(escriptori, tmp_path, monkeypatch):
    """Si a l'adreça desada hi respon un altre servidor (un altre programa, o un Cançoners amb unes altres
    dades), l'app no s'hi connecta: arrenca la seva."""
    monkeypatch.setattr(escriptori, "FITXER_SERVIDOR", tmp_path / "servidor.json")
    pid = 4242
    casos = [
        ({"app": "canconers", "dades": str(tmp_path), "pid": pid}, True),  # és ella
        ({"app": "canconers", "dades": "/una/altra/carpeta", "pid": pid}, False),  # unes altres dades
        ({"app": "canconers", "dades": str(tmp_path), "pid": 1}, False),  # un altre procés
        (None, False),  # un altre programa (i el procés desat no és l'app)
    ]
    monkeypatch.setattr(escriptori, "DADES", tmp_path)
    for resposta, nostra in casos:
        s = _servidor(resposta)
        url = f"http://127.0.0.1:{s.server_port}/"
        escriptori.FITXER_SERVIDOR.write_text(json.dumps({"url": url, "pid": pid}))
        assert (escriptori.instancia_oberta() == url) is nostra, resposta
        s.shutdown()
    # Una versió antiga de l'app (sense /api/identitat) que encara és oberta sí que es reaprofita.
    monkeypatch.setattr(escriptori, "es_l_app", lambda p: p == pid)
    s = _servidor(None)
    url = f"http://127.0.0.1:{s.server_port}/"
    escriptori.FITXER_SERVIDOR.write_text(json.dumps({"url": url, "pid": pid}))
    assert escriptori.instancia_oberta() == url
    s.shutdown()
