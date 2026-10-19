"""Actualització de l'app de Mac des de la mateixa app, amb el progrés visible a la web.

Passos (l'estat es consulta a /api/actualitzacio/estat):
  1. copia        còpia de seguretat de les dades (si falla, no es continua)
  2. baixada      Canconers.zip de l'última release de GitHub, amb el progrés en bytes
  3. verificacio  es descomprimeix i es comprova la signatura (Developer ID, Team ID); a l'usuari
                  només se li diu que el paquet és correcte
  4. installacio  un script auxiliar espera que aquesta app es tanqui, la substitueix i obre la
                  nova; si la nova no arrenca en un minut, torna a posar l'anterior
  5. reinici      l'app es tanca (ho fa escriptori.py quan veu estat["sortir"])
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import requests

from . import actualitzacions, basedades, copies

EQUIP = "3HWTS4AVPU"  # Team ID de la signatura de les versions publicades
API_ULTIMA = actualitzacions.API_ULTIMA
FASES = ("copia", "baixada", "verificacio", "installacio", "reinici")

_bloqueig = threading.Lock()
estat: dict = {"fase": None, "missatge": "", "baixat": 0, "total": 0, "error": None, "fet": False,
               "sortir": False, "copia": None, "versio_nova": None, "registre": []}


class ErrorActualitzacio(RuntimeError):
    pass


def app_actual() -> Path | None:
    """El paquet .app que s'està executant (None si no és l'app de Mac, p. ex. en desenvolupament)."""
    if not getattr(sys, "frozen", False):
        return None
    cami = Path(sys.executable).resolve()
    for pare in cami.parents:
        if pare.suffix == ".app":
            return pare
    return None


def pot_actualitzar() -> tuple[bool, str]:
    app = app_actual()
    if not app:
        return False, "Només l'app de Mac es pot actualitzar sola. Des del codi font, fes «git pull»."
    if not os.access(app.parent, os.W_OK):
        return False, f"No es pot escriure a {app.parent}. Torna a instal·lar-la amb l'ordre del Terminal."
    return True, ""


def _passa(fase: str, missatge: str) -> None:
    estat.update(fase=fase, missatge=missatge)
    estat["registre"].append({"fase": fase, "missatge": missatge, "hora": time.strftime("%H:%M:%S")})


def en_marxa() -> bool:
    return estat["fase"] is not None and not estat["error"] and not estat["fet"]


def inicia() -> bool:
    """Comença l'actualització en un fil a part. Retorna False si ja n'hi ha una en marxa."""
    with _bloqueig:
        if en_marxa():
            return False
        estat.update(fase=None, missatge="", baixat=0, total=0, error=None, fet=False, sortir=False,
                     copia=None, versio_nova=None, registre=[])
        _passa("copia", "Començant…")
    threading.Thread(target=_executa, daemon=True).start()
    return True


def _executa() -> None:
    try:
        _actualitza()
    except Exception as e:  # noqa: BLE001 - qualsevol error atura l'actualització i es mostra
        estat["error"] = str(e) or type(e).__name__
        estat["registre"].append({"fase": estat["fase"], "missatge": f"Error: {estat['error']}",
                                  "hora": time.strftime("%H:%M:%S")})


def _actualitza() -> None:
    ok, motiu = pot_actualitzar()
    if not ok:
        raise ErrorActualitzacio(motiu)
    versio = actualitzacions.versio_actual()

    # 1. Còpia de seguretat
    _passa("copia", "Fent la còpia de seguretat de les dades…")
    try:
        copia = copies.fes_copia(versio, "abans-d-actualitzar")
    except Exception as e:  # noqa: BLE001
        raise ErrorActualitzacio(f"No s'ha pogut fer la còpia de seguretat ({e}). No s'ha tocat res.") from e
    estat["copia"] = copia.name
    _passa("copia", f"Còpia feta: {copia.name} ({copia.stat().st_size / 1e6:.1f} MB)")

    # 2. Baixada
    _passa("baixada", "Buscant l'última versió…")
    try:
        release = requests.get(API_ULTIMA, timeout=10, headers={"Accept": "application/vnd.github+json", **SENSE_COMPRESSIO}).json()
    except (requests.RequestException, ValueError) as e:
        raise ErrorActualitzacio(f"No es pot connectar amb GitHub ({e}).") from e
    nova = str(release.get("tag_name", "")).lstrip("v")
    actiu = next((a for a in release.get("assets", []) if a.get("name") == "Canconers.zip"), None)
    if not nova or not actiu:
        raise ErrorActualitzacio("La versió publicada no té el paquet de l'app (Canconers.zip).")
    estat["versio_nova"] = nova
    temporal = Path(tempfile.mkdtemp(prefix="canconers-"))
    zip_ = temporal / "Canconers.zip"
    _passa("baixada", f"Baixant Cançoners {nova}…")
    for intent in (1, 2):
        try:
            baixa(actiu["browser_download_url"], zip_, int(actiu.get("size") or 0))
            break
        except (requests.RequestException, OSError, ErrorActualitzacio) as e:
            if intent == 2:
                shutil.rmtree(temporal, ignore_errors=True)
                raise ErrorActualitzacio(f"La baixada s'ha interromput ({e}). No s'ha tocat res.") from e
            _passa("baixada", f"La baixada ha fallat ({e}). Es torna a provar…")
    _passa("baixada", f"Baixada completa ({estat['baixat'] / 1e6:.1f} MB)")

    # 3. Verificació
    _passa("verificacio", "Comprovant que el paquet és correcte…")
    nova_app = verifica(zip_, temporal)
    _passa("verificacio", f"Paquet correcte. Versió {nova}.")

    # 4. Instal·lació (la fa un script quan aquesta app ja s'ha tancat)
    _passa("installacio", "Preparant la substitució de l'app…")
    script = _escriu_script(temporal, nova_app, versio)
    subprocess.Popen(["/bin/bash", str(script)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)

    # 5. Reinici
    _passa("reinici", "Tancant aquesta versió i obrint la nova…")
    estat["sortir"] = True


# Les dades es demanen sense compressió HTTP i es desen tal com arriben: alguns proxies, antivirus o
# xarxes marquen la resposta com a comprimida sense ser-ho, i descomprimir-la donava «Error -3 while
# decompressing data: incorrect header check». El paquet ja és un .zip; la mida es comprova.
SENSE_COMPRESSIO = {"Accept-Encoding": "identity"}


def baixa(url: str, desti: Path, mida: int = 0) -> None:
    """Baixa el paquet de l'app a `desti` (comptant el progrés) i en comprova la mida."""
    estat["baixat"] = 0
    with requests.get(url, stream=True, timeout=30, headers=SENSE_COMPRESSIO) as r:
        r.raise_for_status()
        estat["total"] = mida or int(r.headers.get("content-length") or 0)
        with open(desti, "wb") as f:
            for tros in r.raw.stream(256 * 1024, decode_content=False):
                f.write(tros)
                estat["baixat"] += len(tros)
    if mida and desti.stat().st_size != mida:
        raise ErrorActualitzacio(f"s'han rebut {desti.stat().st_size} bytes de {mida}")


def verifica(zip_: Path, desti: Path) -> Path:
    """Descomprimeix l'app i en comprova la signatura i l'equip. Retorna el camí de la nova app."""
    r = subprocess.run(["ditto", "-x", "-k", str(zip_), str(desti)], capture_output=True, text=True)
    nova_app = desti / "Cançoners.app"
    if r.returncode or not nova_app.is_dir():
        raise ErrorActualitzacio("El paquet baixat està malmès.")
    r = subprocess.run(["codesign", "--verify", "--deep", "--strict", str(nova_app)], capture_output=True, text=True)
    if r.returncode:
        raise ErrorActualitzacio("El paquet baixat no és vàlid. No s'ha instal·lat res.")
    r = subprocess.run(["codesign", "-dv", str(nova_app)], capture_output=True, text=True)
    if f"TeamIdentifier={EQUIP}" not in r.stdout + r.stderr:
        raise ErrorActualitzacio("El paquet baixat no és l'oficial de Cançoners. No s'ha instal·lat res.")
    return nova_app


def versio_de(app: Path) -> str:
    try:
        with open(app / "Contents" / "Info.plist", "rb") as f:
            return str(plistlib.load(f).get("CFBundleShortVersionString", ""))
    except OSError:
        return ""


def _escriu_script(temporal: Path, nova_app: Path, versio: str) -> Path:
    app = app_actual()
    dades = basedades.DIRECTORI
    script = temporal / "instal·la.sh"
    script.write_text(f"""#!/bin/bash
# Substitueix Cançoners per la versió nova quan l'actual s'ha tancat. Si la nova no arrenca,
# torna a posar l'anterior.
APP={_q(app)}
NOVA={_q(nova_app)}
DADES={_q(dades)}
TMP={_q(temporal)}
REGISTRE="$DADES/actualitzacio.log"
registra() {{ echo "$(date '+%F %T') $*" >> "$REGISTRE"; }}
registra "Actualitzant de {versio} a $(defaults read "$NOVA/Contents/Info" CFBundleShortVersionString 2>/dev/null)"
for _ in $(seq 60); do kill -0 {os.getpid()} 2>/dev/null || break; sleep 0.5; done
kill -9 {os.getpid()} 2>/dev/null
if ! mv "$APP" "$TMP/anterior.app"; then registra "No s'ha pogut moure l'app actual"; open "$APP"; exit 1; fi
if ! mv "$NOVA" "$APP"; then mv "$TMP/anterior.app" "$APP"; registra "No s'ha pogut posar la nova"; open "$APP"; exit 1; fi
xattr -dr com.apple.quarantine "$APP" 2>/dev/null
printf '{{"de": "%s"}}\\n' {_q(versio)} > "$DADES/actualitzada.json"
inici=$(date +%s)
open "$APP"
for _ in $(seq 60); do
    sleep 1
    if [[ -f "$DADES/servidor.json" ]] && (( $(stat -f %m "$DADES/servidor.json") >= inici )); then
        url=$(sed -E 's/.*"url": *"([^"]+)".*/\\1/' "$DADES/servidor.json")
        if curl -fs -o /dev/null --max-time 2 "$url"; then registra "Fet"; rm -rf "$TMP"; exit 0; fi
    fi
done
registra "La versió nova no arrenca: es torna a l'anterior"
pkill -f "$APP/Contents/MacOS/" 2>/dev/null; sleep 1
rm -rf "$APP" "$DADES/actualitzada.json"
mv "$TMP/anterior.app" "$APP"
printf '{{"error": "La versió nova no ha arrencat i s\\x27ha tornat a la {versio}."}}\\n' > "$DADES/actualitzacio-fallida.json"
open "$APP"
rm -rf "$TMP"
""", "utf-8")
    script.chmod(0o755)
    return script


def _q(valor) -> str:
    """Cometes per a bash."""
    return "'" + str(valor).replace("'", "'\\''") + "'"
