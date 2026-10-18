"""Interfície web (Flask): editor de pàgines, biblioteca, opcions, impressió i API JSON."""

from __future__ import annotations

import re
import traceback
import unicodedata
from datetime import datetime
from html import escape

from flask import (Flask, Response, abort, jsonify, redirect, render_template, request,
                   send_file, url_for)

from . import basedades as bd
from . import actualitzacions, actualitzador, cmyk, diagrames, disseny, document, exemple, intercanvi, maquetacio, marges, pdf, plantilles, tipografies, videos

TIPUS_PDF = {
    "a5": "llibret-A5",
    "a4": "imprimir-A4-doble-cara",
    "a4-vora-llarga": "imprimir-A4-doble-cara-vora-llarga",
    "darrere-girat": "imprimir-A4-cares-darrere-girades",
    "davant": "imprimir-A4-cares-davanteres",
    "darrere": "imprimir-A4-cares-darrere",
    "darrere-invers": "imprimir-A4-cares-darrere-ordre-invers",
    "instruccions": "instruccions-impressio",
    "a5-cmyk": "llibret-A5-impremta-CMYK",
    "a4-cmyk": "imprimir-A4-impremta-CMYK",
}
MIDA_MAXIMA_IMATGE = 12 * 1024 * 1024
MIDA_MAXIMA_FONT = 15 * 1024 * 1024


def _nom_fitxer(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower() or "canconer"


def registra_error(text: str) -> str:
    """Afegeix un error a <dades>/errors.log (es conserva només l'última part) i en retorna el camí."""
    cami = bd.DIRECTORI / "errors.log"
    try:
        bd.DIRECTORI.mkdir(parents=True, exist_ok=True)
        anterior = cami.read_text("utf-8", errors="replace")[-200_000:] if cami.exists() else ""
        cami.write_text(anterior + text, "utf-8")
    except OSError:
        pass
    return str(cami)


def _pagina_error(missatge: str, detall: str, registre: str) -> str:
    """Pàgina d'error autònoma (no depèn de les plantilles, per si l'error ve d'allà)."""
    return f"""<!doctype html><html lang="ca"><meta charset="utf-8"><title>Error · Cançoners</title>
<body style="font:15px/1.5 -apple-system,sans-serif;background:#f6f4ef;color:#1b1a17;max-width:46rem;margin:3rem auto;padding:0 1rem">
<h1 style="font-size:1.6rem">Alguna cosa ha fallat</h1>
<p>Cançoners {escape(actualitzacions.versio_actual())} no ha pogut fer això. Les teves dades no s'han tocat.</p>
<p style="background:#fbe9e7;border-radius:6px;padding:.75rem 1rem;color:#8c1d14"><strong>{escape(missatge)}</strong></p>
<p>L'error s'ha desat a <code>{escape(registre)}</code>. Si tornes a obrir l'app o la pàgina i continua passant,
envia aquest fitxer (o el detall de sota) per poder-ho arreglar.</p>
<p><a href="/">Torna a l'inici</a></p>
<details><summary>Detall tècnic</summary><pre style="white-space:pre-wrap;font-size:12px">{escape(detall)}</pre></details>
</body></html>"""


def fa_temps(moment: str) -> str:
    """«avui», «ahir», «fa 3 dies», «fa 2 setmanes» o la data, a partir d'una data ISO."""
    try:
        dia = datetime.fromisoformat(moment).date()
    except (TypeError, ValueError):
        return ""
    dies = (datetime.now().date() - dia).days
    if dies <= 0:
        return "avui"
    if dies == 1:
        return "ahir"
    if dies < 14:
        return f"fa {dies} dies"
    if dies < 60:
        return f"fa {dies // 7} setmanes"
    return dia.strftime("%d/%m/%Y")


def _enter(valor, defecte: int = 0) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return defecte


def crea_app() -> Flask:
    app = Flask(__name__)
    # Prou gran per importar cançoners exportats (amb imatges i tipografies); cada ruta limita el seu.
    app.config["MAX_CONTENT_LENGTH"] = intercanvi.MIDA_MAXIMA + 1024 * 1024
    # Les plantilles es rellegeixen si canvien (útil mentre es retoca el disseny).
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    @app.errorhandler(500)
    def error_intern(e):
        """Desa l'error amb tot el detall i explica què ha passat (l'app de Mac no té consola)."""
        original = getattr(e, "original_exception", None) or e
        detall = "".join(traceback.format_exception(original))
        missatge = f"{type(original).__name__}: {original}"
        registre = registra_error(f"\n=== {datetime.now().isoformat(timespec='seconds')} · "
                                  f"v{actualitzacions.versio_actual()} · {request.method} {request.full_path}\n{detall}")
        if request.path.startswith("/api/") or request.accept_mimetypes.best == "application/json":
            return jsonify({"error": f"Error intern: {missatge}", "registre": registre}), 500
        return Response(_pagina_error(missatge, detall, registre), status=500, mimetype="text/html")

    def canconer_o_404(id_canconer: str) -> dict:
        try:
            return bd.carrega_canconer(id_canconer)
        except KeyError:
            abort(404)

    def meta_o_404(id_canconer: str) -> dict:
        try:
            return bd.meta_canconer(id_canconer)
        except KeyError:
            abort(404)

    def o_404(funcio, *args, **kwargs):
        try:
            return funcio(*args, **kwargs)
        except KeyError:
            abort(404)

    def fonts() -> list[dict]:
        return tipografies.llista(bd.tipografies_importades())

    # Números a la catalana, sense decimals sobrers: 14 → «14», 2.5 → «2,5».
    app.jinja_env.filters["num"] = lambda v, decimals=1: f"{round(float(v), decimals):g}".replace(".", ",")

    @app.context_processor
    def fonts_per_a_les_plantilles():
        """Llista de tipografies per al motor de dibuix (editor i pàgina d'impressió)."""
        return {"tipografies_navegador": lambda: tipografies.per_al_navegador(fonts()),
                "versio_app": actualitzacions.versio_actual()}

    def canconer_impressio(id_canconer: str) -> dict:
        """Cançoner per imprimir. L'instrument dels diagrames es pot triar a l'hora d'imprimir
        (?instrument=guitarra|ukulele) sense canviar el cançoner desat. Com que forma part de les
        dades, la memòria cau del PDF distingeix cada versió."""
        c = canconer_o_404(id_canconer)
        instrument = request.args.get("instrument")
        if instrument in ("guitarra", "ukulele"):
            c = {**c, "instrument": instrument}
        # Mestra de marges per a l'enquadernació: la desada al cançoner (o «Sense marges»).
        return {**c, "marge": bd.carrega_marge(c.get("marges"))}

    def url_interna(ruta: str) -> str:
        """URL amb què el motor de PDF arriba a aquesta aplicació.

        Amb el Chromium local és la mateixa adreça local; amb Gotenberg (dins de Docker), a través
        de host.docker.internal.
        """
        port = request.host.rsplit(":", 1)[-1] if ":" in request.host else "80"
        if pdf.URL_INTERNA:
            base = pdf.URL_INTERNA
        elif pdf.usa_gotenberg():
            base = f"http://host.docker.internal:{port}"
        else:
            base = f"http://127.0.0.1:{port}"
        return base.rstrip("/") + ruta

    # ------------------------------------------------------------ Pàgines

    @app.get("/")
    def inici():
        # Cada cançoner es mostra com un llibret amb la seva portada real (la dibuixa el navegador
        # amb el mateix motor que l'editor i el PDF) i el nombre de pàgines.
        canconers = []
        for c in bd.llista_canconers():
            try:
                pla = maquetacio.pla(bd.carrega_canconer(c["id"]))
            except Exception:  # noqa: BLE001 - un cançoner malmès no ha de tombar la pàgina d'inici
                pla = None
            canconers.append({**c, "pagines": pla["total"] if pla else None,
                              "portada": pla["pagines"][0] if pla else None, "editat": fa_temps(c["actualitzat"])})
        return render_template("inici.html", canconers=canconers, error=request.args.get("error"))

    @app.post("/canconer/<id_canconer>/duplica")
    def canconer_duplica(id_canconer):
        meta_o_404(id_canconer)
        nou = intercanvi.duplica(id_canconer, duplicar_cancons=bool(request.form.get("duplicar_cancons")))
        return redirect(url_for("canconer", id_canconer=nou))

    @app.get("/canconer/<id_canconer>/exporta")
    def canconer_exporta(id_canconer):
        c = meta_o_404(id_canconer)
        nom = f"{_nom_fitxer(c['titol'])}.canconer"
        return Response(intercanvi.exporta(id_canconer), mimetype="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="{nom}"'})

    @app.post("/canconer/importa")
    def canconer_importa():
        fitxer = request.files.get("fitxer")
        if not fitxer:
            return redirect(url_for("inici", error="Tria un fitxer .canconer per importar."))
        try:
            nou = intercanvi.importa(fitxer.read(intercanvi.MIDA_MAXIMA + 1))
        except ValueError as e:  # ImportacioInvalida o dades que no passen la validació
            return redirect(url_for("inici", error=str(e) or "No s'ha pogut importar el fitxer."))
        return redirect(url_for("canconer", id_canconer=nou))

    @app.post("/canconer/nou")
    def canconer_nou():
        return redirect(url_for("canconer", id_canconer=bd.crea_canconer(request.form.get("titol", "").strip())))

    @app.post("/canconer/exemple")
    def canconer_exemple():
        return redirect(url_for("canconer", id_canconer=exemple.crea_exemple()))

    @app.get("/canconer/<id_canconer>")
    def canconer(id_canconer):
        """Editor de pàgines: és la pàgina principal de cada cançoner."""
        c = meta_o_404(id_canconer)
        marge = bd.carrega_marge(c.get("marges"))
        return render_template("editor.html", c=c, seccio="editor",
                               actual=request.args.get("canco"), especial=request.args.get("especial"),
                               marge={**marge, "escala": marges.escala(marge)} if marges.actiu(marge) else None)

    @app.route("/canconer/<id_canconer>/opcions", methods=["GET", "POST"])
    def canconer_opcions(id_canconer):
        c = meta_o_404(id_canconer)
        if request.method == "POST":
            f = request.form
            bd.desa_meta(id_canconer, {
                "titol": f.get("titol", "").strip() or "Cançoner",
                "subtitol": f.get("subtitol", "").strip(),
                "any": f.get("any", "").strip(),
                "contraportada": f.get("contraportada", "").strip(),
                "pagina_acords": bool(f.get("pagina_acords")),
                "posicio_acords": "final" if f.get("posicio_acords") == "final" else "inici",
                "instrument": "ukulele" if f.get("instrument") == "ukulele" else "guitarra",
            })
            return redirect(url_for("canconer_opcions", id_canconer=id_canconer, desat=1))
        return render_template("opcions.html", c=c, seccio="opcions", desat=request.args.get("desat"))

    @app.get("/canconer/<id_canconer>/portada")
    def canconer_portada(id_canconer):
        return redirect(url_for("canconer", id_canconer=id_canconer, especial="portada"))

    @app.get("/canconer/<id_canconer>/imprimir")
    def canconer_imprimir(id_canconer):
        c = canconer_impressio(id_canconer)
        return render_template("imprimir.html", c=c, seccio="imprimir", pla=maquetacio.pla(c), v=pdf.clau(c),
                               instrument=c["instrument"], marges=bd.llista_marges(), gs=bool(cmyk.ghostscript()),
                               escala_marges=marges.escala(c["marge"]))

    @app.post("/canconer/<id_canconer>/marges")
    def canconer_tria_marges(id_canconer):
        meta_o_404(id_canconer)
        bd.desa_meta(id_canconer, {"marges": bd.carrega_marge(request.form.get("marges"))["id"]})
        return redirect(url_for("canconer_imprimir", id_canconer=id_canconer,
                                instrument=request.form.get("instrument") or None))

    def plantilla_marge() -> dict:
        return {k: v for k, v in marges.PREDEFINIDES[1].items() if k not in ("id", "nom")}

    def _torna_segura(url: str | None) -> str | None:
        """Només s'accepten rutes internes per tornar enrere."""
        return url if url and url.startswith("/") and not url.startswith("//") else None

    @app.post("/canconer/<id_canconer>/index")
    def canconer_tria_index(id_canconer):
        """Índex de cançons al PDF, sí o no."""
        meta_o_404(id_canconer)
        bd.desa_meta(id_canconer, {"pagina_index": bool(request.form.get("pagina_index"))})
        return redirect(url_for("canconer_imprimir", id_canconer=id_canconer,
                                instrument=request.form.get("instrument") or None))

    @app.post("/canconer/<id_canconer>/qr")
    def canconer_tria_qr(id_canconer):
        """Índex de QR dels vídeos al PDF (sí o no, i on)."""
        c = meta_o_404(id_canconer)
        posicio = request.form.get("posicio_qr", c.get("posicio_qr"))
        bd.desa_meta(id_canconer, {"pagina_qr": bool(request.form.get("pagina_qr")),
                                   "posicio_qr": "inici" if posicio == "inici" else "final"})
        return redirect(url_for("canconer_imprimir", id_canconer=id_canconer,
                                instrument=request.form.get("instrument") or None))

    @app.get("/actualitzacio")
    def actualitzacio():
        pot, motiu = actualitzador.pot_actualitzar()
        return render_template("actualitzacio.html", versio=actualitzacions.versio_actual(), pot=pot, motiu=motiu,
                               inicia=bool(request.args.get("inicia")) and pot)

    @app.get("/api/actualitzacio/comprova")
    def api_actualitzacio_comprova():
        try:
            nova = actualitzacions.comprova()
        except OSError as e:
            return jsonify({"error": f"No es pot connectar amb GitHub ({e})."}), 503
        return jsonify({"actual": actualitzacions.versio_actual(), "nova": nova})

    @app.post("/api/actualitzacio/inicia")
    def api_actualitzacio_inicia():
        pot, motiu = actualitzador.pot_actualitzar()
        if not pot:
            return jsonify({"error": motiu}), 400
        if pdf._bloqueig.locked():
            return jsonify({"error": "S'està generant un PDF. Torna-ho a provar d'aquí a un moment."}), 409
        actualitzador.inicia()
        return jsonify({"ok": True})

    @app.get("/api/actualitzacio/estat")
    def api_actualitzacio_estat():
        return jsonify({k: v for k, v in actualitzador.estat.items() if k != "sortir"}
                       | {"versio": actualitzacions.versio_actual()})

    @app.get("/marges")
    def marges_llista():
        return render_template("marges.html", marges=bd.llista_marges(), torna=_torna_segura(request.args.get("torna")),
                               sense_marges=marges.SENSE_MARGES, posicions=marges.posicions_forats, escala=marges.escala)

    @app.post("/marges")
    def marges_nova():
        bd.desa_marge({**plantilla_marge(), **request.form.to_dict(), "nom": request.form.get("nom") or "Marges nous"})
        return redirect(url_for("marges_llista", torna=request.form.get("torna") or None))

    @app.post("/marges/<id_marge>")
    def marges_desa(id_marge):
        try:
            if request.form.get("accio") == "esborra":
                bd.esborra_marge(id_marge)
            else:
                bd.desa_marge(request.form.to_dict(), id_marge)
        except ValueError:
            abort(400)
        except KeyError:
            abort(404)
        return redirect(url_for("marges_llista", torna=request.form.get("torna") or None) + f"#marge-{id_marge}")


    @app.get("/canconer/<id_canconer>/previsualitzacio")
    def canconer_previsualitzacio(id_canconer):
        return redirect(url_for("canconer_imprimir", id_canconer=id_canconer))

    @app.post("/canconer/<id_canconer>/esborra")
    def canconer_esborra(id_canconer):
        meta_o_404(id_canconer)
        bd.esborra_canconer(id_canconer)
        return redirect(url_for("inici"))

    @app.get("/biblioteca")
    def biblioteca():
        ordre = request.args.get("ordre", "titol")
        return render_template("biblioteca.html", cancons=bd.biblioteca(request.args.get("q", ""), ordre),
                               q=request.args.get("q", ""), ordre=ordre, seccio="biblioteca")

    @app.get("/biblioteca/<id_canco>")
    def biblioteca_canco(id_canco):
        """Fitxa d'una cançó: historial de versions, cançoners on surt i accions."""
        canco = o_404(bd.carrega_canco, id_canco)
        usos = bd.usos_canco(id_canco)
        # Les pàgines es mostren amb els estils i mestres del primer cançoner on surt (o els de defecte).
        disseny_canconer = bd.meta_canconer(usos[0]["id"]) if usos else plantilles.amb_valors_per_defecte({})
        return render_template("biblioteca_canco.html", canco=canco, usos=usos, versions=bd.versions(id_canco),
                               canconers=bd.llista_canconers(), seccio="biblioteca",
                               estils=disseny_canconer["estils"], mestres=disseny_canconer["mestres"])

    @app.post("/biblioteca/<id_canco>/afegeix")
    def biblioteca_afegeix(id_canco):
        """Afegeix la cançó a un cançoner (seguint l'esborrany) i l'obre per editar-la."""
        o_404(bd.carrega_canco, id_canco)
        id_canconer = request.form.get("canconer", "")
        meta_o_404(id_canconer)
        bd.afegeix_entrada(id_canconer, id_canco)
        return redirect(url_for("canconer", id_canconer=id_canconer, canco=id_canco))

    @app.post("/biblioteca/<id_canco>/esborra")
    def biblioteca_esborra(id_canco):
        o_404(bd.carrega_canco, id_canco)
        bd.esborra_canco(id_canco)
        return redirect(url_for("biblioteca"))

    # ------------------------------------------------------------ Pàgines que llegeix Gotenberg

    @app.get("/canconer/<id_canconer>/imprimible")
    def canconer_imprimible(id_canconer):
        """Tot el llibret dibuixat amb el mateix motor que l'editor (per convertir-lo en PDF)."""
        c = canconer_impressio(id_canconer)
        return render_template("imprimible.html", c=c, pla=maquetacio.pla(c))

    @app.get("/canconer/<id_canconer>/instruccions")
    def canconer_instruccions(id_canconer):
        c = canconer_impressio(id_canconer)
        return render_template("instruccions.html", c=c, pla=maquetacio.pla(c))

    # ------------------------------------------------------------ API: cançoner, entrades i disseny

    @app.post("/canconer/<id_canconer>/ordre")
    def canconer_ordre(id_canconer):
        """Nou ordre de les cançons (JSON: {"ordre": [id, id, ...]})."""
        meta_o_404(id_canconer)
        if not bd.ordena_entrades(id_canconer, (request.get_json(silent=True) or {}).get("ordre", [])):
            return jsonify({"error": "L'ordre no coincideix amb les cançons del cançoner."}), 400
        return jsonify({"ok": True})

    @app.get("/api/canconer/<id_canconer>")
    def api_canconer(id_canconer):
        return jsonify(canconer_o_404(id_canconer))

    @app.get("/api/canconer/<id_canconer>/pla")
    def api_pla(id_canconer):
        c = canconer_o_404(id_canconer)
        return jsonify({**maquetacio.pla(c), "versio": pdf.empremta(c)})

    @app.put("/api/canconer/<id_canconer>/disseny")
    def api_disseny(id_canconer):
        """Desa estils, pàgines mestres i/o pàgines especials (portada, índex, acords, contraportada)."""
        c = meta_o_404(id_canconer)
        d = request.get_json(silent=True) or {}
        canvis = {}
        if "estils" in d:
            canvis["estils"] = disseny.estils(d["estils"])
        if "mestres" in d:
            mestres = disseny.mestres(d["mestres"])
            if not any(m["id"] == "estandard" for m in mestres):
                return jsonify({"error": "No es pot esborrar la pàgina mestra estàndard."}), 400
            canvis["mestres"] = mestres
        if "especials" in d:
            canvis["especials"] = {**c["especials"], **disseny.especials(d["especials"])}
        if d.get("restableix") in plantilles.ESPECIALS:
            canvis["especials"] = {**c["especials"], d["restableix"]: plantilles.especials()[d["restableix"]]}
        meta = bd.desa_meta(id_canconer, canvis)
        return jsonify({k: meta[k] for k in ("estils", "mestres", "especials")})

    @app.get("/api/canconer/<id_canconer>/mestres/altres")
    def api_mestres_altres(id_canconer):
        """Pàgines mestres dels altres cançoners, per copiar-les."""
        meta_o_404(id_canconer)
        return jsonify({"canconers": [
            {"id": k["id"], "titol": k["titol"], "mestres": k["mestres"], "estils": k["estils"]}
            for k in bd.llista_canconers() if k["id"] != id_canconer]})

    @app.post("/api/canconer/<id_canconer>/mestres/copia")
    def api_mestres_copia(id_canconer):
        meta_o_404(id_canconer)
        d = request.get_json(silent=True) or {}
        meta_o_404(str(d.get("de", "")))
        noves = bd.copia_mestres(id_canconer, d["de"], [str(i) for i in d.get("mestres", [])][:20])
        meta = bd.meta_canconer(id_canconer)
        return jsonify({"noves": [m["id"] for m in noves], "mestres": meta["mestres"], "estils": meta["estils"]})

    @app.post("/api/canconer/<id_canconer>/canco")
    def api_canco_nova(id_canconer):
        """Crea una cançó nova (o una pàgina lliure) i l'afegeix al cançoner, seguint l'esborrany."""
        meta = meta_o_404(id_canconer)
        d = request.get_json(silent=True) or {}
        tipus = "pagina" if d.get("tipus") == "pagina" else "canco"
        # Si porta text (copiat de webs de tabs), la cançó es crea amb la lletra i els acords ja posats.
        contingut = plantilles.de_document(document.de_text(str(d["text"]))) if d.get("text") and tipus == "canco" else None
        # Plantilla (pàgina mestra) triada: s'aplica a totes les pàgines de la cançó nova.
        if d.get("mestra") and any(m["id"] == d["mestra"] for m in meta["mestres"]):
            if contingut is None:
                contingut = plantilles.canco_nova() if tipus == "canco" else {"format": 2, "pagines": [plantilles.pagina([])]}
            for p in contingut["pagines"]:
                p["mestra"] = d["mestra"]
        id_canco = bd.crea_canco(str(d.get("titol") or "").strip() or ("Pàgina lliure" if tipus == "pagina" else "Nova cançó"),
                                 str(d.get("autor") or "").strip(), contingut, tipus=tipus)
        bd.afegeix_entrada(id_canconer, id_canco, despres_de=d.get("despres_de"))
        if tipus == "pagina":
            bd.actualitza_entrada(id_canconer, id_canco, inici="qualsevol")
        return jsonify({"id": id_canco})

    @app.post("/api/canconer/<id_canconer>/importa")
    def api_importa(id_canconer):
        """Importa cançons de la biblioteca, fixades a la seva última versió."""
        meta_o_404(id_canconer)
        d = request.get_json(silent=True) or {}
        afegides = []
        for id_canco in d.get("cancons", [])[:200]:
            versio = o_404(bd.ultima_versio, id_canco)
            bd.afegeix_entrada(id_canconer, id_canco, versio_id=versio["id"], despres_de=d.get("despres_de"))
            afegides.append(id_canco)
        return jsonify({"afegides": afegides})

    @app.patch("/api/canconer/<id_canconer>/entrada/<id_canco>")
    def api_entrada(id_canconer, id_canco):
        """Si surt al PDF, transport, versió que fa servir aquest cançoner i on comença."""
        d = request.get_json(silent=True) or {}
        canvis = {}
        if "inclosa" in d:
            canvis["inclosa"] = 1 if d["inclosa"] else 0
        if "transport" in d:
            canvis["transport"] = max(-11, min(11, _enter(d["transport"])))
        if "versio_id" in d:
            canvis["versio_id"] = d["versio_id"] or None  # None = segueix l'esborrany
        if "inici" in d:
            canvis["inici"] = "qualsevol" if d["inici"] == "qualsevol" else "esquerra"
        o_404(bd.actualitza_entrada, id_canconer, id_canco, **canvis)
        return jsonify({"ok": True})

    @app.delete("/api/canconer/<id_canconer>/entrada/<id_canco>")
    def api_entrada_treu(id_canconer, id_canco):
        bd.treu_entrada(id_canconer, id_canco)
        return jsonify({"ok": True})

    # ------------------------------------------------------------ API: cançons i versions

    @app.get("/api/canco/<id_canco>")
    def api_canco(id_canco):
        return jsonify(o_404(bd.carrega_canco, id_canco))

    @app.put("/api/canco/<id_canco>")
    def api_canco_desa(id_canco):
        d = request.get_json(silent=True) or {}
        contingut = None
        if "contingut" in d:
            try:
                contingut = disseny.contingut(d["contingut"])
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
        o_404(bd.desa_esborrany, id_canco,
              titol=str(d["titol"]).strip() if "titol" in d else None,
              autor=str(d["autor"]).strip() if "autor" in d else None,
              contingut=contingut)
        return jsonify({"ok": True})

    @app.get("/api/canco/<id_canco>/versions")
    def api_versions(id_canco):
        canco = o_404(bd.carrega_canco, id_canco)
        return jsonify({"versions": bd.versions(id_canco), "esborrany_modificat": canco["esborrany_modificat"]})

    @app.post("/api/canco/<id_canco>/versions")
    def api_versio_nova(id_canco):
        nota = str((request.get_json(silent=True) or {}).get("nota", ""))[:200]
        return jsonify({"versio": o_404(bd.crea_versio, id_canco, nota)})

    @app.get("/api/versio/<id_versio>")
    def api_versio(id_versio):
        return jsonify(o_404(bd.carrega_versio, id_versio))

    @app.put("/api/versio/<id_versio>/nota")
    def api_versio_nota(id_versio):
        nota = str((request.get_json(silent=True) or {}).get("nota", "")).strip()
        o_404(bd.edita_nota_versio, id_versio, nota)
        return jsonify({"ok": True, "nota": nota[:200]})

    @app.post("/api/canco/<id_canco>/restaura")
    def api_restaura(id_canco):
        o_404(bd.restaura_versio, id_canco, (request.get_json(silent=True) or {}).get("versio_id", ""))
        return jsonify({"canco": bd.carrega_canco(id_canco)})

    @app.post("/api/diagrames")
    def api_diagrames():
        """SVG dels diagrames d'uns acords, per a l'editor ({acord: svg})."""
        d = request.get_json(silent=True) or {}
        instrument = "ukulele" if d.get("instrument") == "ukulele" else "guitarra"
        acords = [str(a)[:16] for a in (d.get("acords") or [])[:100] if a]
        return jsonify({a: diagrames.svg(a.split("/")[0], instrument) for a in acords})

    @app.post("/api/video")
    def api_video():
        """Analitza una adreça de YouTube i en busca el títol (si hi ha connexió)."""
        try:
            v = videos.analitza((request.get_json(silent=True) or {}).get("url", ""))
        except videos.UrlInvalida as e:
            return jsonify({"error": str(e)}), 400
        v = videos.normalitza([{**v, **videos.informacio(v), "inclou_qr": True}])[0]
        return jsonify({"video": v, "url": videos.url_curta(v), "miniatura": videos.miniatura(v)})

    @app.get("/api/biblioteca")
    def api_biblioteca():
        return jsonify({"cancons": bd.biblioteca(request.args.get("q", ""))})

    # ------------------------------------------------------------ API: elements, text i imatges

    @app.get("/api/elements")
    def api_elements():
        return jsonify({"elements": bd.elements_desats()})

    @app.post("/api/elements")
    def api_element_nou():
        d = request.get_json(silent=True) or {}
        elements = disseny.elements(d.get("elements"))
        if not elements:
            return jsonify({"error": "No hi ha cap element per desar."}), 400
        return jsonify({"id": bd.desa_element(str(d.get("nom", "")).strip(), elements)})

    @app.delete("/api/elements/<id_element>")
    def api_element_esborra(id_element):
        o_404(bd.esborra_element, id_element)
        return jsonify({"ok": True})

    @app.post("/api/converteix")
    def api_converteix():
        """Text de webs de tabs (acords a sobre de la lletra) → document de l'editor."""
        text = str((request.get_json(silent=True) or {}).get("text", ""))
        return jsonify({"doc": document.de_text(text), "te_acords": document.sembla_text_amb_acords(text)})

    @app.post("/api/transporta")
    def api_transporta():
        """Transporta els acords de tots els marcs de lletra d'una cançó."""
        d = request.get_json(silent=True) or {}
        try:
            contingut = disseny.contingut(d.get("contingut"))
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        semitons = _enter(d.get("semitons"))
        for p in contingut["pagines"]:
            for e in p["elements"]:
                if e["tipus"] == "lletra":
                    e["doc"] = document.transporta(e["doc"], semitons)
        return jsonify({"contingut": contingut})

    @app.post("/api/imatges")
    def api_imatge_nova():
        fitxer = request.files.get("imatge")
        if not fitxer:
            abort(400, "Falta la imatge")
        dades = fitxer.read(MIDA_MAXIMA_IMATGE + 1)
        if len(dades) > MIDA_MAXIMA_IMATGE:
            return jsonify({"error": "La imatge fa més de 12 MB."}), 413
        try:
            id_imatge = bd.desa_imatge(dades, fitxer.mimetype, fitxer.filename or "")
        except ValueError as e:
            return jsonify({"error": str(e)}), 415
        return jsonify({"id": id_imatge, "url": url_for("imatge", id_imatge=id_imatge)})

    @app.get("/imatges/<id_imatge>")
    def imatge(id_imatge):
        cami, tipus = o_404(bd.imatge, id_imatge)
        if not cami.exists():
            abort(404)
        resposta = send_file(cami, mimetype=tipus, max_age=31536000)
        resposta.headers["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'"
        return resposta

    # ------------------------------------------------------------ Tipografies

    @app.get("/fonts.css")
    def fonts_css():
        css = tipografies.css(fonts(), lambda f: url_for("static", filename=f"fonts/{f}"),
                              lambda i: url_for("fitxer_tipografia", id_tipografia=i))
        return Response(css, mimetype="text/css", headers={"Cache-Control": "no-cache"})

    @app.get("/tipografies/<id_tipografia>")
    def fitxer_tipografia(id_tipografia):
        cami, format_ = o_404(bd.fitxer_tipografia, id_tipografia)
        if not cami.exists():
            abort(404)
        return send_file(cami, mimetype=f"font/{'ttf' if format_ == 'ttf' else format_}", max_age=31536000)

    @app.get("/api/fonts")
    def api_fonts():
        return jsonify({"fonts": tipografies.per_al_navegador(fonts()), "importades": bd.tipografies_importades()})

    @app.post("/api/fonts")
    def api_font_nova():
        """Importa un fitxer de font (TTF, OTF, WOFF o WOFF2) com una cara d'una família."""
        fitxer = request.files.get("font")
        if not fitxer:
            abort(400, "Falta el fitxer")
        dades = fitxer.read(MIDA_MAXIMA_FONT + 1)
        if len(dades) > MIDA_MAXIMA_FONT:
            return jsonify({"error": "La font fa més de 15 MB."}), 413
        format_ = tipografies.tipus_fitxer(dades)
        if not format_:
            return jsonify({"error": "No és un fitxer de font TTF, OTF, WOFF o WOFF2."}), 415
        nom = (request.form.get("nom") or "").strip()[:80] or re.sub(r"[-_]+", " ", (fitxer.filename or "Font").rsplit(".", 1)[0])
        id_font = bd.desa_tipografia(dades, format_, nom, _enter(request.form.get("pes"), 400), request.form.get("estil", "normal"))
        return jsonify({"id": id_font, "clau": tipografies.clau_importada(nom), "nom": nom})

    @app.delete("/api/fonts/<id_tipografia>")
    def api_font_esborra(id_tipografia):
        o_404(bd.esborra_tipografia, id_tipografia)
        return jsonify({"ok": True})

    # ------------------------------------------------------------ PDF (Gotenberg)

    @app.get("/canconer/<id_canconer>/pdf/<tipus>")
    def canconer_pdf(id_canconer, tipus):
        if tipus not in TIPUS_PDF:
            abort(404)
        c = canconer_impressio(id_canconer)
        instrument = c["instrument"]
        try:
            if tipus == "instruccions":
                contingut = pdf.instruccions(url_interna(url_for("canconer_instruccions", id_canconer=id_canconer)))
            else:
                pla = maquetacio.pla(c)
                url = url_interna(url_for("canconer_imprimible", id_canconer=id_canconer, v=pdf.empremta(c),
                                          instrument=instrument))
                contingut = pdf.genera(c, tipus, url, pla["total"], colors_cmyk=pla["colors"])
        except (pdf.GotenbergNoDisponible, cmyk.GhostscriptNoDisponible) as e:
            return Response(str(e), status=503, mimetype="text/plain; charset=utf-8")
        pdf.neteja_cau()
        # Si hi ha pàgina de diagrames, el nom del fitxer diu per a quin instrument és.
        sufix = f"-{instrument}" if c.get("pagina_acords") and tipus != "instruccions" else ""
        if marges.actiu(c["marge"]) and tipus != "instruccions":
            sufix += f"-marges-{_nom_fitxer(c['marge']['nom'])}"
        nom = f"{_nom_fitxer(c['titol'])}-{TIPUS_PDF[tipus]}{sufix}.pdf"
        mode = "attachment" if request.args.get("baixa") else "inline"
        cau = "private, max-age=86400" if request.args.get("v") else "no-cache"
        return Response(contingut, mimetype="application/pdf",
                        headers={"Content-Disposition": f'{mode}; filename="{nom}"', "Cache-Control": cau})

    return app
