"""Grava un vídeo d'una sessió: fotogrames amb el temps real, cursor fals i rètols; ffmpeg els munta."""
from __future__ import annotations

import base64
import shutil
import subprocess
import time
from pathlib import Path

from nav import TREBALL, Nav

SUPERPOSICIO = """
(() => {
  if (document.getElementById('gv-cursor')) return;
  const estil = document.createElement('style');
  estil.textContent = `
    #gv-cursor { position: fixed; left: 0; top: 0; z-index: 2147483647; pointer-events: none; width: 26px; height: 26px;
                 filter: drop-shadow(0 1px 2px rgba(0,0,0,.35)); }
    #gv-ona { position: fixed; z-index: 2147483646; pointer-events: none; width: 44px; height: 44px; margin: -22px 0 0 -22px;
              border-radius: 50%; background: rgba(214, 48, 30, .35); opacity: 0; transform: scale(.3); }
    #gv-ona.viu { transition: opacity .45s ease-out, transform .45s ease-out; }
    #gv-retol { position: fixed; left: 50%; bottom: 26px; transform: translateX(-50%); z-index: 2147483645; pointer-events: none;
                max-width: 80vw; padding: 12px 22px; border-radius: 12px; background: rgba(20, 20, 20, .92); color: #fff;
                font: 600 19px/1.35 -apple-system, 'Helvetica Neue', sans-serif; text-align: center;
                box-shadow: 0 8px 28px rgba(0,0,0,.28); opacity: 0; transition: opacity .25s; }
    #gv-retol.viu { opacity: 1; }
    #gv-retol small { display: block; font-weight: 400; font-size: 15px; opacity: .8; margin-top: 2px; }
    #gv-retol kbd { font: 600 16px ui-monospace, Menlo, monospace; background: rgba(255,255,255,.18); border-radius: 5px; padding: 1px 6px; }`;
  document.documentElement.appendChild(estil);
  const cursor = document.createElement('div');
  cursor.id = 'gv-cursor';
  cursor.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26"><path d="M4 2l15 9.5-6.6 1.3 4 7.6-2.8 1.5-4-7.7L4 19z" fill="#111" stroke="#fff" stroke-width="1.4" stroke-linejoin="round"/></svg>';
  const ona = document.createElement('div'); ona.id = 'gv-ona';
  const retol = document.createElement('div'); retol.id = 'gv-retol';
  document.documentElement.append(ona, retol, cursor);
  window.gvMou = (x, y) => { cursor.style.transform = `translate(${x - 4}px, ${y - 2}px)`; };
  window.gvOna = (x, y) => {
    ona.classList.remove('viu'); ona.style.left = x + 'px'; ona.style.top = y + 'px';
    ona.style.opacity = 1; ona.style.transform = 'scale(.3)';
    requestAnimationFrame(() => requestAnimationFrame(() => { ona.classList.add('viu'); ona.style.opacity = 0; ona.style.transform = 'scale(1.5)'; }));
  };
  window.gvRetol = (html) => { if (html) { retol.innerHTML = html; retol.classList.add('viu'); } else retol.classList.remove('viu'); };
})()
"""


class Gravador(Nav):
    def __init__(self, nom, ample=1440, alt=900):
        super().__init__(ample, alt, escala=4 / 3)
        self.nom = nom
        self.dir = TREBALL / "fotogrames" / nom
        shutil.rmtree(self.dir, ignore_errors=True)
        self.dir.mkdir(parents=True)
        self.llista = []  # (fitxer, instant)
        self.x, self.y = ample / 2, alt / 2
        self.text_retol = ""
        self.descompte = 0.0  # temps que no ha de sortir al vídeo (càrregues)

    # --- fotogrames ---
    def foto(self):
        dades = self.s.crida("Page.captureScreenshot", {"format": "jpeg", "quality": 92})["data"]
        fitxer = self.dir / f"{len(self.llista):05d}.jpg"
        fitxer.write_bytes(base64.b64decode(dades))
        self.llista.append((fitxer, time.time() - self.descompte))

    def pausa(self, segons):
        limit = time.time() + segons
        while True:
            self.foto()
            if time.time() >= limit:
                break
            time.sleep(0.03)

    def sense_gravar(self, funcio):
        """Fa una cosa lenta (carregar una pàgina) sense que el temps compti al vídeo."""
        inici = time.time()
        funcio()
        self.superposa()
        self.descompte += time.time() - inici

    def superposa(self):
        self.avalua(SUPERPOSICIO)
        self.avalua(f"gvMou({self.x}, {self.y}); gvRetol({self.text_retol!r})")

    # --- gestos visibles ---
    def retol(self, html, segons=0.0):
        self.text_retol = html
        self.avalua(f"gvRetol({html!r})")
        self.pausa(max(segons, 0.35))

    def mou(self, x, y, durada=0.7):
        x0, y0 = self.x, self.y
        passos = max(6, int(durada * 24))
        for i in range(1, passos + 1):
            t = i / passos
            t = t * t * (3 - 2 * t)  # suau al principi i al final
            self.x, self.y = x0 + (x - x0) * t, y0 + (y - y0) * t
            self.ratoli("mouseMoved", self.x, self.y)
            self.avalua(f"gvMou({self.x}, {self.y})")
            self.foto()

    def clica(self, on, vegades=1, despres=0.6, durada=0.7):
        x, y = on if isinstance(on, (tuple, list)) else self.centre(on)
        self.mou(x, y, durada)
        self.pausa(0.15)
        self.avalua(f"gvOna({x}, {y})")
        self.clic(x, y, vegades)
        self.pausa(despres)

    def tecleja(self, text, ritme=0.045):
        for lletra in text:
            if lletra == "\n":
                self.tecla("Enter", "Enter", 13)
            else:
                self.escriu(lletra)
            time.sleep(ritme)
            self.foto()

    # --- muntatge ---
    def munta(self, desti_mp4, desti_gif=None, ample_gif=900, fps_gif=10):
        self.foto()
        concat = self.dir / "llista.txt"
        linies = []
        for (fitxer, t), (_, t2) in zip(self.llista, self.llista[1:]):
            linies += [f"file '{fitxer.resolve()}'", f"duration {max(t2 - t, 0.01):.4f}"]
        linies.append(f"file '{self.llista[-1][0].resolve()}'")
        concat.write_text("\n".join(linies))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat),
                        "-vf", "fps=30,scale=1920:-2:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-crf", "20",
                        "-preset", "slow", "-movflags", "+faststart", str(desti_mp4)], check=True)
        if desti_gif:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(desti_mp4), "-vf",
                            f"fps={fps_gif},scale={ample_gif}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle",
                            str(desti_gif)], check=True)
        durada = self.llista[-1][1] - self.llista[0][1]
        print(f"{desti_mp4}: {durada:.1f} s, {len(self.llista)} fotogrames")

    def arrossega_v(self, origen, desti, durada=1.1):
        x1, y1 = origen if isinstance(origen, (tuple, list)) else self.centre(origen)
        x2, y2 = desti
        self.mou(x1, y1)
        self.pausa(0.2)
        self.ratoli("mousePressed", x1, y1, "left", 1, clickCount=1)
        passos = int(durada * 24)
        for i in range(1, passos + 1):
            t = i / passos
            t = t * t * (3 - 2 * t)
            self.x, self.y = x1 + (x2 - x1) * t, y1 + (y2 - y1) * t
            self.ratoli("mouseMoved", self.x, self.y, "left", 1)
            self.avalua(f"gvMou({self.x}, {self.y})")
            self.foto()
        self.ratoli("mouseReleased", x2, y2, "left", 0, clickCount=1)
        self.pausa(0.6)
