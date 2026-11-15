"""Intel·ligència artificial: el proveïdor i el model que tria l'usuari, i el que se'ls demana.

Proveïdors: Anthropic (SDK `anthropic`), OpenAI i OpenRouter (SDK `openai`; OpenRouter parla el mateix
protocol en una altra adreça). Els SDK s'importen quan calen: l'app arrenca igual si no hi són.

La clau de cada proveïdor és al clauer del Mac (`clauer.py`) o, si no n'hi ha, a la variable d'entorn
habitual del proveïdor. El proveïdor i els models triats són preferències (`ia.*`).

Primera acció: `canco_de_foto`, que llegeix la foto d'una partitura o d'un full de cançoner i en torna
el títol, l'autor, la lletra amb acords i on és el pentagrama (per retallar-lo de la foto).
"""

from __future__ import annotations

import base64
import json
import os
import re

from . import clauer, preferencies

PROVEIDORS = {
    "anthropic": {"nom": "Anthropic (Claude)", "entorn": "ANTHROPIC_API_KEY", "base": None,
                  "claus": "https://platform.claude.com/settings/keys"},
    "openai": {"nom": "OpenAI", "entorn": "OPENAI_API_KEY", "base": None,
               "claus": "https://platform.openai.com/api-keys"},
    "openrouter": {"nom": "OpenRouter", "entorn": "OPENROUTER_API_KEY", "base": "https://openrouter.ai/api/v1",
                   "claus": "https://openrouter.ai/settings/keys"},
}
TIPUS_FOTO = {"image/jpeg", "image/png", "image/webp"}
MIDA_MAXIMA_FOTO = 8 * 1024 * 1024
TEMPS_MAXIM = 180  # segons: llegir una partitura sencera pot trigar
# Models d'OpenAI que no serveixen per llegir una foto (so, imatges, incrustacions…).
_NO_SON_DE_XAT = re.compile(r"embedding|whisper|tts|dall-e|moderation|audio|realtime|transcribe|image|sora|babbage|davinci")


class ErrorIA(Exception):
    """Error per ensenyar a l'usuari (ja en català i sense detalls tècnics que no l'ajudin)."""

    def __init__(self, missatge: str, codi: int = 502):
        super().__init__(missatge)
        self.codi = codi


# ---------------------------------------------------------------- Configuració


def _proveidor_valid(proveidor: str) -> str:
    if proveidor not in PROVEIDORS:
        raise ErrorIA("Proveïdor desconegut.", 400)
    return proveidor


def clau(proveidor: str) -> str | None:
    """La clau del proveïdor: la del clauer i, si no n'hi ha, la de la variable d'entorn."""
    try:
        desada = clauer.llegeix(_proveidor_valid(proveidor))
    except clauer.ErrorClauer:
        desada = None
    return desada or os.environ.get(PROVEIDORS[proveidor]["entorn"], "").strip() or None


def configuracio() -> dict:
    """El que ensenya la pàgina de configuració. Les claus no surten mai: només si n'hi ha."""
    p = preferencies.carrega()
    return {
        "proveidor": p["ia.proveidor"],
        "clauer": clauer.disponible(),
        "proveidors": [{"id": k, "nom": v["nom"], "model": p[f"ia.model.{k}"], "te_clau": bool(clau(k)),
                        "entorn": v["entorn"], "claus": v["claus"]} for k, v in PROVEIDORS.items()],
    }


def desa_configuracio(canvis: dict) -> dict:
    """Desa el proveïdor actiu, el model de cada proveïdor i, si arriba, la clau (al clauer)."""
    preferencies_noves = {}
    if "proveidor" in canvis:
        preferencies_noves["ia.proveidor"] = _proveidor_valid(str(canvis["proveidor"]))
    for proveidor, model in (canvis.get("models") or {}).items():
        preferencies_noves[f"ia.model.{_proveidor_valid(str(proveidor))}"] = str(model).strip()
    for proveidor, valor in (canvis.get("claus") or {}).items():
        _proveidor_valid(str(proveidor))
        try:
            if valor:
                clauer.desa(proveidor, str(valor))
            else:
                clauer.esborra(proveidor)
        except clauer.ErrorClauer as e:
            raise ErrorIA(str(e), 400) from e
    if preferencies_noves:
        preferencies.desa(preferencies_noves)
    return configuracio()


def _actiu() -> tuple[str, str, str]:
    """Proveïdor actiu, el seu model i la seva clau; si falta res, diu què cal fer."""
    p = preferencies.carrega()
    proveidor = p["ia.proveidor"]
    model = p[f"ia.model.{proveidor}"]
    clau_api = clau(proveidor)
    if not clau_api or not model:
        raise ErrorIA("Encara no has configurat la intel·ligència artificial: tria el proveïdor, "
                      "posa-hi la clau d'API i tria un model.", 409)
    return proveidor, model, clau_api


# ---------------------------------------------------------------- Clients i errors


def _client_anthropic(clau_api: str):
    import anthropic
    return anthropic, anthropic.Anthropic(api_key=clau_api, timeout=TEMPS_MAXIM, max_retries=1)


def _client_openai(proveidor: str, clau_api: str):
    import openai
    return openai, openai.OpenAI(api_key=clau_api, base_url=PROVEIDORS[proveidor]["base"],
                                 timeout=TEMPS_MAXIM, max_retries=1)


def _error(sdk, e: Exception, proveidor: str) -> ErrorIA:
    """Tradueix els errors dels SDK (l'`anthropic` i l'`openai` els anomenen igual)."""
    nom = PROVEIDORS[proveidor]["nom"]
    if isinstance(e, sdk.AuthenticationError):
        return ErrorIA(f"{nom} no accepta la clau d'API. Revisa-la a la configuració.", 401)
    if isinstance(e, sdk.PermissionDeniedError):
        return ErrorIA(f"Aquesta clau no té permís per fer servir aquest model de {nom}.", 403)
    if isinstance(e, sdk.NotFoundError):
        return ErrorIA(f"{nom} no coneix aquest model. Tria'n un altre a la configuració.", 404)
    if isinstance(e, sdk.RateLimitError):
        return ErrorIA(f"{nom} diu que has arribat al límit d'ús o de saldo. Torna-ho a provar d'aquí a una estona.", 429)
    if isinstance(e, sdk.APITimeoutError):
        return ErrorIA(f"{nom} ha trigat massa a respondre. Torna-ho a provar.", 504)
    if isinstance(e, sdk.APIConnectionError):
        return ErrorIA(f"No s'ha pogut connectar amb {nom}. Comprova la connexió a internet.", 503)
    if isinstance(e, sdk.APIStatusError):
        detall = getattr(e, "message", "") or str(e)
        return ErrorIA(f"{nom} ha tornat un error ({e.status_code}): {detall[:300]}", 502)
    return ErrorIA(f"Error inesperat parlant amb {nom}: {e}", 502)


# ---------------------------------------------------------------- Models


def models(proveidor: str, clau_api: str | None = None) -> list[dict]:
    """Models que ofereix el proveïdor amb aquesta clau: [{id, nom}], els més nous primer."""
    clau_api = (clau_api or "").strip() or clau(_proveidor_valid(proveidor))
    if not clau_api:
        raise ErrorIA("Primer cal la clau d'API d'aquest proveïdor.", 409)
    if proveidor == "anthropic":
        sdk, client = _client_anthropic(clau_api)
        try:
            return [{"id": m.id, "nom": m.display_name or m.id} for m in client.models.list(limit=100)]
        except sdk.APIError as e:
            raise _error(sdk, e, proveidor) from e
    sdk, client = _client_openai(proveidor, clau_api)
    try:
        llista = list(client.models.list())
    except sdk.APIError as e:
        raise _error(sdk, e, proveidor) from e
    if proveidor == "openrouter":
        # Només els que entenen imatges (OpenRouter ho diu a «architecture»); els noms ja venen fets.
        def veu_imatges(m) -> bool:
            modalitats = ((getattr(m, "architecture", None) or {}).get("input_modalities")
                          if isinstance(getattr(m, "architecture", None), dict) else None)
            return modalitats is None or "image" in modalitats
        return sorted(({"id": m.id, "nom": getattr(m, "name", None) or m.id} for m in llista if veu_imatges(m)),
                      key=lambda m: m["nom"].lower())
    de_xat = [m for m in llista if not _NO_SON_DE_XAT.search(m.id)]
    return [{"id": m.id, "nom": m.id} for m in sorted(de_xat, key=lambda m: getattr(m, "created", 0) or 0, reverse=True)]


# ---------------------------------------------------------------- Demanar un JSON amb una imatge


def _json_de_text(text: str) -> dict:
    """El JSON de la resposta (alguns models l'emboliquen amb ``` o hi posen text al voltant)."""
    inici, final = text.find("{"), text.rfind("}")
    try:
        dades = json.loads(text[inici:final + 1]) if inici >= 0 and final > inici else None
    except ValueError:
        dades = None
    if not isinstance(dades, dict):
        raise ErrorIA("El model no ha respost en el format esperat. Torna-ho a provar o tria un altre model.")
    return dades


def _demana_anthropic(model: str, clau_api: str, instruccions: str, peticio: str, foto: bytes, tipus: str, esquema: dict) -> dict:
    sdk, client = _client_anthropic(clau_api)
    parametres = dict(
        model=model, max_tokens=16000, system=instruccions,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": tipus,
                                         "data": base64.standard_b64encode(foto).decode("ascii")}},
            {"type": "text", "text": peticio},
        ]}])
    try:
        try:
            resposta = client.messages.create(**parametres, output_config={"format": {"type": "json_schema", "schema": esquema}})
        except sdk.BadRequestError as e:
            # Un model antic que no admet sortida estructurada: es demana el JSON només amb les instruccions.
            if "output_config" not in str(e) and "format" not in str(e):
                raise
            resposta = client.messages.create(**parametres)
    except sdk.APIError as e:
        raise _error(sdk, e, "anthropic") from e
    if resposta.stop_reason == "refusal":
        raise ErrorIA("El model s'ha negat a llegir aquesta imatge.", 422)
    if resposta.stop_reason == "max_tokens":
        raise ErrorIA("La cançó és massa llarga per llegir-la d'un sol cop. Prova-ho amb una foto de menys tros.", 422)
    return _json_de_text("".join(b.text for b in resposta.content if b.type == "text"))


def _demana_openai(proveidor: str, model: str, clau_api: str, instruccions: str, peticio: str, foto: bytes, tipus: str, esquema: dict) -> dict:
    sdk, client = _client_openai(proveidor, clau_api)
    parametres = dict(
        model=model,
        messages=[
            {"role": "system", "content": instruccions},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:{tipus};base64,{base64.standard_b64encode(foto).decode('ascii')}"}},
                {"type": "text", "text": peticio},
            ]},
        ])
    try:
        try:
            resposta = client.chat.completions.create(**parametres, response_format={
                "type": "json_schema", "json_schema": {"name": "resposta", "strict": True, "schema": esquema}})
        except sdk.BadRequestError as e:
            # Models (sobretot a OpenRouter) que no admeten sortida estructurada.
            if "response_format" not in str(e) and "json_schema" not in str(e) and "structured" not in str(e).lower():
                raise
            resposta = client.chat.completions.create(**parametres)
    except sdk.APIError as e:
        raise _error(sdk, e, proveidor) from e
    if not resposta.choices:
        raise ErrorIA("El model no ha tornat cap resposta. Torna-ho a provar o tria un altre model.")
    tria = resposta.choices[0]
    if getattr(tria.message, "refusal", None):
        raise ErrorIA("El model s'ha negat a llegir aquesta imatge.", 422)
    if tria.finish_reason == "length":
        raise ErrorIA("La cançó és massa llarga per llegir-la d'un sol cop. Prova-ho amb una foto de menys tros.", 422)
    return _json_de_text(tria.message.content or "")


def _demana(instruccions: str, peticio: str, foto: bytes, tipus: str, esquema: dict) -> dict:
    proveidor, model, clau_api = _actiu()
    if proveidor == "anthropic":
        return _demana_anthropic(model, clau_api, instruccions, peticio, foto, tipus, esquema)
    return _demana_openai(proveidor, model, clau_api, instruccions, peticio, foto, tipus, esquema)


def prova() -> dict:
    """Comprova que el proveïdor actiu respon amb la clau i el model triats (una petició mínima)."""
    proveidor, model, clau_api = _actiu()
    if proveidor == "anthropic":
        sdk, client = _client_anthropic(clau_api)
        try:
            client.messages.create(model=model, max_tokens=16, messages=[{"role": "user", "content": "Digues «hola»."}])
        except sdk.APIError as e:
            raise _error(sdk, e, proveidor) from e
    else:
        sdk, client = _client_openai(proveidor, clau_api)
        try:
            client.chat.completions.create(model=model, messages=[{"role": "user", "content": "Digues «hola»."}])
        except sdk.APIError as e:
            raise _error(sdk, e, proveidor) from e
    return {"ok": True, "proveidor": PROVEIDORS[proveidor]["nom"], "model": model}


# ---------------------------------------------------------------- Cançó a partir d'una foto

INSTRUCCIONS_FOTO = """\
Ets un copista de cançoners. Reps la foto d'un full amb una cançó (una partitura, un full de cançoner o \
una lletra amb acords) i en fas la transcripció per a una app de cançoners. Respon només amb el JSON demanat.

Camps:
- "titol": el títol tal com surt al full. Cadena buida si no n'hi ha.
- "autor": autor, compositor o origen («Popular catalana», «Tradicional»…) si el full ho diu. Si no, buida.
- "text": la lletra sencera, en l'idioma original i sense corregir-la ni traduir-la.
  - Una línia per vers; una línia buida entre estrofes.
  - Si la lletra és sota les notes amb les síl·labes separades per guionets (can-ta, a-mic), ajunta-les en \
paraules normals. Si hi ha diverses estrofes numerades sota el pentagrama, escriu-les una darrere l'altra.
  - Posa una etiqueta entre claudàtors en una línia a part només quan el full la marca o és evident: \
[Tornada], [Estrofa 1], [Intro], [Pont], [Final].
  - Acords: si el full en porta (a sobre de la lletra o del pentagrama), escriu-los en una línia just a sobre \
del vers, alineant amb espais cada acord sobre la síl·laba on cau. Fes servir sempre el xifrat anglosaxó \
(C D E F G A B, amb m, 7, maj7, sus4, /baix…): converteix Do Re Mi Fa Sol La Si i «lam», «SOL7», etc. \
No t'inventis acords: si el full no en té, no en posis cap.
  - No hi posis el títol ni l'autor, ni números de pàgina ni peus de pàgina.
- "partitures": els rectangles de la foto on hi ha notació musical (pentagrames amb notes), perquè l'app \
els retalli i els posi com a imatge. Cada rectangle ha d'incloure tots els pentagrames seguits, amb la clau, \
els acords de sobre i la lletra que hi hagi entre pentagrames, amb una mica de marge. Normalment n'hi ha un \
de sol; fes-ne més només si hi ha blocs de pentagrames separats per text. Les coordenades són mil·lèsimes de \
la imatge: "x" i "y" són el cantó de dalt a l'esquerra, "ample" i "alt" la mida; 0 és la vora esquerra o de \
dalt i 1000 la dreta o de baix. Si no hi ha cap pentagrama (només lletra, amb acords o sense), llista buida.

Si la imatge no és cap cançó, torna tots els camps buits."""

ESQUEMA_FOTO = {
    "type": "object",
    "properties": {
        "titol": {"type": "string"},
        "autor": {"type": "string"},
        "text": {"type": "string"},
        "partitures": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"x": {"type": "integer"}, "y": {"type": "integer"},
                               "ample": {"type": "integer"}, "alt": {"type": "integer"}},
                "required": ["x", "y", "ample", "alt"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["titol", "autor", "text", "partitures"],
    "additionalProperties": False,
}
MARGE_RETALL = 0.012  # marge que s'afegeix a cada retall, en fracció de la imatge


def _fraccio(valor) -> float | None:
    try:
        return max(0.0, min(1.0, float(valor) / 1000))
    except (TypeError, ValueError):
        return None


def _retalls(partitures) -> list[dict]:
    """Rectangles vàlids, en fraccions de la imatge (0–1), amb una mica de marge i dins de la foto."""
    retalls = []
    for r in partitures if isinstance(partitures, list) else []:
        if not isinstance(r, dict):
            continue
        x, y, ample, alt = (_fraccio(r.get(k)) for k in ("x", "y", "ample", "alt"))
        if None in (x, y, ample, alt):
            continue
        x0, y0 = max(0.0, x - MARGE_RETALL), max(0.0, y - MARGE_RETALL)
        x1, y1 = min(1.0, x + ample + MARGE_RETALL), min(1.0, y + alt + MARGE_RETALL)
        if x1 - x0 < 0.05 or y1 - y0 < 0.02:
            continue  # massa petit per ser un pentagrama
        retalls.append({"x": round(x0, 4), "y": round(y0, 4), "ample": round(x1 - x0, 4), "alt": round(y1 - y0, 4)})
    return retalls[:4]


def canco_de_foto(foto: bytes, tipus: str) -> dict:
    """Llegeix la foto d'una cançó: {titol, autor, text, partitures: [{x, y, ample, alt}]} (fraccions 0–1).

    El text és en el format «acords a sobre de la lletra» (el mateix d'«Importa»: `document.de_text`)."""
    if tipus not in TIPUS_FOTO:
        raise ErrorIA("La foto ha de ser JPG, PNG o WEBP.", 415)
    if not foto or len(foto) > MIDA_MAXIMA_FOTO:
        raise ErrorIA("La foto és buida o massa grossa.", 413)
    dades = _demana(INSTRUCCIONS_FOTO, "Transcriu la cançó d'aquesta foto.", foto, tipus, ESQUEMA_FOTO)
    text = str(dades.get("text") or "").replace("\r\n", "\n").strip("\n")
    retalls = _retalls(dades.get("partitures"))
    if not text.strip() and not retalls:
        raise ErrorIA("No s'ha trobat cap cançó en aquesta foto.", 422)
    return {"titol": str(dades.get("titol") or "").strip()[:200], "autor": str(dades.get("autor") or "").strip()[:200],
            "text": text, "partitures": retalls}
