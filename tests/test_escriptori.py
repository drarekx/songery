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
