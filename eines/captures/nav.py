"""Chromium invisible controlat amb DevTools per fer captures i vídeos de Cançoners."""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket

ARREL = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ARREL))
from canconer import motor_pdf  # noqa: E402

# fes.sh engega el servidor de demostració i defineix aquestes variables.
BASE = os.environ.get("CAPTURES_URL", "http://127.0.0.1:5391")
TREBALL = Path(os.environ.get("CAPTURES_TREBALL", "/tmp/canconer-captures"))  # fotogrames i ids dels cançoners
IMATGES = ARREL / "docs" / "imatges"
VIDEOS = ARREL / "docs" / "videos"
LLEST = "document.querySelector('.pagina-editor') && document.fonts.status === 'loaded'"


class Nav:
    def __init__(self, ample=1440, alt=900, escala=2):
        self.ample, self.alt = ample, alt
        self.perfil = Path(tempfile.mkdtemp(prefix="canconer-captures-"))
        self.proces = subprocess.Popen(
            [motor_pdf.troba_navegador(), "--headless=new", "--no-first-run", "--no-default-browser-check",
             "--hide-scrollbars", "--mute-audio", "--disable-extensions", "--remote-debugging-port=0",
             f"--window-size={ample},{alt}", f"--user-data-dir={self.perfil}", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        port = motor_pdf._llegeix_port(self.perfil, self.proces)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as r:
            objectiu = next(t for t in json.load(r) if t.get("type") == "page")
        self.ws = websocket.create_connection(objectiu["webSocketDebuggerUrl"], timeout=60, suppress_origin=True)
        self.s = motor_pdf._Sessio(self.ws)
        self.s.crida("Page.enable")
        self.s.crida("Runtime.enable")
        self.s.crida("Emulation.setDeviceMetricsOverride",
                     {"width": ample, "height": alt, "deviceScaleFactor": escala, "mobile": False})
        # Sense la franja de desenvolupament ni el peu amb la carpeta de dades.
        self.s.crida("Page.addScriptToEvaluateOnNewDocument", {"source": """
          document.addEventListener('DOMContentLoaded', () => {
            const e = document.createElement('style');
            e.textContent = 'body > [role=note], body > footer { display: none !important; }';
            document.head.appendChild(e);
          });"""})

    def tanca(self):
        try:
            self.ws.close()
        finally:
            self.proces.kill()

    def avalua(self, js):
        r = self.s.crida("Runtime.evaluate", {"expression": js, "awaitPromise": True, "returnByValue": True})
        if "exceptionDetails" in r:
            raise RuntimeError(str(r["exceptionDetails"].get("exception", {}).get("description") or r["exceptionDetails"]))
        return r.get("result", {}).get("value")

    def espera(self, condicio, temps=15):
        limit = time.time() + temps
        while time.time() < limit:
            if self.avalua(f"!!({condicio})"):
                return
            time.sleep(0.1)
        raise RuntimeError(f"No s'ha complert: {condicio}")

    def obre(self, url, condicio="document.readyState === 'complete'", temps=25):
        self.s.crida("Page.navigate", {"url": url if url.startswith("http") else BASE + url})
        time.sleep(0.3)
        self.espera(condicio, temps)

    def captura(self, fitxer, retall=None):
        params = {"format": "png"}
        if retall:
            x, y, w, h = retall
            params["clip"] = {"x": x, "y": y, "width": w, "height": h, "scale": 1}
        dades = self.s.crida("Page.captureScreenshot", params)["data"]
        Path(fitxer).write_bytes(base64.b64decode(dades))

    # --- ratolí i teclat de debò ---
    def ratoli(self, tipus, x, y, boto="none", botons=0, **extra):
        self.s.crida("Input.dispatchMouseEvent", {"type": tipus, "x": x, "y": y, "button": boto, "buttons": botons, **extra})

    def clic(self, x, y, vegades=1):
        self.ratoli("mouseMoved", x, y)
        for n in range(1, vegades + 1):
            self.ratoli("mousePressed", x, y, "left", 1, clickCount=n)
            self.ratoli("mouseReleased", x, y, "left", 0, clickCount=n)

    def centre(self, selector_js):
        """Centre de l'element que torna l'expressió JavaScript."""
        return self.avalua(f"(() => {{ const r = ({selector_js}).getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }})()")

    def escriu(self, text):
        self.s.crida("Input.insertText", {"text": text})

    def tecla(self, tecla, codi=None, vk=0, modificadors=0):
        for tipus in ("keyDown", "keyUp"):
            self.s.crida("Input.dispatchKeyEvent", {"type": tipus, "key": tecla, "code": codi or tecla,
                                                    "windowsVirtualKeyCode": vk, "modifiers": modificadors})


def desa_id(nom, valor):
    (TREBALL / f"id-{nom}.txt").write_text(valor)


def llegeix_id(nom):
    return (TREBALL / f"id-{nom}.txt").read_text().strip()


# Expressions JavaScript per trobar botons pel text o pel títol.
def boto(text):
    return f"[...document.querySelectorAll('button,a')].find(b=>b.offsetParent && b.textContent.trim()==={text!r})"


def boto_conte(text):
    return f"[...document.querySelectorAll('button,a')].find(b=>b.offsetParent && b.textContent.includes({text!r}))"


def boto_titol(text):
    return f"[...document.querySelectorAll('button')].find(b=>(b.title||b.getAttribute('aria-label')||'').startsWith({text!r}))"


# La creu del panell flotant «Acords de la cançó» (n'hi ha d'altres amb el mateix títol).
TANCA_PANELL_ACORDS = ("[...document.querySelectorAll('button')].filter(b=>(b.title||b.getAttribute('aria-label')||'')==='Tanca')"
                       ".find(b=>b.offsetParent && b.getBoundingClientRect().top < 260 && b.getBoundingClientRect().left < 900)")
RECTANGLE = "(() => {{ const r = document.querySelector({sel!r}).getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }})()"
