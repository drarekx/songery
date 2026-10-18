import pytest

from canconer import diagrames, disseny, plantilles
from canconer.parser import _SEMITO

AFINACIO = {"guitarra": [4, 9, 2, 7, 11, 4], "ukulele": [7, 0, 4, 9]}
INTERVALS = {"": {0, 4, 7}, "m": {0, 3, 7}, "7": {0, 4, 7, 10}, "m7": {0, 3, 7, 10}, "maj7": {0, 4, 7, 11}}


@pytest.mark.parametrize("instrument", ["guitarra", "ukulele"])
@pytest.mark.parametrize("arrel", ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"])
@pytest.mark.parametrize("qualitat", ["", "m", "7", "m7", "maj7"])
def test_els_diagrames_tenen_les_notes_de_l_acord(instrument, arrel, qualitat):
    posicions, _ = diagrames.posicio(arrel + qualitat, instrument)
    assert len(posicions) == len(AFINACIO[instrument])
    notes = {(corda + trast) % 12 for corda, trast in zip(AFINACIO[instrument], posicions) if trast >= 0}
    esperades = {(_SEMITO[arrel] + i) % 12 for i in INTERVALS[qualitat]}
    assert notes <= esperades
    assert _SEMITO[arrel] in notes


def test_svg_ukulele_te_quatre_cordes():
    import re
    svg = diagrames.svg("Am", "ukulele")
    verticals = [m for m in re.finditer(r'<line x1="([\d.]+)" y1="[\d.]+" x2="([\d.]+)"', svg) if m[1] == m[2]]
    assert len(verticals) == 4


def test_element_valors_dolents():
    e = disseny.element({"tipus": "text", "x": "9999", "y": 5, "w": 10, "h": 5, "text": "{titol}",
                         "estil": "Títol!", "format": {"color": "red", "mida": 1000, "font": "Comic Sans!"}})
    assert e["x"] == 296 and "estil" not in e and e["format"] == {"mida": 300}
    assert disseny.element({"tipus": "script"}) is None


def test_marc_de_lletra_i_contingut():
    c = disseny.contingut({"pagines": [{"mestra": "estandard", "elements": [
        {"tipus": "lletra", "x": 0, "y": 0, "w": 50, "h": 50, "doc": "dolent", "columnes": 9}]}]})
    marc = c["pagines"][0]["elements"][0]
    assert marc["doc"]["type"] == "doc" and marc["columnes"] == 4 and marc["ajusta"] is True
    with pytest.raises(ValueError):
        disseny.contingut({"pagines": []})


def test_estils_i_mestres():
    estils = disseny.estils({"lletra": {"mida": 14, "color": "#123456", "nom": "Lletra gran"}, "Dolent!": {}})
    assert estils["lletra"]["mida"] == 14 and estils["lletra"]["color"] == "#123456" and "Dolent!" not in estils
    mestres = disseny.mestres(plantilles.mestres() + [{"id": "MAL ID"}])
    assert [m["id"] for m in mestres] == ["estandard"]


def test_conversio_del_format_antic_a_pagines():
    from canconer.document import de_text
    curta = plantilles.de_document(de_text("C\nhola"))
    assert len(curta["pagines"]) == 1
    llarga = plantilles.de_document(de_text("\n\n".join(["C\nuna línia"] * 30)))
    assert len(llarga["pagines"]) == 2
    tipus = [e["tipus"] for e in llarga["pagines"][1]["elements"]]
    assert tipus == ["lletra"]  # la segona pàgina no repeteix el títol


def test_tipografia_i_bloqueig_dels_elements():
    e = disseny.element({"tipus": "imatge", "x": 0, "y": 0, "w": 9, "h": 9, "bloquejat": True,
                         "format": {"font": "u-meva-lletra"}})
    assert e["bloquejat"] is True and e["format"]["font"] == "u-meva-lletra"
    e = disseny.element({"tipus": "text", "x": 0, "y": 0, "w": 9, "h": 9, "format": {"font": "<script>"}})
    assert "bloquejat" not in e and "font" not in e.get("format", {})


def test_grups_d_elements():
    e = disseny.element({"tipus": "forma", "x": 0, "y": 0, "w": 9, "h": 9, "grup": "abc123"})
    assert e["grup"] == "abc123"
    assert "grup" not in disseny.element({"tipus": "forma", "x": 0, "y": 0, "w": 9, "h": 9, "grup": "<b>dolent</b>"})
