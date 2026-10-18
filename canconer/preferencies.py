"""Preferències de l'usuari: l'estat de la interfície que es recorda d'una sessió a l'altra (per
exemple, l'amplada de la columna de propietats de l'editor).

Es desen en un fitxer JSON a la carpeta de dades (preferencies.json). Cada preferència té un valor
per defecte i una validació: el que arriba de fora i no és vàlid s'ignora.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from . import basedades

FITXER = "preferencies.json"

# clau → (valor per defecte, validació)
PREFERENCIES = {
    # Amplada (px) de la columna de la dreta de l'editor (propietats, capes, cançó...).
    "editor.amplePropietats": (320, lambda v: isinstance(v, int) and 260 <= v <= 720),
    # Amplada (px) de la columna de l'esquerra de l'editor (llibret, cançons, mestres).
    "editor.ampleLlista": (256, lambda v: isinstance(v, int) and 200 <= v <= 480),
    # Zoom del llenç (1 = la doble pàgina ajustada a la finestra).
    "editor.zoom": (1, lambda v: isinstance(v, (int, float)) and not isinstance(v, bool) and 0.3 <= v <= 4),
    # Pestanya oberta de la columna de la dreta.
    "editor.pestanya": ("propietats", lambda v: v in ("propietats", "capes", "canco", "estils", "biblioteca")),
}

_bloqueig = threading.Lock()


def _cami() -> Path:
    return Path(basedades.DIRECTORI) / FITXER


def carrega() -> dict:
    """Totes les preferències (les desades i, per a la resta, els valors per defecte)."""
    try:
        desades = json.loads(_cami().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        desades = {}
    if not isinstance(desades, dict):
        desades = {}
    return {clau: desades[clau] if clau in desades and valida(desades[clau]) else defecte
            for clau, (defecte, valida) in PREFERENCIES.items()}


def desa(canvis: dict) -> dict:
    """Desa els canvis vàlids (les claus desconegudes o els valors no vàlids s'ignoren) i torna les
    preferències resultants. Un valor None torna la preferència al valor per defecte."""
    with _bloqueig:
        actuals = carrega()
        for clau, valor in (canvis or {}).items():
            if clau not in PREFERENCIES:
                continue
            defecte, valida = PREFERENCIES[clau]
            if valor is None:
                actuals[clau] = defecte
            elif valida(valor):
                actuals[clau] = valor
        cami = _cami()
        cami.parent.mkdir(parents=True, exist_ok=True)
        temporal = cami.with_suffix(".tmp")
        temporal.write_text(json.dumps(actuals, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporal, cami)
    return actuals
