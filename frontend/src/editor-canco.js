// Editor de cançons amb Tiptap: acords ancorats a la síl·laba, seccions, notes, imatges
// i marques musicals (síl·laba tònica, veus del cor). L'esquema és el mateix que llegeix
// canconer/document.py per generar el PDF.
import { Editor, Extension, InputRule, Mark, Node, mergeAttributes } from "@tiptap/core";
import Bold from "@tiptap/extension-bold";
import Italic from "@tiptap/extension-italic";
import { Dropcursor, Gapcursor, Placeholder, UndoRedo } from "@tiptap/extensions";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import { FONTS, colorCss } from "./pagines.js";

// ---------------------------------------------------------------- Acords (mateixa regla que parser.py)

const NOTA = "[A-G](?:#|b)?";
const QUALITAT = "(?:maj|Maj|min|dim|aug|sus|add|m|M|\\+|-|°|ø|\\d|#|b|\\(|\\))*";
const REGEX_ACORD = new RegExp(`^(?:N\\.?C\\.?|${NOTA}${QUALITAT}(?:/${NOTA})?)$`);
const REGEX_NEUTRE = /^(?:\|+|:?\|\|?:?|%|-+|\(?x\d+\)?)$/i;

export const esAcord = (text) => REGEX_ACORD.test(text);

export function esLiniaAcords(linia) {
  const elements = linia.trim().split(/\s+/).filter(Boolean);
  if (!elements.length) return false;
  let hiHaAcord = false;
  for (const e of elements) {
    if (esAcord(e)) hiHaAcord = true;
    else if (!REGEX_NEUTRE.test(e)) return false;
  }
  return hiHaAcord;
}

/** True si un text enganxat sembla de web de tabs (alguna línia només d'acords). */
export const semblaTextAmbAcords = (text) =>
  text.split(/\r?\n/).some((l) => esLiniaAcords(l) || /^\s*\[[^\]]+\]\s+\S/.test(l) && esLiniaAcords(l.replace(/^\s*\[[^\]]+\]/, "")));

// ---------------------------------------------------------------- Nodes de bloc

const Document = Node.create({ name: "doc", topNode: true, content: "bloc+" });
const Text = Node.create({ name: "text", group: "inline" });

/** Després d'una secció o nota, Enter crea una línia de lletra normal. */
function enterSurtABlocNormal(nom) {
  return ({ editor }) => {
    if (!editor.isActive(nom)) return false;
    return editor.chain().splitBlock().setNode("linia").run();
  };
}

const Linia = Node.create({
  name: "linia",
  group: "bloc",
  content: "inline*",
  priority: 1000,
  parseHTML: () => [{ tag: "p" }, { tag: "div" }],
  renderHTML: ({ HTMLAttributes }) => ["p", mergeAttributes(HTMLAttributes, { class: "linia" }), 0],
});

const Seccio = Node.create({
  name: "seccio",
  group: "bloc",
  content: "text*",
  marks: "",
  defining: true,
  parseHTML: () => [{ tag: "h4" }, { tag: "h3" }],
  renderHTML: ({ HTMLAttributes }) => ["h4", mergeAttributes(HTMLAttributes, { class: "seccio" }), 0],
  addKeyboardShortcuts() {
    return { Enter: enterSurtABlocNormal(this.name), "Mod-Alt-1": () => this.editor.commands.toggleNode(this.name, "linia") };
  },
});

const Nota = Node.create({
  name: "nota",
  group: "bloc",
  content: "text*",
  defining: true,
  parseHTML: () => [{ tag: "p.nota" }],
  renderHTML: ({ HTMLAttributes }) => ["p", mergeAttributes(HTMLAttributes, { class: "nota" }), 0],
  addKeyboardShortcuts() {
    return { Enter: enterSurtABlocNormal(this.name), "Mod-Alt-2": () => this.editor.commands.toggleNode(this.name, "linia") };
  },
});

// ---------------------------------------------------------------- Imatge (bloc amb el text al voltant)

function creaImatge(urlImatge) {
  return Node.create({
    name: "imatge",
    group: "bloc",
    atom: true,
    draggable: true,
    selectable: true,
    addAttributes: () => ({
      src: { default: null },
      posicio: { default: "dreta" },
      amplada: { default: 40 },
    }),
    parseHTML: () => [{ tag: "figure[data-imatge]" }],
    renderHTML: ({ HTMLAttributes }) => ["figure", mergeAttributes(HTMLAttributes, { "data-imatge": "" })],
    addNodeView() {
      return ({ node, getPos, editor }) => {
        let actual = node;
        const figura = document.createElement("figure");
        figura.className = "imatge-ed";
        figura.contentEditable = "false";
        const img = document.createElement("img");
        img.draggable = false;
        img.alt = "";
        const eines = document.createElement("div");
        eines.className = "eines-imatge";
        const accions = [
          ["esquerra", "Text a la dreta", "M2 3h5v6H2zM9 3h5M9 6h5M9 9h5M2 12h12"],
          ["centre", "Sola, centrada", "M4 3h8v6H4zM2 12h12"],
          ["dreta", "Text a l'esquerra", "M9 3h5v6H9zM2 3h5M2 6h5M2 9h5M2 12h12"],
          ["-", "Més petita", "M4 8h8"],
          ["+", "Més gran", "M8 4v8M4 8h8"],
          ["x", "Elimina la imatge", "M4 4l8 8M12 4l-8 8"],
        ];
        for (const [accio, titol, cami] of accions) {
          const b = document.createElement("button");
          b.type = "button";
          b.title = titol;
          b.dataset.accio = accio;
          b.innerHTML = `<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6"><path d="${cami}"/></svg>`;
          b.addEventListener("mousedown", (e) => e.preventDefault());
          b.addEventListener("click", () => {
            const pos = getPos();
            if (typeof pos !== "number") return;
            if (accio === "x") {
              editor.chain().focus().deleteRange({ from: pos, to: pos + actual.nodeSize }).run();
              return;
            }
            const attrs = { ...actual.attrs };
            if (accio === "-") attrs.amplada = Math.max(15, attrs.amplada - 10);
            else if (accio === "+") attrs.amplada = Math.min(100, attrs.amplada + 10);
            else attrs.posicio = accio;
            editor.view.dispatch(editor.state.tr.setNodeMarkup(pos, undefined, attrs));
          });
          eines.append(b);
        }
        figura.append(img, eines);
        const pinta = () => {
          img.src = actual.attrs.src ? urlImatge(actual.attrs.src) : "";
          figura.dataset.posicio = actual.attrs.posicio;
          figura.style.width = `${actual.attrs.amplada}%`;
        };
        pinta();
        return {
          dom: figura,
          update(nou) {
            if (nou.type.name !== "imatge") return false;
            actual = nou;
            pinta();
            return true;
          },
          selectNode: () => figura.classList.add("seleccionada"),
          deselectNode: () => figura.classList.remove("seleccionada"),
          stopEvent: (e) => !!e.target.closest?.(".eines-imatge"),
          ignoreMutation: () => true,
        };
      };
    },
  });
}

// ---------------------------------------------------------------- Acord (en línia, ancorat a la síl·laba)

function creaAcord(editaAcord) {
  return Node.create({
    name: "acord",
    group: "inline",
    inline: true,
    atom: true,
    selectable: true,
    draggable: true,
    addAttributes: () => ({ nom: { default: "C" } }),
    parseHTML: () => [{ tag: "span[data-acord]", getAttrs: (el) => ({ nom: el.getAttribute("data-acord") }) }],
    renderHTML: ({ node }) => ["span", { "data-acord": node.attrs.nom, class: "acord" }, ["span", { class: "acord-nom" }, node.attrs.nom]],
    addNodeView() {
      return ({ node, getPos }) => {
        const dom = document.createElement("span");
        dom.className = "acord";
        dom.contentEditable = "false";
        const nom = document.createElement("span");
        nom.className = "acord-nom";
        nom.textContent = node.attrs.nom;
        nom.title = "Clica per canviar l'acord · arrossega'l per moure'l";
        dom.append(nom);
        nom.addEventListener("click", (e) => {
          e.preventDefault();
          const pos = getPos();
          if (typeof pos === "number") editaAcord({ pos, nom: node.attrs.nom, element: nom });
        });
        return {
          dom,
          update(nou) {
            if (nou.type.name !== "acord") return false;
            node = nou;
            nom.textContent = nou.attrs.nom;
            return true;
          },
          selectNode: () => dom.classList.add("seleccionat"),
          deselectNode: () => dom.classList.remove("seleccionat"),
          ignoreMutation: () => true,
        };
      };
    },
  });
}

// ---------------------------------------------------------------- Marques musicals

const Tonica = Mark.create({
  name: "tonica",
  parseHTML: () => [{ tag: "span.tonica" }],
  renderHTML: () => ["span", { class: "tonica" }, 0],
  addKeyboardShortcuts() {
    return { "Mod-u": () => this.editor.commands.toggleMark(this.name) };
  },
});

/** Mida relativa d'un tros de text (en em, respecte de la mida del marc): petita, gran, molt gran. */
const Mida = Mark.create({
  name: "mida",
  addAttributes: () => ({
    valor: {
      default: 1,
      parseHTML: (el) => Number(el.getAttribute("data-mida")) || 1,
      renderHTML: (attrs) => ({ "data-mida": attrs.valor, style: `font-size:${attrs.valor}em` }),
    },
  }),
  parseHTML: () => [{ tag: "span[data-mida]" }],
  renderHTML: ({ HTMLAttributes }) => ["span", HTMLAttributes, 0],
});

/**
 * Marca amb un valor (tipografia, color del text o color de fons) d'un tros de text. El valor es desa
 * a l'atribut «valor»: la clau de la tipografia o el color («#rrggbb» o «cmyk(c,m,y,k)», exacte al PDF).
 */
function marcaAmbValor(nom, propietat, css) {
  return Mark.create({
    name: nom,
    addAttributes: () => ({
      valor: {
        default: null,
        parseHTML: (el) => el.getAttribute(`data-${nom}`),
        renderHTML: (attrs) => (attrs.valor ? { [`data-${nom}`]: attrs.valor, style: `${propietat}:${css(attrs.valor)}` } : {}),
      },
    }),
    parseHTML: () => [{ tag: `span[data-${nom}]` }],
    renderHTML: ({ HTMLAttributes }) => ["span", HTMLAttributes, 0],
  });
}
const Font = marcaAmbValor("font", "font-family", (clau) => FONTS[clau] || "inherit");
const ColorText = marcaAmbValor("color", "color", colorCss);
const Fons = marcaAmbValor("fons", "background-color", colorCss);

const Cor = Mark.create({
  name: "cor",
  parseHTML: () => [{ tag: "span.cor" }],
  renderHTML: () => ["span", { class: "cor" }, 0],
  addKeyboardShortcuts() {
    return { "Mod-Shift-k": () => this.editor.commands.toggleMark(this.name) };
  },
});

// ---------------------------------------------------------------- Regles d'entrada i decoracions

// Etiquetes de secció habituals (en anglès o castellà) → en català (la mateixa taula que document.py).
const SECCIONS_CATALA = {
  verse: "Estrofa", verso: "Estrofa", estrofa: "Estrofa",
  chorus: "Tornada", coro: "Tornada", estribillo: "Tornada", refrain: "Tornada", hook: "Tornada",
  "pre-chorus": "Pre-tornada", prechorus: "Pre-tornada", "pre chorus": "Pre-tornada", "pre-coro": "Pre-tornada",
  "post-chorus": "Post-tornada", bridge: "Pont", puente: "Pont",
  intro: "Intro", outro: "Final", final: "Final", ending: "Final", coda: "Coda",
  interlude: "Interludi", interludio: "Interludi", instrumental: "Instrumental", solo: "Solo",
};

/** «Verse 1» → «Estrofa 1», «Chorus» → «Tornada»... Les que no es coneixen queden igual. */
export function etiquetaCatalana(etiqueta) {
  const m = /^\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ -]*?)\s*(\d+|[IVX]+)?\s*:?\s*$/.exec(etiqueta);
  const nom = m && SECCIONS_CATALA[m[1].toLowerCase()];
  if (!nom) return etiqueta;
  return m[2] ? `${nom} ${m[2]}` : nom;
}

/** [G] crea un acord; [Tornada] (o [Chorus]) sol en una línia la converteix en secció. */
const ReglesMusicals = Extension.create({
  name: "reglesMusicals",
  addInputRules() {
    return [
      new InputRule({
        find: /\[([^\]\n]{1,40})\]$/,
        handler: ({ state, range, match }) => {
          const text = match[1].trim();
          const { $from } = state.selection;
          if ($from.parent.type.name !== "linia") return null;
          if (esAcord(text)) {
            state.tr.replaceWith(range.from, range.to, state.schema.nodes.acord.create({ nom: text }));
            return;
          }
          // Etiqueta de secció: només si és tot el que hi ha a la línia (escrita o enganxada de cop).
          const inici = $from.start();
          const despres = state.doc.textBetween(range.to, $from.end());
          if (range.from === inici && !despres.trim()) {
            state.tr.replaceWith(inici - 1, $from.end() + 1,
              state.schema.nodes.seccio.create(null, state.schema.text(etiquetaCatalana(text))));
            return;
          }
          return null;
        },
      }),
    ];
  },
});

/** Classes a les línies: amb acords (deixen espai a sobre) i només d'acords (es mostren seguits). */
const DecoracioLinies = Extension.create({
  name: "decoracioLinies",
  addProseMirrorPlugins() {
    const calcula = (doc) => {
      const decoracions = [];
      doc.forEach((node, pos) => {
        if (node.type.name !== "linia") return;
        let acords = 0;
        let text = "";
        node.forEach((fill) => {
          if (fill.type.name === "acord") acords++;
          else if (fill.isText) text += fill.text;
        });
        if (acords) decoracions.push(Decoration.node(pos, pos + node.nodeSize,
          { class: text.trim() ? "amb-acords" : "nomes-acords" }));
      });
      return DecorationSet.create(doc, decoracions);
    };
    return [new Plugin({
      key: new PluginKey("decoracioLinies"),
      state: {
        init: (_, { doc }) => calcula(doc),
        apply: (tr, anterior) => (tr.docChanged ? calcula(tr.doc) : anterior),
      },
      props: { decorations(state) { return this.getState(state); } },
    })];
  },
});

/** En enganxar text amb línies d'acords a sobre, es converteix al format de l'editor. */
function creaEnganxat(converteix) {
  return Extension.create({
    name: "enganxatTabs",
    addProseMirrorPlugins() {
      const editor = this.editor;
      return [new Plugin({
        key: new PluginKey("enganxatTabs"),
        props: {
          handlePaste(view, event) {
            const text = event.clipboardData?.getData("text/plain") || "";
            if (!text.includes("\n") || !semblaTextAmbAcords(text)) return false;
            event.preventDefault();
            converteix(text).then((doc) => {
              if (doc?.content?.length) editor.chain().focus().insertContent(doc.content).run();
            });
            return true;
          },
        },
      })];
    },
  });
}

// ---------------------------------------------------------------- Creació de l'editor

/**
 * @param {HTMLElement} element
 * @param {object} opcions
 *   doc: document inicial
 *   urlImatge(id): URL per mostrar una imatge
 *   converteix(text): Promise<doc> (text de tabs → document)
 *   editaAcord({pos, nom, element}): obre el diàleg per canviar un acord
 *   canvi(editor): cridat a cada canvi del document
 *   seleccio(editor): cridat quan canvia la selecció (per actualitzar la barra d'eines)
 */
export function creaEditorCanco(element, opcions) {
  return new Editor({
    element,
    content: opcions.doc,
    extensions: [
      Document, Text, Linia, Seccio, Nota,
      creaImatge(opcions.urlImatge),
      creaAcord(opcions.editaAcord),
      Bold, Italic, Tonica, Cor, Mida, Font, ColorText, Fons,
      UndoRedo, Dropcursor.configure({ color: "#141414", width: 2 }), Gapcursor,
      Placeholder.configure({
        placeholder: ({ node, pos }) => {
          if (node.type.name === "seccio") return "Nom de la secció (Tornada, Estrofa 1…)";
          if (node.type.name === "nota") return "Nota (x2, només veus…)";
          return pos === 0 ? "Escriu o enganxa la lletra. Escriu [G] per posar un acord, o [Tornada] per una secció." : "";
        },
        showOnlyCurrent: false,
      }),
      ReglesMusicals, DecoracioLinies, creaEnganxat(opcions.converteix),
    ],
    editorProps: { attributes: { class: "editor-canco", spellcheck: "false" } },
    onUpdate: ({ editor }) => opcions.canvi?.(editor),
    onSelectionUpdate: ({ editor }) => opcions.seleccio?.(editor),
    onTransaction: ({ editor }) => opcions.seleccio?.(editor),
  });
}

/**
 * Posa un acord. Si pos apunta a un acord existent, el canvia; si no, l'insereix a posInsercio
 * (per defecte, l'inici de la selecció). Si hi ha text seleccionat, el text no s'esborra: l'acord
 * queda a sobre de la primera síl·laba de la selecció.
 */
export function posaAcord(editor, nom, pos = null, posInsercio = null) {
  if (pos !== null) {
    const node = editor.state.doc.nodeAt(pos);
    if (node?.type.name === "acord") {
      editor.view.dispatch(editor.state.tr.setNodeMarkup(pos, undefined, { nom }));
      editor.commands.focus();
      return;
    }
  }
  const on = posInsercio ?? editor.state.selection.from;
  editor.chain().focus().insertContentAt(on, { type: "acord", attrs: { nom } }).setTextSelection(on + 1).run();
}

/** Canvia la mida del text seleccionat (1 = la del marc). */
export function posaMida(editor, valor) {
  if (Number(valor) === 1) editor.chain().focus().unsetMark("mida").run();
  else editor.chain().focus().setMark("mida", { valor: Number(valor) }).run();
}

/** Posa (o treu, amb valor buit) una marca amb valor al text seleccionat: font, color o fons. */
export function posaMarcaValor(editor, nom, valor) {
  if (valor) editor.chain().focus().setMark(nom, { valor }).run();
  else editor.chain().focus().unsetMark(nom).run();
}

export function treuAcord(editor, pos) {
  const node = editor.state.doc.nodeAt(pos);
  if (node?.type.name === "acord") editor.chain().focus().deleteRange({ from: pos, to: pos + 1 }).run();
}

/** Acords de la cançó, en ordre d'aparició (per suggerir-los en afegir-ne un). */
export function acordsDelDocument(editor) {
  const noms = [];
  editor.state.doc.descendants((node) => {
    if (node.type.name === "acord" && !noms.includes(node.attrs.nom)) noms.push(node.attrs.nom);
  });
  return noms;
}
