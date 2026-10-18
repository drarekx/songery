"""Generació de PDF amb un Chromium local, sense Docker.

Fa servir el Chrome, Edge, Brave o Chromium que hi hagi al Mac en mode invisible (headless) i el
controla amb el protocol de DevTools: obre la pàgina d'impressió, espera que estigui dibuixada i la
desa en PDF (Page.printToPDF). És el mateix motor que fa servir Gotenberg, i el mateix que el
navegador on s'edita: el PDF és idèntic al que es veu a l'editor.

Si no hi ha cap navegador compatible, es baixa una sola vegada el «Chrome headless shell» oficial
de Google (Chrome for Testing) a la carpeta de dades.
"""

from __future__ import annotations

import base64
import io
import json
import os
import platform
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

import websocket

from .actualitzacions import context_ssl

NAVEGADORS_MAC = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Vivaldi.app/Contents/MacOS/Vivaldi",
]
NAVEGADORS_LINUX = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"]
VERSIONS_CFT = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"

_bloqueig = threading.Lock()
_estat = {"preparant": False, "error": ""}


class MotorNoDisponible(RuntimeError):
    pass


def _directori_motor() -> Path:
    from . import basedades

    return basedades.DIRECTORI / "motor-pdf"


def _shell_descarregat() -> Path | None:
    for cami in _directori_motor().glob("chrome-headless-shell-*/chrome-headless-shell"):
        if os.access(cami, os.X_OK):
            return cami
    return None


def troba_navegador() -> str | None:
    """Executable de Chromium que es pot fer servir (variable CANCONER_NAVEGADOR, instal·lat o descarregat)."""
    propi = os.environ.get("CANCONER_NAVEGADOR")
    if propi:
        return propi if os.path.exists(propi) else None
    candidats = [*NAVEGADORS_MAC, *(os.path.expanduser("~" + c) for c in NAVEGADORS_MAC)]
    for cami in candidats:
        if os.access(cami, os.X_OK):
            return cami
    for nom in NAVEGADORS_LINUX:
        trobat = shutil.which(nom)
        if trobat:
            return trobat
    shell = _shell_descarregat()
    return str(shell) if shell else None


def descarrega_motor() -> str:
    """Baixa el Chrome headless shell de Google (uns 90 MB) a la carpeta de dades."""
    plataforma = {("Darwin", "arm64"): "mac-arm64", ("Darwin", "x86_64"): "mac-x64",
                  ("Linux", "x86_64"): "linux64"}.get((platform.system(), platform.machine()))
    if not plataforma:
        raise MotorNoDisponible("No hi ha cap navegador Chrome o Edge i aquest sistema no permet baixar-ne un.")
    with urllib.request.urlopen(VERSIONS_CFT, timeout=30, context=context_ssl()) as r:
        baixades = json.load(r)["channels"]["Stable"]["downloads"]["chrome-headless-shell"]
    url = next(d["url"] for d in baixades if d["platform"] == plataforma)
    desti = _directori_motor()
    desti.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=600, context=context_ssl()) as r:
        dades = r.read()
    with zipfile.ZipFile(io.BytesIO(dades)) as z:
        z.extractall(desti)
    shell = _shell_descarregat()
    if not shell:
        # zipfile no conserva els permisos d'execució: es restableixen.
        for f in desti.rglob("*"):
            if f.is_file() and (f.name.startswith("chrome-headless-shell") or f.suffix in ("", ".dylib")):
                f.chmod(0o755)
        shell = _shell_descarregat()
    if not shell:
        raise MotorNoDisponible("No s'ha pogut preparar el motor de PDF descarregat.")
    if platform.system() == "Darwin":
        subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(desti)], capture_output=True)
    return str(shell)


def prepara_en_segon_pla() -> None:
    """Si no hi ha cap navegador, comença a baixar el motor (perquè el primer PDF no hagi d'esperar)."""
    if troba_navegador() or _estat["preparant"]:
        return

    def feina():
        _estat["preparant"] = True
        try:
            with _bloqueig:
                if not troba_navegador():
                    descarrega_motor()
        except Exception as e:  # noqa: BLE001 — es mostra a la interfície quan es demani un PDF
            _estat["error"] = str(e)
        finally:
            _estat["preparant"] = False

    threading.Thread(target=feina, daemon=True).start()


def estat() -> dict:
    return {"navegador": troba_navegador(), **_estat}


# ---------------------------------------------------------------- Conversió amb DevTools


class _Sessio:
    def __init__(self, ws):
        self.ws = ws
        self.n = 0

    def crida(self, metode: str, params: dict | None = None, temps: float = 60) -> dict:
        self.n += 1
        identificador = self.n
        self.ws.send(json.dumps({"id": identificador, "method": metode, "params": params or {}}))
        limit = time.time() + temps
        while time.time() < limit:
            self.ws.settimeout(max(0.1, limit - time.time()))
            missatge = json.loads(self.ws.recv())
            if missatge.get("id") == identificador:
                if "error" in missatge:
                    raise MotorNoDisponible(f"El navegador ha retornat un error: {missatge['error'].get('message')}")
                return missatge.get("result", {})
        raise MotorNoDisponible(f"El navegador no ha respost a temps ({metode}).")


def _llegeix_port(directori: Path, proces: subprocess.Popen, temps: float = 20) -> int:
    fitxer = directori / "DevToolsActivePort"
    limit = time.time() + temps
    while time.time() < limit:
        if proces.poll() is not None:
            raise MotorNoDisponible("El navegador s'ha tancat en engegar-lo.")
        if fitxer.exists() and fitxer.read_text().strip():
            return int(fitxer.read_text().split()[0])
        time.sleep(0.05)
    raise MotorNoDisponible("El navegador no s'ha engegat a temps.")


def converteix_url(url: str, mida: tuple[float, float], esperar: bool = True, temps: float = 90) -> bytes:
    """Obre la URL en un Chromium invisible i la desa en PDF (mida en polzades)."""
    executable = troba_navegador()
    if not executable:
        with _bloqueig:
            executable = troba_navegador() or descarrega_motor()
    perfil = Path(tempfile.mkdtemp(prefix="canconer-pdf-"))
    opcions = [executable, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
               "--hide-scrollbars", "--mute-audio", "--disable-extensions", "--remote-debugging-port=0",
               f"--user-data-dir={perfil}", url]
    if "chrome-headless-shell" in executable:
        opcions.remove("--headless=new")  # el shell ja és sempre invisible
    proces = subprocess.Popen(opcions, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        port = _llegeix_port(perfil, proces)
        pagina = None
        limit = time.time() + 10
        while not pagina and time.time() < limit:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as r:
                pagina = next((t for t in json.load(r) if t.get("type") == "page"), None)
            if not pagina:
                time.sleep(0.1)
        if not pagina:
            raise MotorNoDisponible("El navegador no ha obert la pàgina.")
        ws = websocket.create_connection(pagina["webSocketDebuggerUrl"], timeout=10, suppress_origin=True)
        sessio = _Sessio(ws)
        condicio = ("window.paginesLlestes === true" if esperar else
                    "document.readyState === 'complete' && document.fonts.status === 'loaded'")
        limit = time.time() + temps
        while True:
            resultat = sessio.crida("Runtime.evaluate", {"expression": condicio, "returnByValue": True})
            if resultat.get("result", {}).get("value") is True:
                break
            if time.time() > limit:
                raise MotorNoDisponible("La pàgina d'impressió no s'ha acabat de dibuixar a temps.")
            time.sleep(0.15)
        pdf = sessio.crida("Page.printToPDF", {
            "paperWidth": mida[0], "paperHeight": mida[1],
            "marginTop": 0, "marginBottom": 0, "marginLeft": 0, "marginRight": 0,
            "printBackground": True, "preferCSSPageSize": True,
        }, temps=180)
        ws.close()
        return base64.b64decode(pdf["data"])
    finally:
        proces.terminate()
        try:
            proces.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proces.kill()
        shutil.rmtree(perfil, ignore_errors=True)
