from canconer import document


def _linia(doc, i):
    return doc["content"][i]


def test_converteix_acords_a_sobre_de_la_lletra():
    doc = document.de_text("G          D/F#\nCamino pel sender de")
    contingut = _linia(doc, 0)["content"]
    assert contingut == [
        {"type": "acord", "attrs": {"nom": "G"}},
        {"type": "text", "text": "Camino pel "},
        {"type": "acord", "attrs": {"nom": "D/F#"}},
        {"type": "text", "text": "sender de"},
    ]


def test_acord_mes_enlla_del_final_de_la_lletra():
    doc = document.de_text("C        G\nHola")
    assert document.a_chordpro(doc) == "[C]Hola     [G]"


def test_seccions_linies_buides_i_linies_nomes_d_acords():
    doc = document.de_text("[Intro] G  D\n\n\n[Chorus]\nC\nla la")
    tipus = [b["type"] for b in doc["content"]]
    assert tipus == ["seccio", "linia", "linia", "seccio", "linia"]
    assert document.a_chordpro(doc).splitlines()[1] == "[G][D]"


def test_acords_i_transport_del_document():
    doc = document.de_text("G   D/F#  Em\nuna lletra qualsevol\nN.C.\nfi")
    assert document.acords(doc) == ["G", "D/F#", "Em"]
    assert document.acords(document.transporta(doc, 2)) == ["A", "E/G#", "F#m"]
    assert document.acords(doc) == ["G", "D/F#", "Em"]  # l'original no canvia


def test_detecta_text_amb_acords_en_enganxar():
    assert document.sembla_text_amb_acords("G   D\nhola que tal")
    assert not document.sembla_text_amb_acords("A la vora del mar\nhi ha una casa")


def test_etiquetes_de_seccio_en_catala():
    assert document.etiqueta_catalana("Verse 1") == "Estrofa 1"
    assert document.etiqueta_catalana("CHORUS") == "Tornada"
    assert document.etiqueta_catalana("Pre-Chorus") == "Pre-tornada"
    assert document.etiqueta_catalana("Bridge:") == "Pont"
    assert document.etiqueta_catalana("Estribillo") == "Tornada"
    assert document.etiqueta_catalana("Final x2") == "Final x2"  # desconeguda: igual
    doc = document.de_text("[Verse 2]\nG\nla la\n\n[Chorus]\nC\nla")
    assert [b["content"][0]["text"] for b in doc["content"] if b["type"] == "seccio"] == ["Estrofa 2", "Tornada"]
