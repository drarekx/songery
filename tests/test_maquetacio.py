import copy

import pytest

from canconer import basedades, maquetacio, plantilles
from canconer.document import de_text


def _canco(i: int, pagines: int = 2, **extra) -> dict:
    doc = de_text("C   G\nlletra")
    contingut = {"format": 2, "pagines": [plantilles.pagina_canco(doc) for _ in range(pagines)]}
    return {"id": f"c{i}", "titol": f"Cançó {i}", "autor": "", "contingut": contingut, "tipus": "canco",
            "inici": "esquerra", "transport": 0, "inclosa": True, **extra}


def _canconer(cancons: list[dict], **extra) -> dict:
    return plantilles.amb_valors_per_defecte({"titol": "Prova", "subtitol": "", "any": "2026", "contraportada": "",
                                              "pagina_acords": False, "posicio_acords": "inici",
                                              "instrument": "guitarra", "cancons": cancons, **extra})


def tipus(pla):
    return [p["tipus"] for p in pla["pagines"]]


def test_acceptacio_4_cancons_de_2_pagines_fan_12_pagines():
    pla = maquetacio.pla(_canconer([_canco(i) for i in range(4)]))
    assert pla["total"] == 12 and pla["fulls"] == 3
    assert [c["pagina_inici"] for c in pla["cancons"]] == [4, 6, 8, 10]
    assert tipus(pla) == ["portada", "index", "blanc"] + ["canco"] * 8 + ["contraportada"]


@pytest.mark.parametrize("n", range(0, 7))
def test_sempre_multiple_de_4_i_cancons_a_l_esquerra(n):
    pla = maquetacio.pla(_canconer([_canco(i, pagines=1 + i % 3) for i in range(n)]))
    assert pla["total"] % 4 == 0
    assert all(c["pagina_inici"] % 2 == 0 for c in pla["cancons"])
    assert tipus(pla)[0] == "portada" and tipus(pla)[-1] == "contraportada"


def test_inici_on_toqui_permet_dues_cancons_a_la_mateixa_doble_pagina():
    pla = maquetacio.pla(_canconer([_canco(0, pagines=1), _canco(1, pagines=1, inici="qualsevol")]))
    assert [c["pagina_inici"] for c in pla["cancons"]] == [4, 5]


def test_pagines_lliures_no_surten_a_l_index():
    lliure = _canco(9, pagines=1, tipus="pagina", inici="qualsevol", titol="Dedicatòria")
    pla = maquetacio.pla(_canconer([lliure, _canco(0)]))
    assert [c["titol"] for c in pla["cancons"]] == ["Cançó 0"]
    assert "lliure" in tipus(pla)
    index = next(p for p in pla["pagines"] if p["tipus"] == "index")
    assert [e["titol"] for e in index["index"]] == ["Cançó 0"]


def test_cancons_excloses():
    pla = maquetacio.pla(_canconer([_canco(0), _canco(1, inclosa=False)]))
    assert [c["id"] for c in pla["cancons"]] == ["c0"]


def test_index_de_diverses_pagines():
    n = plantilles.ENTRADES_PER_PAGINA_INDEX + 1
    pla = maquetacio.pla(_canconer([_canco(i, pagines=1) for i in range(n)]))
    index = [p for p in pla["pagines"] if p["tipus"] == "index"]
    assert len(index) == 2 and len(index[0]["index"]) == plantilles.ENTRADES_PER_PAGINA_INDEX and len(index[1]["index"]) == 1


def test_pagina_d_acords_al_principi_o_al_final():
    cancons = [_canco(0), _canco(1)]
    inici = maquetacio.pla(_canconer(cancons, pagina_acords=True))
    assert tipus(inici)[:3] == ["portada", "index", "acords"]
    assert inici["pagines"][2]["diagrames"]
    final = maquetacio.pla(_canconer(cancons, pagina_acords=True, posicio_acords="final"))
    assert tipus(final)[-2:] == ["acords", "contraportada"] and final["total"] % 4 == 0


def test_mestra_segons_la_paritat_i_numeros():
    pla = maquetacio.pla(_canconer([_canco(0)]))
    p4, p5 = pla["pagines"][3], pla["pagines"][4]
    assert (p4["numero"], p4["costat"], p5["costat"]) == (4, "parell", "senar")
    assert p4["mestra"]["elements"][0]["alineacio"] == "left"
    assert p5["mestra"]["elements"][0]["alineacio"] == "right"
    assert pla["pagines"][0]["mestra"] is None  # portada
    assert p4["context"]["pagina"] == 4 and p4["context"]["titol"] == "Cançó 0"


def test_transport_als_marcs_i_a_la_llista_d_acords():
    pla = maquetacio.pla(_canconer([_canco(0, transport=2)]))
    pagina = pla["pagines"][3]
    marc = next(e for e in pagina["elements"] if e["tipus"] == "lletra")
    assert '"D"' in str(marc["doc"]).replace("'", '"') and pagina["context"]["acords"] == "D · A"


def test_no_es_modifica_el_canconer_original():
    k = _canconer([_canco(0, transport=3)])
    abans = copy.deepcopy(k)
    maquetacio.pla(k)
    assert k == abans


def test_amb_dades_de_la_base_de_dades():
    from canconer import exemple
    k = basedades.carrega_canconer(exemple.crea_exemple())
    pla = maquetacio.pla(k)
    assert pla["total"] % 4 == 0 and len(pla["cancons"]) == 4
