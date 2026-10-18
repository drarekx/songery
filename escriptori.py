"""Llançador de l'app d'escriptori (Cançoners.app).

En obrir l'app:
  - les dades es desen a ~/Library/Application Support/Cançoners
  - s'engega el servidor en un port local lliure
  - s'obre el navegador (Chrome si hi és, perquè és el mateix motor que genera el PDF)
  - apareix una icona a la barra de menú per tornar a obrir-lo, anar a les dades o sortir
Si l'app ja està oberta, només s'obre una finestra nova del navegador.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

NOM = "Cançoners"
DADES = Path.home() / "Library" / "Application Support" / NOM
os.environ.setdefault("CANCONER_DADES", str(DADES))  # abans d'importar l'aplicació

FITXER_SERVIDOR = DADES / "servidor.json"
INSTAL_LADOR = "https://raw.githubusercontent.com/drarekx/songery/main/install.sh"
CHROME = "/Applications/Google Chrome.app"


def recurs(nom: str) -> str:
    """Camí d'un fitxer de recursos, tant en desenvolupament com dins de l'app."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base / "eines" / "app" / nom)


def obre_navegador(url: str) -> None:
    if os.environ.get("CANCONER_NO_OBRIS"):  # per a proves automàtiques
        return
    if Path(CHROME).exists():
        subprocess.Popen(["open", "-a", CHROME, url])
    else:
        subprocess.Popen(["open", url])


def instancia_oberta() -> str | None:
    """URL de l'app si ja n'hi ha una altra d'oberta (i respon)."""
    try:
        url = json.loads(FITXER_SERVIDOR.read_text())["url"]
        with urllib.request.urlopen(url, timeout=2):
            return url
    except (OSError, ValueError, KeyError):
        return None


def port_lliure(preferit: int = 5050) -> int:
    for port in (preferit, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
            except OSError:
                continue
    raise RuntimeError("No hi ha cap port lliure")


def engega_servidor() -> str:
    from werkzeug.serving import make_server

    from canconer import motor_pdf
    from canconer.web import crea_app

    port = port_lliure()
    servidor = make_server("127.0.0.1", port, crea_app(), threaded=True)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    DADES.mkdir(parents=True, exist_ok=True)
    FITXER_SERVIDOR.write_text(json.dumps({"url": url, "pid": os.getpid()}))
    motor_pdf.prepara_en_segon_pla()  # si no hi ha Chrome/Edge, baixa el motor de PDF ara
    return url


def main() -> None:
    oberta = instancia_oberta()
    if oberta:
        obre_navegador(oberta)
        return

    url = engega_servidor()
    obre_navegador(url)

    import rumps

    class App(rumps.App):
        def __init__(self):
            icona = recurs("icona-menu.png")
            super().__init__(NOM, icon=icona if Path(icona).exists() else None, template=True,
                             title=None if Path(icona).exists() else "♪", quit_button=None)
            self.menu = [
                rumps.MenuItem("Obre Cançoners", callback=lambda _: obre_navegador(url)),
                rumps.MenuItem("Obre la carpeta de dades", callback=lambda _: subprocess.Popen(["open", str(DADES)])),
                rumps.MenuItem("Actualitza a l'última versió", callback=self.actualitza),
                None,
                rumps.MenuItem("Surt", callback=self.surt),
            ]

        def actualitza(self, _):
            """Torna a executar l'instal·lador: baixa l'última versió, tanca aquesta i obre la nova."""
            if not rumps.alert("Actualitzar Cançoners", "Es baixarà l'última versió i l'app es tornarà a obrir. "
                               "Les teves dades no es toquen.", ok="Actualitza", cancel="Cancel·la"):
                return
            FITXER_SERVIDOR.unlink(missing_ok=True)
            subprocess.Popen(["/bin/bash", "-c", f"curl -fsSL {INSTAL_LADOR} | bash"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)

        def surt(self, _):
            FITXER_SERVIDOR.unlink(missing_ok=True)
            rumps.quit_application()

    App().run()


if __name__ == "__main__":
    main()
