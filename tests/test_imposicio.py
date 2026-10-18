from io import BytesIO

import pytest
from pypdf import PdfReader, PdfWriter

from canconer.imposicio import A4_ALT, A4_AMPLE, A5_ALT, A5_AMPLE, imposa, ordre_imposicio, parelles


def test_n4():
    assert parelles(4) == [(4, 1), (2, 3)]


def test_n8():
    assert parelles(8) == [(8, 1), (2, 7), (6, 3), (4, 5)]


def test_n12_exemple_de_l_enunciat():
    assert parelles(12) == [(12, 1), (2, 11), (10, 3), (4, 9), (8, 5), (6, 7)]


def test_n16():
    assert parelles(16) == [(16, 1), (2, 15), (14, 3), (4, 13), (12, 5), (6, 11), (10, 7), (8, 9)]


@pytest.mark.parametrize("n", [4, 8, 12, 16, 40])
def test_cada_pagina_surt_un_cop_i_els_costats_sumen_n_mes_1(n):
    cares = ordre_imposicio(n)
    pagines = [p for c in cares for p in (c.esquerra, c.dreta)]
    assert sorted(pagines) == list(range(1, n + 1))
    # En un llibret a cavallet, les dues pàgines d'una cara sempre sumen N + 1.
    assert all(c.esquerra + c.dreta == n + 1 for c in cares)
    assert [c.costat for c in cares[:2]] == ["davant", "darrere"]
    assert len(cares) == n // 2


@pytest.mark.parametrize("n", [0, 2, 6, 10])
def test_rebutja_si_no_es_multiple_de_4(n):
    with pytest.raises(ValueError):
        ordre_imposicio(n)


def _pdf_a5(n: int) -> bytes:
    escriptor = PdfWriter()
    for _ in range(n):
        escriptor.add_blank_page(width=A5_AMPLE, height=A5_ALT)
    sortida = BytesIO()
    escriptor.write(sortida)
    return sortida.getvalue()


def test_pdf_imposat_te_mida_a4_horitzontal():
    lector = PdfReader(BytesIO(imposa(_pdf_a5(12))))
    assert len(lector.pages) == 6
    caixa = lector.pages[0].mediabox
    assert float(caixa.width) == pytest.approx(A4_AMPLE, abs=0.5)
    assert float(caixa.height) == pytest.approx(A4_ALT, abs=0.5)


def test_cares_separades_per_a_impressores_sense_doble_cara():
    a5 = _pdf_a5(12)
    assert len(PdfReader(BytesIO(imposa(a5, costat="davant"))).pages) == 3
    assert len(PdfReader(BytesIO(imposa(a5, costat="darrere"))).pages) == 3


def test_vora_llarga_gira_nomes_les_cares_del_darrere():
    lector = PdfReader(BytesIO(imposa(_pdf_a5(8), gira_darrere=True)))
    import re
    # Matriu de rotació de 180°: -1 ~0 ~0 -1 (el sinus surt com a 1e-16).
    girades = [bool(re.search(rb"(^|\s)-1 [-\d.e]+ [-\d.e]+ -1 ", p.get_contents().get_data())) for p in lector.pages]
    assert girades == [False, True, False, True]  # davant, darrere, davant, darrere
    assert all(round(float(p.mediabox.width)) == round(A4_AMPLE) for p in lector.pages)
