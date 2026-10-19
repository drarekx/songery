"""Cançoner d'exemple per provar l'aplicació (lletres inventades)."""

from __future__ import annotations

from . import basedades, document, plantilles

_ESTROFA = """\
G           D/F#        Em
Pujo pel sender de la muntanya,
C               G          D
l'aire fresc del matí em fa companyia,
G            D/F#         Em
el sol s'aixeca sobre la cabana
C           D            G
i el dia nou comença d'alegria."""

_TORNADA = """\
[Tornada]
C         D        G      Em
Canta, canta, que la nit és llarga,
C         D           G
canta fins que surti el sol,
C          D         Em    C
una cançó que ens abraça i ens empara,
Am        D          G
cantem plegats amb tot el cor."""


def cos_llarg(estrofes: int = 4, intro: str = "G  D  Em  C") -> str:
    """Genera un cos de cançó (format de text amb acords a sobre) amb les estrofes que es vulgui."""
    parts = [f"[Intro]\n{intro}"]
    for i in range(estrofes):
        parts.append(f"[Estrofa {i + 1}]\n{_ESTROFA}")
        parts.append(_TORNADA)
    parts.append("[Final]\nC  D  G\nN.C.")
    return "\n\n".join(parts)


CANCONS = [
    {"titol": "Camí de muntanya", "autor": "Popular inventada", "cos": cos_llarg(4)},
    {"titol": "Cançó del far", "autor": "Grup de prova", "cos": cos_llarg(4, "Am  F  C  G"), "transport": 2},
    {"titol": "La barca", "autor": "", "cos": cos_llarg(5, "Em  C  G  D")},
    {"titol": "Nit d'estiu", "autor": "Anònim", "cos": cos_llarg(4, "D  A  Bm  G")},
]


def crea_exemple() -> str:
    """Crea un cançoner amb 4 cançons noves a la biblioteca i en retorna l'id."""
    id_canconer = basedades.crea_canconer(
        "Cançoner d'exemple", subtitol="Trobada de prova", any="2026",
        contraportada="Fet amb el generador de cançoners.\nBona cantada!",
        especials={"portada": plantilles.portada_completa()})
    for c in CANCONS:
        id_canco = basedades.crea_canco(c["titol"], c["autor"], document.de_text(c["cos"]))
        basedades.crea_versio(id_canco, "Versió inicial")
        basedades.afegeix_entrada(id_canconer, id_canco)
        if c.get("transport"):
            basedades.actualitza_entrada(id_canconer, id_canco, transport=c["transport"])
    return id_canconer
