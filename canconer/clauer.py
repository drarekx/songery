"""Claus d'API al clauer del Mac (Accés a Claus), amb l'eina `security` del sistema.

Les claus no es desen mai a la carpeta de dades: no surten a les còpies de seguretat ni als cançoners
exportats. Fora del Mac (Docker) no hi ha clauer: la clau es passa amb una variable d'entorn.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

SECURITY = "/usr/bin/security"
# Nom del servei al clauer (un element per proveïdor: el compte és el nom del proveïdor).
SERVEI = os.environ.get("CANCONER_CLAUER_SERVEI", "Canconers IA")
# Una clau d'API: caràcters visibles, sense espais, cometes ni barres inverses (van dins d'una ordre).
_CLAU_VALIDA = re.compile(r"^[A-Za-z0-9._\-+/=:~@]{8,500}$")
_COMPTE_VALID = re.compile(r"^[a-z0-9_-]{1,40}$")


class ErrorClauer(Exception):
    """No s'ha pogut llegir o escriure al clauer (el missatge és per a l'usuari)."""


def disponible() -> bool:
    return sys.platform == "darwin" and os.access(SECURITY, os.X_OK)


def _compte(compte: str) -> str:
    if not _COMPTE_VALID.match(compte):
        raise ValueError(f"Compte no vàlid: {compte}")
    return compte


def _security(*arguments: str, entrada: str | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run([SECURITY, *arguments], input=entrada, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise ErrorClauer("El clauer del Mac no respon.") from e


def llegeix(compte: str) -> str | None:
    """La clau desada, o None si no n'hi ha (o no hi ha clauer)."""
    if not disponible():
        return None
    r = _security("find-generic-password", "-s", SERVEI, "-a", _compte(compte), "-w")
    clau = r.stdout.strip()
    return clau if r.returncode == 0 and clau else None


def desa(compte: str, clau: str) -> None:
    """Desa (o substitueix) la clau. No passa mai pels arguments del procés: `security -i` la llegeix
    de l'entrada, i així no es veu a la llista de processos."""
    clau = clau.strip()
    if not _CLAU_VALIDA.match(clau):
        raise ErrorClauer("Aquesta clau no sembla una clau d'API: enganxa-la sencera, sense espais.")
    if not disponible():
        raise ErrorClauer("Aquí no hi ha el clauer del Mac. Passa la clau amb la variable d'entorn del proveïdor.")
    ordre = f'add-generic-password -U -s "{SERVEI}" -a "{_compte(compte)}" -l "{SERVEI} ({compte})" -w "{clau}"\n'
    r = _security("-i", entrada=ordre)
    if r.returncode != 0 or llegeix(compte) != clau:
        raise ErrorClauer("No s'ha pogut desar la clau al clauer del Mac.")


def esborra(compte: str) -> None:
    if disponible():
        _security("delete-generic-password", "-s", SERVEI, "-a", _compte(compte))
