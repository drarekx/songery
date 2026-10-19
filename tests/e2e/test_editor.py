"""Editor de cançoners al navegador: zoom, menú del botó dret, enganxar imatges, columnes
redimensionables, format del text seleccionat i la vista prèvia de la biblioteca."""

from __future__ import annotations

import json
from pathlib import Path

from .conftest import canconer_exemple

LLEST = "document.querySelector('.pagina-editor') && document.fonts.status === 'loaded'"


def obre_editor(pagina, servidor) -> str:
    url = canconer_exemple(servidor)
    pagina.obre(url, LLEST)
    pagina.espera("document.querySelectorAll('.capa-elements [data-id]').length > 0")
    return url


def test_zoom_la_vista_previa_coincideix_amb_el_redibuix(pagina, servidor):
    """Mentre es fa zoom, el contingut s'escala en viu; quan es redibuixa, no ha de saltar de lloc."""
    obre_editor(pagina, servidor)
    resultats = pagina.avalua("""(async () => {
      const espera = (ms) => new Promise((r) => setTimeout(r, ms));
      const L = document.getElementById('llenc');
      const r = L.getBoundingClientRect();
      const pos = () => { const q = document.querySelector('.pagina-editor').getBoundingClientRect(); return [q.left, q.top, q.width].map(Math.round); };
      const sortida = [];
      for (const [x, y, n, dy] of [[0.3, 0.4, 20, -6], [0.7, 0.6, 15, -8], [0.5, 0.5, 25, 5]]) {
        for (let i = 0; i < n; i++) {
          L.dispatchEvent(new WheelEvent('wheel', { deltaY: dy, ctrlKey: true, clientX: r.left + r.width * x, clientY: r.top + r.height * y, bubbles: true, cancelable: true }));
          await espera(16);
        }
        const previa = pos();
        await espera(500);
        sortida.push([previa, pos()]);
      }
      return sortida;
    })()""")
    for previa, final in resultats:
        assert all(abs(a - b) <= 2 for a, b in zip(previa, final)), (previa, final)


def test_menu_del_boto_dret_a_la_zona_del_voltant(pagina, servidor):
    obre_editor(pagina, servidor)
    abans = pagina.avalua("document.querySelectorAll('.capa-elements [data-id]').length")
    x, y = pagina.avalua("(() => { const r = document.getElementById('llenc').getBoundingClientRect(); return [r.left + 20, r.bottom - 30]; })()")
    pagina.clic_dret(x, y)
    pagina.espera("document.querySelector('.menu-context')")
    opcions = pagina.avalua("[...document.querySelectorAll('.menu-context button')].map((b) => b.textContent.trim())")
    for text in ("Desfés", "Afegeix", "Pàgina", "Zoom", "Mou el llenç"):
        assert any(o.startswith(text) for o in opcions), (text, opcions)
    pagina.avalua("[...document.querySelectorAll('.menu-context button')].find((b) => b.textContent.includes('Afegeix')).dispatchEvent(new Event('mouseenter'))")
    pagina.espera("document.querySelectorAll('.menu-context').length === 2")
    pagina.avalua("[...document.querySelectorAll('.menu-context')[1].querySelectorAll('button')].find((b) => b.textContent.includes('Rectangle')).click()")
    pagina.espera(f"document.querySelectorAll('.capa-elements [data-id]').length === {abans + 1}")


def test_enganxar_una_imatge_del_porta_retalls(pagina, servidor):
    obre_editor(pagina, servidor)
    abans = pagina.avalua("document.querySelectorAll('.capa-elements img').length")
    pagina.avalua("""(async () => {
      const c = document.createElement('canvas'); c.width = 300; c.height = 200;
      c.getContext('2d').fillRect(0, 0, 300, 200);
      const blob = await new Promise((r) => c.toBlob(r, 'image/png'));
      const dt = new DataTransfer();
      dt.items.add(new File([blob], 'captura.png', { type: 'image/png' }));
      document.body.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
    })()""")
    pagina.espera(f"document.querySelectorAll('.capa-elements img').length === {abans + 1}", 15)


def test_les_columnes_es_redimensionen_i_es_recorden(pagina, servidor, tmp_path):
    url = obre_editor(pagina, servidor)
    for selector, dx in (("#panell-props .nansa-columna", -150), ("#panell-llenc .nansa-columna", 80)):
        x, y = pagina.avalua(f"(() => {{ const r = document.querySelector('{selector}').getBoundingClientRect(); return [r.left + 4, r.top + 300]; }})()")
        pagina.arrossega(x, y, x + dx, y)
    pagina.espera("document.getElementById('panell-props').offsetWidth === 470 && document.getElementById('panell-llista').offsetWidth === 336")
    pagina.obre(url, LLEST)
    assert pagina.avalua("[document.getElementById('panell-props').offsetWidth, document.getElementById('panell-llista').offsetWidth]") == [470, 336]
    preferencies = json.loads((Path(tmp_path) / "dades" / "preferencies.json").read_text())
    assert preferencies["editor.amplePropietats"] == 470 and preferencies["editor.ampleLlista"] == 336


def test_tipografia_i_colors_del_text_seleccionat(pagina, servidor):
    obre_editor(pagina, servidor)
    pagina.avalua("""(async () => {
      const marc = document.querySelector('.marc-lletra');
      const r = marc.getBoundingClientRect();
      marc.dispatchEvent(new MouseEvent('dblclick', { bubbles: true, clientX: r.left + 40, clientY: r.top + 60 }));
      await new Promise((res) => setTimeout(res, 400));
      marc._editor.commands.setTextSelection({ from: 40, to: 60 });
    })()""")
    pagina.espera("document.getElementById('bombolla').classList.contains('flex')")
    marques = pagina.avalua("""(async () => {
      const espera = (ms) => new Promise((r) => setTimeout(r, ms));
      document.getElementById('font-seleccio').click();
      await espera(300);
      document.querySelectorAll('#llista-fonts button')[2].click();
      for (const [id, valor] of [['color-seleccio', 'cmyk(0,100,100,0)'], ['fons-seleccio', '#ffee88']]) {
        const input = document.getElementById(id);
        input.value = valor;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        await espera(150);
      }
      const marques = new Set();
      document.querySelector('.marc-lletra')._editor.state.doc.descendants((n) => n.marks?.forEach((m) => marques.add(m.type.name)));
      return [...marques];
    })()""")
    assert {"font", "color", "fons"} <= set(marques)


def test_vista_previa_de_la_biblioteca_amb_pagines(pagina, servidor):
    canconer_exemple(servidor)
    pagina.obre(servidor + "/biblioteca", "document.getElementById('previa-pagines')?.textContent")
    pagina.espera("document.getElementById('previa-pagines').textContent === 'pàg. 1 de 2'")
    pagina.avalua("document.getElementById('previa-seguent').click()")
    pagina.espera("document.getElementById('previa-pagines').textContent === 'pàg. 2 de 2'")
    pagina.avalua("document.getElementById('previa').dispatchEvent(new WheelEvent('wheel', { deltaY: -100, bubbles: true, cancelable: true }))")
    pagina.espera("document.getElementById('previa-pagines').textContent === 'pàg. 1 de 2'")


def test_marges_del_canconer_com_a_guies_que_enganxen(pagina, servidor):
    """Els marges es trien a Opcions; a l'editor surten a cada pàgina i els elements s'hi enganxen."""
    import urllib.parse
    import urllib.request

    url = canconer_exemple(servidor)
    id_canconer = url.rstrip("/").rsplit("/", 1)[-1]
    dades = urllib.parse.urlencode({"marges": "encolat"}).encode()
    urllib.request.urlopen(urllib.request.Request(f"{servidor}/canconer/{id_canconer}/marges", data=dades))
    pagina.obre(url, LLEST)
    pagina.espera("document.querySelectorAll('.capa-elements [data-id]').length > 0")
    assert pagina.avalua("document.querySelectorAll('.pagina-editor').length") == pagina.avalua(
        "document.querySelectorAll('.pagina-editor .guia-marges').length") == 2
    # Pàgina de la dreta (senar): el plec, de 9 mm, és a l'esquerra. El marc de lletra hi és a 13 mm;
    # arrossegat 3,4 mm cap a l'esquerra (a 9,6 mm), s'enganxa a la guia dels 9 mm.
    x, y, px_mm = pagina.avalua("""(() => {
      const caixa = document.querySelectorAll('.pagina-editor')[1];
      const marc = caixa.querySelector('.marc-lletra');
      const r = marc.getBoundingClientRect();
      return [r.left + 30, r.top + 30, caixa.getBoundingClientRect().width / 148];
    })()""")
    pagina.arrossega(x, y, x - 3.4 * px_mm, y)
    pagina.espera("document.querySelector('#panell-propietats input')")
    valor_x = pagina.avalua("""(() => {
      const etiqueta = [...document.querySelectorAll('#panell-propietats label')].find((l) => l.textContent.trim().startsWith('X'));
      return Number(etiqueta.querySelector('input').value);
    })()""")
    assert valor_x == 9


def test_omplir_la_pagina_3_en_blanc_des_de_tot_el_llibret(pagina, servidor):
    obre_editor(pagina, servidor)
    pagina.avalua("[...document.querySelectorAll('#panell-llista button')].find((b) => b.textContent.includes('Tot el llibret')).click()")
    pagina.espera("document.querySelector('.vista-llibre .pagina-blanca')")
    assert pagina.avalua("document.querySelector('.vista-llibre .pagina-blanca').title").startswith("Pàgina 3")
    pagina.avalua("document.querySelector('.vista-llibre .pagina-blanca').click()")
    # S'obre la pàgina lliure nova, a la pàgina 3, i la primera cançó continua a la 4.
    pagina.espera("document.querySelector('.peu-pagina-editor')?.textContent === 'Pàgina 3'", 15)
    llista = pagina.avalua("[...document.querySelectorAll('#panell-llista li[data-id]')].slice(0, 2).map((li) => li.textContent.replace(/\\s+/g, ' ').trim())")
    assert "Pàgina lliure" in llista[0] and "pàg. 3" in llista[0]
    assert "pàg. 4" in llista[1]


def test_una_pagina_omplerta_i_deixada_buida_es_desfa(pagina, servidor):
    obre_editor(pagina, servidor)
    llibre = "[...document.querySelectorAll('#panell-llista button')].find((b) => b.textContent.includes('Tot el llibret')).click()"
    pagina.avalua(llibre)
    pagina.espera("document.querySelector('.vista-llibre .pagina-blanca')")
    pagina.avalua("document.querySelector('.vista-llibre .pagina-blanca').click()")
    pagina.espera("document.querySelector('.peu-pagina-editor')?.textContent === 'Pàgina 3'", 15)
    assert "buida" in pagina.avalua("document.querySelector('#panell-llista li[data-id]').textContent")
    # Se'n surt sense posar-hi res: es desfà i la pàgina 3 torna a ser en blanc.
    pagina.avalua(llibre)
    pagina.espera("document.querySelector('.vista-llibre .pagina-blanca')?.title.startsWith('Pàgina 3')", 15)
    assert not pagina.avalua("[...document.querySelectorAll('#panell-llista li[data-id]')].some((li) => li.textContent.includes('Pàgina lliure'))")


def test_estils_propis_crear_aplicar_i_esborrar(pagina, servidor):
    """Issue #11: un estil nou surt a la llista d'estils dels elements; no s'esborra mentre es fa servir."""
    obre_editor(pagina, servidor)
    pagina.avalua("document.querySelector('[data-pestanya=estils]').click()")
    pagina.espera("[...document.querySelectorAll('#panell-estils button')].some((b) => b.textContent.includes('Estil nou'))")
    pagina.avalua("[...document.querySelectorAll('#panell-estils button')].find((b) => b.textContent.includes('Estil nou')).click()")
    pagina.espera("document.querySelector('dialog[open] input')")
    pagina.avalua("""(() => { const i = document.querySelector('dialog[open] input'); i.value = 'Destacat'; i.dispatchEvent(new Event('input'));
                     document.querySelector('dialog[open] button.btn-primari').click(); })()""")
    pagina.espera("[...document.querySelectorAll('#panell-estils li')].some((li) => li.textContent.includes('Destacat'))")
    # S'aplica a un text de la pàgina.
    pagina.avalua("""(async () => {
      const text = [...document.querySelectorAll('.capa-elements [data-tipus=text]')][0];
      const r = text.getBoundingClientRect();
      text.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, clientX: r.left + 3, clientY: r.top + 3, button: 0, isPrimary: true }));
      window.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, clientX: r.left + 3, clientY: r.top + 3, button: 0, isPrimary: true }));
      document.querySelector('[data-pestanya=propietats]').click();
    })()""")
    pagina.espera("[...document.querySelectorAll('#panell-propietats select option')].some((o) => o.textContent === 'Destacat')")
    pagina.avalua("""(() => { const s = [...document.querySelectorAll('#panell-propietats select')].find((x) => [...x.options].some((o) => o.textContent === 'Destacat'));
                     s.value = [...s.options].find((o) => o.textContent === 'Destacat').value; s.dispatchEvent(new Event('change')); })()""")
    pagina.espera("document.querySelector('.capa-elements [data-tipus=text][class*=estil-propi_]')")
    # Mentre es fa servir, no s'esborra.
    pagina.avalua("document.querySelector('[data-pestanya=estils]').click()")
    pagina.avalua("""(() => { const li = [...document.querySelectorAll('#panell-estils li')].find((x) => x.textContent.includes('Destacat'));
                     li.querySelector('details').open = true; [...li.querySelectorAll('button')].find((b) => b.textContent.startsWith('Esborra')).click(); })()""")
    pagina.espera("document.querySelector('dialog[open]')?.textContent.includes(\"s'està fent servir\")")


def test_ajuda_de_l_editor(pagina, servidor):
    """#12: el botó «?» (o la tecla ?) obre l'ajuda amb les eines i les dreceres; Esc la tanca."""
    obre_editor(pagina, servidor)
    pagina.avalua("document.querySelector('[aria-label=Ajuda]').click()")
    pagina.espera("document.querySelector('#ajuda-editor')")
    text = pagina.avalua("document.querySelector('#ajuda-editor').textContent")
    assert "Marc de lletra amb acords" in text and "Duplica la pàgina" in text and "Dreceres" in text
    caixa = pagina.avalua("(() => { const r = document.querySelector('#ajuda-editor').getBoundingClientRect(); return [r.left, r.right, r.bottom, innerWidth, innerHeight]; })()")
    assert caixa[0] >= 0 and caixa[1] <= caixa[3] and caixa[2] <= caixa[4]  # dins de la finestra
    pagina.avalua("document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))")
    pagina.espera("!document.querySelector('#ajuda-editor')")
    pagina.avalua("document.body.dispatchEvent(new KeyboardEvent('keydown', { key: '?', bubbles: true }))")
    pagina.espera("document.querySelector('#ajuda-editor')")


def test_editar_una_canco_des_de_la_biblioteca_sense_canconer(pagina, servidor):
    """#13: l'editor complet per a una cançó, sense cançoner; els canvis van a la cançó (i els veuen els
    cançoners que la segueixen). El que és del cançoner no hi surt."""
    import json as json_
    import urllib.request

    url = canconer_exemple(servidor)
    k = json_.loads(urllib.request.urlopen(url.replace("/canconer/", "/api/canconer/")).read())
    canco = k["cancons"][0]["id"]
    pagina.obre(f"{servidor}/biblioteca/{canco}/edita", LLEST)
    pagina.espera("document.querySelectorAll('.capa-elements [data-id]').length > 0")
    llista = pagina.avalua("document.getElementById('panell-llista').textContent")
    assert "fora de cap cançoner" in llista and "Tot el llibret" not in llista and "Pàgines mestres" not in llista
    assert "Cançoner d'exemple" in llista  # el disseny és el del cançoner on surt
    pagina.avalua("document.querySelector('[data-pestanya=canco]').click()")
    assert "Transport" not in pagina.avalua("document.querySelector('[data-panell-pestanya=canco]').textContent")
    pagina.avalua("document.querySelector('[data-pestanya=estils]').click()")
    assert pagina.avalua("[...document.querySelectorAll('#panell-estils fieldset')].every((f) => f.disabled)")
    # S'edita la lletra i es desa a la cançó.
    pagina.avalua("""(async () => {
      const marc = document.querySelector('.marc-lletra');
      const r = marc.getBoundingClientRect();
      marc.dispatchEvent(new MouseEvent('dblclick', { bubbles: true, clientX: r.left + 40, clientY: r.top + 60 }));
      await new Promise((res) => setTimeout(res, 400));
      marc._editor.commands.insertContentAt(1, 'EDITADA DES DE LA BIBLIOTECA ');
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    })()""")
    pagina.espera("document.getElementById('text-estat').textContent.includes('Tot desat')", 10)
    desada = json_.loads(urllib.request.urlopen(f"{servidor}/api/canco/{canco}").read())
    assert "EDITADA DES DE LA BIBLIOTECA" in json_.dumps(desada["contingut"], ensure_ascii=False)
    k = json_.loads(urllib.request.urlopen(url.replace("/canconer/", "/api/canconer/")).read())
    assert "EDITADA DES DE LA BIBLIOTECA" in json_.dumps(k["cancons"][0]["contingut"], ensure_ascii=False)


def test_selector_d_autor_i_filtre_de_la_biblioteca(pagina, servidor):
    """#14: a la pestanya Cançó, l'autor es tria o es crea amb el selector; la biblioteca hi filtra."""
    import json as json_
    import urllib.request

    obre_editor(pagina, servidor)
    pagina.avalua("document.querySelector('[data-pestanya=canco]').click()")
    pagina.espera("document.getElementById('autor-canco')")
    pagina.avalua("""(async () => {
      const i = document.getElementById('autor-canco');
      i.focus(); i.value = 'Enric Morera'; i.dispatchEvent(new Event('input', { bubbles: true }));
      await new Promise((r) => setTimeout(r, 400));
      [...document.querySelectorAll('[role=option]')].find((o) => o.textContent.includes('Crea')).dispatchEvent(new MouseEvent('click', { bubbles: true }));
    })()""")
    pagina.espera("document.getElementById('text-estat').textContent.includes('Tot desat')", 10)
    autors = json_.loads(urllib.request.urlopen(f"{servidor}/api/autors?q=morera").read())
    assert [a["nom"] for a in autors] == ["Enric Morera"] and autors[0]["cancons"] == 1
    pagina.obre(f"{servidor}/biblioteca?autor={autors[0]['id']}", "document.querySelector('.fila-biblioteca')")
    files = pagina.avalua("document.querySelectorAll('.fila-biblioteca').length")
    assert files == 1 and "Enric Morera" in pagina.avalua("document.querySelector('.fila-biblioteca').textContent")
