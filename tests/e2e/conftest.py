"""Tests de punta a punta: l'app de veritat (app.py amb dades temporals) i un Chromium invisible
controlat amb DevTools (el mateix client que fa servir el motor de PDF). Proven el que només es pot
provar en un navegador: gestos del ratolí, el porta-retalls, el zoom, menús...

Si no hi ha cap Chromium (Chrome, Edge o el que baixa el motor de PDF), se salten.
Per no executar-los: pytest -m "not e2e".
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import websocket

from canconer import motor_pdf

ARREL = Path(__file__).resolve().parents[2]


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: tests de punta a punta amb un navegador (més lents)")


def pytest_collection_modifyitems(items):
    for item in items:
        if "/e2e/" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)


def _port_lliure() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _espera_url(url: str, temps: float = 20) -> None:
    limit = time.time() + temps
    while time.time() < limit:
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"{url} no respon")


@pytest.fixture
def servidor(tmp_path):
    """L'app engegada amb una carpeta de dades buida. Torna l'adreça base (http://127.0.0.1:port)."""
    port = _port_lliure()
    entorn = {**os.environ, "CANCONER_DADES": str(tmp_path / "dades")}
    proces = subprocess.Popen([sys.executable, str(ARREL / "app.py"), "--port", str(port), "--sense-recarrega"],
                              cwd=ARREL, env=entorn, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        _espera_url(base + "/")
        yield base
    finally:
        proces.terminate()
        proces.wait(10)


def canconer_exemple(base: str) -> str:
    """Crea el cançoner d'exemple i en torna l'adreça de l'editor."""
    peticio = urllib.request.Request(base + "/canconer/exemple", method="POST")

    class SenseRedireccio(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    try:
        urllib.request.build_opener(SenseRedireccio).open(peticio)
    except urllib.error.HTTPError as e:
        return base + e.headers["Location"] if e.headers["Location"].startswith("/") else e.headers["Location"]
    raise RuntimeError("No s'ha creat el cançoner d'exemple")


class Pagina:
    """Una pestanya de Chromium: navegar, avaluar JavaScript i fer servir el ratolí de debò."""

    def __init__(self, sessio):
        self.s = sessio

    def obre(self, url: str, condicio: str = "document.readyState === 'complete'", temps: float = 20) -> None:
        self.s.crida("Page.navigate", {"url": url})
        time.sleep(0.2)
        self.espera(condicio, temps)

    def avalua(self, js: str):
        r = self.s.crida("Runtime.evaluate", {"expression": js, "awaitPromise": True, "returnByValue": True})
        if "exceptionDetails" in r:
            raise AssertionError(f"Error de JavaScript: {r['exceptionDetails'].get('exception', {}).get('description') or r['exceptionDetails']}")
        return r.get("result", {}).get("value")

    def espera(self, condicio: str, temps: float = 10) -> None:
        limit = time.time() + temps
        while time.time() < limit:
            if self.avalua(f"!!({condicio})"):
                return
            time.sleep(0.1)
        raise AssertionError(f"No s'ha complert a temps: {condicio}")

    def _ratoli(self, tipus: str, x: float, y: float, boto: str = "none", botons: int = 0, **extra) -> None:
        self.s.crida("Input.dispatchMouseEvent", {"type": tipus, "x": x, "y": y, "button": boto, "buttons": botons, **extra})

    def arrossega(self, x1: float, y1: float, x2: float, y2: float, passos: int = 10) -> None:
        self._ratoli("mouseMoved", x1, y1)
        self._ratoli("mousePressed", x1, y1, "left", 1, clickCount=1)
        for i in range(1, passos + 1):
            self._ratoli("mouseMoved", x1 + (x2 - x1) * i / passos, y1 + (y2 - y1) * i / passos, "left", 1)
            time.sleep(0.02)
        self._ratoli("mouseReleased", x2, y2, "left", 0, clickCount=1)

    def clic_dret(self, x: float, y: float) -> None:
        self._ratoli("mouseMoved", x, y)
        self._ratoli("mousePressed", x, y, "right", 2, clickCount=1)
        self._ratoli("mouseReleased", x, y, "right", 0, clickCount=1)


@pytest.fixture
def pagina():
    executable = motor_pdf.troba_navegador()
    if not executable:
        pytest.skip("No hi ha cap Chromium per als tests de punta a punta")
    perfil = Path(tempfile.mkdtemp(prefix="canconer-e2e-"))
    opcions = [executable, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
               "--mute-audio", "--disable-extensions", "--remote-debugging-port=0", "--window-size=1500,950",
               f"--user-data-dir={perfil}", "about:blank"]
    if "chrome-headless-shell" in executable:
        opcions.remove("--headless=new")
    proces = subprocess.Popen(opcions, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        port = motor_pdf._llegeix_port(perfil, proces)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as r:
            objectiu = next(t for t in json.load(r) if t.get("type") == "page")
        ws = websocket.create_connection(objectiu["webSocketDebuggerUrl"], timeout=30, suppress_origin=True)
        sessio = motor_pdf._Sessio(ws)
        sessio.crida("Page.enable")
        sessio.crida("Runtime.enable")
        yield Pagina(sessio)
        ws.close()
    finally:
        proces.kill()
