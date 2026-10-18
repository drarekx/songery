import pytest

from canconer.parser import (acords_utilitzats, analitza, es_acord, es_linia_acords,
                             transporta_acord, transporta_cos, transporta_linia_acords)


@pytest.mark.parametrize("acord", [
    "A", "Bb", "C#", "Am", "Em7", "Gmaj7", "CMaj7", "Dsus4", "Dsus2", "Cadd9", "Bdim",
    "Caug", "F#m7b5", "D/F#", "G/B", "Am7/G", "E7(#9)", "C6", "Bbmin", "N.C.", "NC", "A5",
])
def test_acords_valids(acord):
    assert es_acord(acord)


@pytest.mark.parametrize("element", ["H", "la", "Am,", "Do", "Camino", "Add", "Bad", "c", "[Intro]"])
def test_no_son_acords(element):
    assert not es_acord(element)


@pytest.mark.parametrize("linia", [
    "G           D/F#        Em",
    "   Am  F  C  G",
    "N.C.",
    "C  |  G  |  Am  F  |",
    "E   A   (x2)",
])
def test_linies_d_acords(linia):
    assert es_linia_acords(linia)


@pytest.mark.parametrize("linia", [
    "Camino pel sender de la muntanya",
    "A la vora del mar",
    "E la nit",
    "",
    "   ",
    "| | |",
    "[Chorus]",
])
def test_linies_que_no_son_d_acords(linia):
    assert not es_linia_acords(linia)


def test_classificacio_de_linies():
    tipus = [l.tipus for l in analitza("[Intro]\nG  D\n\nG    D\nHola món\n[Chorus] C G")]
    assert tipus == ["seccio", "acords", "buida", "acords", "lletra", "seccio"]
    assert analitza("[Chorus] C G")[0].resta_acords


def test_espais_es_conserven_exactament():
    linia = "    G      D/F#   Em"
    assert analitza(linia)[0].text == linia


def test_tabuladors_es_converteixen_en_espais():
    assert analitza("G\tD")[0].text == "G       D"


def test_acords_utilitzats_en_ordre_i_sense_repetir():
    cos = "[Intro] E  A\n\nE      A       D\nlletra\nE   B7  N.C.\nmés lletra"
    assert acords_utilitzats(cos) == ["E", "A", "D", "B7"]


# ---------------------------------------------------------------- Transport

@pytest.mark.parametrize("acord, semitons, esperat", [
    ("C", 2, "D"),
    ("C", 1, "C#"),
    ("C", 3, "Eb"),
    ("Am", 2, "Bm"),
    ("G7", 5, "C7"),
    ("B", 1, "C"),
    ("D/F#", 2, "E/G#"),
    ("Bb", 2, "C"),
    ("Eb", 2, "F"),
    ("F#m7b5", 1, "Gm7b5"),
    ("E", -1, "Eb"),
    ("C", -1, "B"),
    ("A", 12, "A"),
    ("Cmaj7", 7, "Gmaj7"),
    ("N.C.", 3, "N.C."),
])
def test_transporta_acord(acord, semitons, esperat):
    assert transporta_acord(acord, semitons) == esperat


def test_transport_arriba_al_semito_correcte():
    from canconer.parser import _SEMITO
    for arrel in ["C", "F#", "Bb", "E"]:
        for s in range(-11, 12):
            assert _SEMITO[transporta_acord(arrel, s)] == (_SEMITO[arrel] + s) % 12


def test_transport_mante_les_columnes():
    original = "G           D/F#        Em"
    transportat = transporta_linia_acords(original, 2)
    assert transportat == "A           E/G#        F#m"
    for o, t in zip(original.split(), transportat.split()):
        assert original.index(o) == transportat.index(t)


def test_transport_amb_acords_que_s_allarguen_deixa_un_espai():
    assert transporta_linia_acords("C D E", 1) == "C# Eb F"


def test_transporta_cos_no_toca_la_lletra():
    cos = "[Intro] C  G\nC        G\nCanta la C i la G"
    resultat = transporta_cos(cos, 2).split("\n")
    assert resultat == ["[Intro] D  A", "D        A", "Canta la C i la G"]
