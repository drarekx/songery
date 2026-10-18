"""Llançador de l'app d'escriptori (Cançoners.app).

En obrir l'app:
  - les dades es desen a ~/Library/Application Support/Cançoners
  - s'engega el servidor en un port local lliure
  - s'obre el navegador (Chrome si hi és, perquè és el mateix motor que genera el PDF)
  - apareix una icona a la barra de menú per tornar a obrir-lo, anar a les dades o sortir
  - es comprova (en obrir-la i cada dia) si hi ha una versió nova; si n'hi ha, es pregunta si
    es vol instal·lar. Abans d'actualitzar es fa sempre una còpia de seguretat de les dades.
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
CONFIGURACIO = DADES / "configuracio.json"
CADA_QUANT = 24 * 3600  # comprovació de versions noves (segons)


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


def configuracio() -> dict:
    try:
        return json.loads(CONFIGURACIO.read_text())
    except (OSError, ValueError):
        return {}


def desa_configuracio(**canvis) -> None:
    DADES.mkdir(parents=True, exist_ok=True)
    CONFIGURACIO.write_text(json.dumps({**configuracio(), **canvis}, indent=2))


def tria_fitxer(carpeta: Path) -> Path | None:
    """Diàleg de macOS per triar un .zip (None si es cancel·la)."""
    script = (f'POSIX path of (choose file with prompt "Tria la còpia de seguretat que vols restaurar:" '
              f'of type {{"zip", "public.zip-archive"}} default location (POSIX file "{carpeta}"))')
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return Path(r.stdout.strip()) if r.returncode == 0 and r.stdout.strip() else None


def main() -> None:
    oberta = instancia_oberta()
    if oberta:
        obre_navegador(oberta)
        return

    url = engega_servidor()
    obre_navegador(url)

    import rumps

    from canconer import actualitzacions, copies, pdf

    versio = actualitzacions.versio_actual()

    class App(rumps.App):
        def __init__(self):
            icona = recurs("icona-menu.png")
            super().__init__(NOM, icon=icona if Path(icona).exists() else None, template=True,
                             title=None if Path(icona).exists() else "♪", quit_button=None)
            self.item_versio = rumps.MenuItem(f"Cançoners {versio}")
            self.menu = [
                rumps.MenuItem("Obre Cançoners", callback=lambda _: obre_navegador(url)),
                rumps.MenuItem("Obre la carpeta de dades", callback=lambda _: subprocess.Popen(["open", str(DADES)])),
                None,
                self.item_versio,
                rumps.MenuItem("Cerca actualitzacions…", callback=lambda _: self.cerca(manual=True)),
                rumps.MenuItem("Fes una còpia de seguretat ara", callback=self.copia_ara),
                rumps.MenuItem("Restaura una còpia…", callback=self.restaura),
                None,
                rumps.MenuItem("Surt", callback=self.surt),
            ]
            # La consulta a GitHub es fa en un fil a part; el resultat es mostra des del fil
            # principal (rumps només pot obrir diàlegs des d'aquí).
            self.resultat = None
            self.cercant = False
            rumps.Timer(self.mostra_resultat, 1).start()
            rumps.Timer(lambda _: self.cerca(manual=False), CADA_QUANT).start()
            primera = threading.Timer(8, lambda: self.cerca(manual=False))
            primera.daemon = True
            primera.start()

        # -------------------------------------------------------- Actualitzacions

        def cerca(self, manual: bool) -> None:
            if self.cercant:
                return
            self.cercant = True

            def fes():
                try:
                    self.resultat = ("nova", actualitzacions.comprova(), manual)
                except OSError as e:
                    self.resultat = ("error", str(e), manual)
                finally:
                    self.cercant = False
            threading.Thread(target=fes, daemon=True).start()

        def mostra_resultat(self, _) -> None:
            if not self.resultat:
                return
            tipus, dades, manual = self.resultat
            self.resultat = None
            if tipus == "error":
                if manual:
                    rumps.alert("No s'ha pogut comprovar", f"No es pot connectar amb GitHub.\n\n{dades}")
                return
            if not dades:
                self.item_versio.title = f"Cançoners {versio}"
                if manual:
                    rumps.alert("Cançoners està al dia", f"Tens l'última versió ({versio}).")
                return
            self.item_versio.title = f"Cançoners {versio} · hi ha la {dades['versio']}"
            # Avisa un sol cop per versió (si no és que l'usuari ho demana).
            if not manual and configuracio().get("avisada") == dades["versio"]:
                return
            desa_configuracio(avisada=dades["versio"])
            notes = dades["notes"].strip()
            text = (f"Tens la {versio}. Abans d'actualitzar es farà una còpia de seguretat de les teves dades."
                    + (f"\n\n{notes[:600]}" if notes else ""))
            if rumps.alert(f"Hi ha una versió nova: {dades['versio']}", text, ok="Actualitza ara", cancel="Més tard"):
                self.actualitza()

        def actualitza(self) -> None:
            """Còpia de seguretat i, si ha anat bé, l'instal·lador: baixa l'última versió, en
            comprova la signatura, tanca aquesta i obre la nova (si la nova no arrenca, torna a l'anterior)."""
            if pdf._bloqueig.locked():
                rumps.alert("Ara no", "S'està generant un PDF. Torna-ho a provar d'aquí a un moment.")
                return
            try:
                copia = copies.fes_copia(versio, "abans-d-actualitzar")
            except Exception as e:  # noqa: BLE001 - qualsevol error atura l'actualització
                rumps.alert("No s'ha actualitzat", f"No s'ha pogut fer la còpia de seguretat, així que no s'ha tocat res.\n\n{e}")
                return
            try:
                rumps.notification(NOM, "Actualitzant…", f"Còpia de seguretat feta: {copia.name}. L'app es tornarà a obrir sola.")
            except Exception:  # noqa: BLE001 - la notificació és només informativa
                pass
            FITXER_SERVIDOR.unlink(missing_ok=True)
            registre = DADES / "actualitzacio.log"
            with open(registre, "ab") as sortida:
                subprocess.Popen(["/bin/bash", "-c", f"curl -fsSL {INSTAL_LADOR} | bash"],
                                 stdout=sortida, stderr=subprocess.STDOUT, start_new_session=True)

        # -------------------------------------------------------- Còpies de seguretat

        def copia_ara(self, _) -> None:
            try:
                copia = copies.fes_copia(versio, "manual")
            except Exception as e:  # noqa: BLE001
                rumps.alert("No s'ha pogut fer la còpia", str(e))
                return
            if rumps.alert("Còpia de seguretat feta", f"S'ha desat {copia.name}. Es conserven les últimes {copies.CONSERVADES}.",
                           ok="D'acord", cancel="Mostra-la"):
                return
            subprocess.Popen(["open", "-R", str(copia)])

        def restaura(self, _) -> None:
            fitxer = tria_fitxer(copies.directori())
            if not fitxer:
                return
            if not rumps.alert("Restaurar la còpia?", f"Les dades tornaran a l'estat de {fitxer.name}. "
                               "Abans es farà una còpia de l'estat actual, per si de cas.\n\n"
                               "Tanca les pestanyes de Cançoners del navegador abans de continuar.",
                               ok="Restaura", cancel="Cancel·la"):
                return
            try:
                abans = copies.restaura(fitxer, versio)
            except Exception as e:  # noqa: BLE001
                rumps.alert("No s'ha pogut restaurar", str(e))
                return
            rumps.alert("Còpia restaurada", f"L'estat anterior s'ha desat a {abans.name}.")
            obre_navegador(url)

        def surt(self, _):
            FITXER_SERVIDOR.unlink(missing_ok=True)
            rumps.quit_application()

    App().run()


if __name__ == "__main__":
    main()
