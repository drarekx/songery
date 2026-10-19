"""Llançador de l'app d'escriptori (Cançoners.app).

En obrir l'app:
  - les dades es desen a ~/Library/Application Support/Cançoners
  - s'engega el servidor en un port local: el de l'última vegada o, si està ocupat, un de fix d'una
    llista curta (mai es desa un port aleatori, perquè l'adreça no vagi canviant)
  - s'obre en una finestra pròpia de Chrome, Edge o Brave (sense barra d'adreces; és el mateix motor
    que genera el PDF), o al navegador per defecte si no n'hi ha cap o si s'ha triat així
  - té icona al Dock (clicar-la obre Cançoners) i a la barra de menú (obrir-lo, anar a les dades
    o sortir)
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
import urllib.error
import urllib.request
from pathlib import Path

NOM = "Cançoners"
DADES = Path.home() / "Library" / "Application Support" / NOM
os.environ.setdefault("CANCONER_DADES", str(DADES))  # abans d'importar l'aplicació

FITXER_SERVIDOR = DADES / "servidor.json"
# Ports fixos, poc habituals: si el de l'última vegada està ocupat, es prova aquests en ordre.
PORTS = tuple(range(48650, 48660))
# Navegadors amb motor Chromium que poden obrir l'app en una finestra pròpia (--app).
NAVEGADORS_APP = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
CONFIGURACIO = DADES / "configuracio.json"
CADA_QUANT = 24 * 3600  # comprovació de versions noves (segons)


def recurs(nom: str) -> str:
    """Camí d'un fitxer de recursos, tant en desenvolupament com dins de l'app."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base / "eines" / "app" / nom)


def navegador_app() -> str | None:
    """Executable d'un navegador Chromium per obrir l'app en una finestra pròpia, si n'hi ha."""
    for cami in NAVEGADORS_APP:
        for candidat in (cami, str(Path.home()) + cami):
            if os.access(candidat, os.X_OK):
                return candidat
    return None


def obre_navegador(url: str) -> None:
    """Obre l'app: en una finestra pròpia (sense barra d'adreces) si hi ha Chrome, Edge o Brave i no
    s'ha triat el navegador normal; si no, al navegador per defecte."""
    if os.environ.get("CANCONER_NO_OBRIS"):  # per a proves automàtiques
        return
    navegador = navegador_app() if configuracio().get("finestra", "app") == "app" else None
    if navegador:
        # Si el navegador ja és obert, la instància que hi ha obre la finestra i aquesta es tanca.
        subprocess.Popen([navegador, f"--app={url}", "--window-size=1440,900"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    else:
        subprocess.Popen(["open", url])


def instancia_oberta() -> str | None:
    """URL de l'app si ja n'hi ha una altra d'oberta. Ha de ser aquesta mateixa app amb aquestes mateixes
    dades: si a l'adreça desada hi respon un altre servidor (un altre programa o un servidor de
    desenvolupament de Cançoners amb unes altres dades), no es fa servir i l'app arrenca la seva."""
    try:
        desat = json.loads(FITXER_SERVIDOR.read_text())
        url, pid = desat["url"], int(desat["pid"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    try:
        with urllib.request.urlopen(url + "api/identitat", timeout=2) as r:
            qui = json.loads(r.read())
        if qui.get("app") == "canconers" and qui.get("pid") == pid and Path(qui.get("dades", "")).resolve() == DADES.resolve():
            return url
        return None
    except urllib.error.HTTPError as e:
        # Una versió antiga (sense /api/identitat) que encara és oberta: és ella si el procés desat és
        # l'app de Cançoners.
        return url if e.code == 404 and es_l_app(pid) else None
    except (OSError, ValueError):
        return None


def es_l_app(pid: int) -> bool:
    """Si el procés és l'app de Cançoners (i no un altre programa que hagi reaprofitat el número)."""
    try:
        ordre = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True).stdout
    except OSError:
        return False
    return "/Contents/MacOS/Canconers" in ordre


def port_lliure(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def tria_port(desat: int | None) -> tuple[int, bool]:
    """Port per al servidor i si s'ha de desar: el de l'última vegada, si és lliure; si no, el primer
    lliure dels fixos (PORTS). Només si tots estan ocupats, un d'aleatori, que no es desa (la vegada
    següent es torna a provar el de sempre)."""
    for port in ([desat] if desat else []) + [p for p in PORTS if p != desat]:
        if port_lliure(port):
            return port, True
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1], False


def engega_servidor() -> tuple[str, bool]:
    """Engega el servidor. Torna l'adreça i si el port ha canviat respecte de l'última vegada."""
    from werkzeug.serving import make_server

    from canconer import motor_pdf
    from canconer.web import crea_app

    # El mateix port que l'última vegada: així l'adreça no canvia i, després d'actualitzar, la pàgina
    # s'hi reconnecta.
    desat = configuracio().get("port")
    port, desa = tria_port(desat if isinstance(desat, int) else None)
    if desa:
        desa_configuracio(port=port)
    servidor = make_server("127.0.0.1", port, crea_app(), threaded=True)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/"
    DADES.mkdir(parents=True, exist_ok=True)
    FITXER_SERVIDOR.write_text(json.dumps({"url": url, "pid": os.getpid()}))
    motor_pdf.prepara_en_segon_pla()  # si no hi ha Chrome/Edge, baixa el motor de PDF ara
    return url, desat is not None and port != desat


def configuracio() -> dict:
    try:
        return json.loads(CONFIGURACIO.read_text())
    except (OSError, ValueError):
        return {}


def desa_configuracio(**canvis) -> None:
    DADES.mkdir(parents=True, exist_ok=True)
    CONFIGURACIO.write_text(json.dumps({**configuracio(), **canvis}, indent=2))


def redirigeix_sortida() -> None:
    """Dins de l'app no hi ha consola: la sortida i els errors van a <dades>/canconers.log."""
    if not getattr(sys, "frozen", False):
        return
    DADES.mkdir(parents=True, exist_ok=True)
    registre = DADES / "canconers.log"
    try:
        if registre.exists() and registre.stat().st_size > 2_000_000:
            registre.replace(registre.with_suffix(".log.1"))
        fitxer = open(registre, "a", buffering=1, encoding="utf-8")
    except OSError:
        return
    sys.stdout = sys.stderr = fitxer


def main() -> None:
    redirigeix_sortida()
    oberta = instancia_oberta()
    if oberta:
        obre_navegador(oberta)
        return

    url, port_canviat = engega_servidor()
    # Després d'una actualització feta des de la web, la pàgina d'actualització s'hi reconnecta
    # sola: no cal obrir cap finestra nova (ho diu l'avís de la barra de menú). Si el port ha canviat,
    # la pàgina no s'hi podria reconnectar: s'obre una finestra a l'adreça nova.
    if port_canviat or not (DADES / "actualitzada.json").exists():
        obre_navegador(url)

    import rumps

    from canconer import actualitzacions, actualitzador, copies

    # Clicar la icona del Dock (o tornar a obrir l'app des del Finder) obre la finestra de Cançoners.
    # rumps no ho exposa: s'afegeix el mètode corresponent al delegat de l'aplicació.
    try:
        import objc
        from rumps import rumps as _rumps

        def torna_a_obrir(self, aplicacio, finestres_visibles):
            obre_navegador(url)
            return True

        objc.classAddMethods(_rumps.NSApp, [objc.selector(
            torna_a_obrir, selector=b"applicationShouldHandleReopen:hasVisibleWindows:", signature=b"Z@:@Z")])
    except Exception:  # noqa: BLE001 - sense això, l'app funciona igual (des de la barra de menú)
        pass

    versio = actualitzacions.versio_actual()

    class App(rumps.App):
        def __init__(self):
            icona = recurs("icona-menu.png")
            super().__init__(NOM, icon=icona if Path(icona).exists() else None, template=True,
                             title=None if Path(icona).exists() else "♪", quit_button=None)
            self.item_versio = rumps.MenuItem(f"Cançoners {versio}")
            # Finestra pròpia (amb Chrome, Edge o Brave) o el navegador de sempre.
            self.item_finestra = rumps.MenuItem("Obre en una finestra pròpia", callback=self.canvia_finestra)
            self.item_finestra.state = int(configuracio().get("finestra", "app") == "app")
            if not navegador_app():
                self.item_finestra.set_callback(None)  # sense Chrome, Edge ni Brave no es pot
            self.menu = [
                rumps.MenuItem("Obre Cançoners", callback=lambda _: obre_navegador(url)),
                rumps.MenuItem("Obre la carpeta de dades", callback=lambda _: subprocess.Popen(["open", str(DADES)])),
                self.item_finestra,
                None,
                self.item_versio,
                rumps.MenuItem("Cerca actualitzacions…", callback=lambda _: obre_navegador(url + "actualitzacio")),
                rumps.MenuItem("Fes una còpia de seguretat ara", callback=self.copia_ara),
                rumps.MenuItem("Còpies de seguretat…", callback=lambda _: obre_navegador(url + "copies")),
                None,
                rumps.MenuItem("Surt", callback=self.surt),
            ]
            # La consulta a GitHub es fa en un fil a part; el resultat es mostra des del fil
            # principal (rumps només pot obrir diàlegs des d'aquí).
            self.resultat = None
            self.cercant = False
            rumps.Timer(self.mostra_resultat, 1).start()
            rumps.Timer(lambda _: self.cerca(manual=False), CADA_QUANT).start()
            # Si l'app s'acaba d'actualitzar (l'instal·lador ho marca), es diu un sol cop.
            marca = DADES / "actualitzada.json"
            try:
                anterior = json.loads(marca.read_text()).get("de")
            except (OSError, ValueError):
                anterior = None
            marca.unlink(missing_ok=True)
            self.actualitzada = anterior if anterior and anterior != versio else None
            fallida = DADES / "actualitzacio-fallida.json"
            try:
                self.fallida = json.loads(fallida.read_text()).get("error")
            except (OSError, ValueError):
                self.fallida = None
            fallida.unlink(missing_ok=True)
            primera = threading.Timer(8, lambda: self.cerca(manual=False))
            primera.daemon = True
            primera.start()

        def canvia_finestra(self, item) -> None:
            item.state = int(not item.state)
            desa_configuracio(finestra="app" if item.state else "navegador")
            obre_navegador(url)

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
            # L'actualització es fa des de la web; quan acaba de preparar-ho tot, l'app es tanca.
            if actualitzador.estat["sortir"]:
                actualitzador.estat["sortir"] = False
                FITXER_SERVIDOR.unlink(missing_ok=True)
                rumps.quit_application()
                return
            if self.fallida:
                missatge, self.fallida = self.fallida, None
                rumps.alert("No s'ha pogut actualitzar", f"{missatge}\n\nEl detall és a {DADES / 'actualitzacio.log'}.")
            if self.actualitzada:
                abans, self.actualitzada = self.actualitzada, None
                copies_fetes = copies.llista()
                if not rumps.alert(f"Cançoners s'ha actualitzat a la {versio}",
                                   f"Tenies la {abans}. Les teves dades hi són totes."
                                   + (f"\n\nÚltima còpia de seguretat: {copies_fetes[0].name}" if copies_fetes else ""),
                                   ok="D'acord", cancel="Obre Cançoners"):
                    obre_navegador(url)
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
            """L'actualització es fa a la pàgina /actualitzacio, que en mostra cada pas: còpia de
            seguretat, baixada, verificació de la signatura, instal·lació i reinici."""
            obre_navegador(url + "actualitzacio?inicia=1")

        # -------------------------------------------------------- Còpies de seguretat

        def copia_ara(self, _) -> None:
            try:
                copia = copies.fes_copia(versio, "manual")
            except Exception as e:  # noqa: BLE001
                rumps.alert("No s'ha pogut fer la còpia", str(e))
                return
            if rumps.alert("Còpia de seguretat feta", f"S'ha desat {copia.name}. Es conserven les dels últims {copies.DIES_CONSERVADES} dies.",
                           ok="D'acord", cancel="Mostra-la"):
                return
            subprocess.Popen(["open", "-R", str(copia)])

        def surt(self, _):
            FITXER_SERVIDOR.unlink(missing_ok=True)
            rumps.quit_application()

    App().run()


if __name__ == "__main__":
    main()
