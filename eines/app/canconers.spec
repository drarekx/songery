# -*- mode: python ; coding: utf-8 -*-
# Especificació de PyInstaller per a Cançoners.app (la fa servir eines/app/construeix.sh).
from pathlib import Path

ARREL = Path(SPECPATH).resolve().parent.parent
VERSIO = (ARREL / "eines" / "app" / "VERSIO").read_text().strip()

a = Analysis(
    [str(ARREL / "escriptori.py")],
    pathex=[str(ARREL)],
    datas=[
        (str(ARREL / "canconer" / "templates"), "canconer/templates"),
        (str(ARREL / "canconer" / "static"), "canconer/static"),
        (str(ARREL / "eines" / "app" / "icona-menu.png"), "eines/app"),
        (str(ARREL / "eines" / "app" / "VERSIO"), "eines/app"),
        # Llicència i origen del codi font de Ghostscript (AGPL-3.0)
        (str(ARREL / "eines" / "ghostscript" / "LICENSE"), "eines/ghostscript"),
        (str(ARREL / "eines" / "ghostscript" / "CODI_FONT"), "eines/ghostscript"),
    ],
    # Ghostscript, per fer el PDF en CMYK per a impremta (el compila eines/app/ghostscript.sh)
    binaries=[(str(ARREL / "eines" / "ghostscript" / "gs"), "eines/ghostscript")],
    hiddenimports=["canconer.web", "canconer.motor_pdf", "rumps", "ScriptingBridge"],
    excludes=["tkinter", "pytest", "weasyprint", "PIL", "IPython", "numpy"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Canconers", console=False,
          argv_emulation=False, target_arch=None)
coll = COLLECT(exe, a.binaries, a.datas, name="Canconers")
app = BUNDLE(
    coll,
    name="Cançoners.app",
    icon=str(ARREL / "eines" / "app" / "icona.icns"),
    bundle_identifier="com.drarek.canconers",
    version=VERSIO,
    info_plist={
        "CFBundleDisplayName": "Cançoners",
        "CFBundleShortVersionString": VERSIO,
        "CFBundleVersion": VERSIO,
        "LSUIElement": False,  # icona al Dock (clicar-la obre Cançoners) i a la barra de menú
        "LSMinimumSystemVersion": "12.0",
        "NSHumanReadableCopyright": "Cançoners",
        "LSApplicationCategoryType": "public.app-category.music",
        # macOS ho mostra en demanar permís per controlar Chrome (vegeu escriptori._pestanya_oberta).
        "NSAppleEventsUsageDescription": "Cançoners fa servir el navegador per anar a la pestanya de Cançoners que ja tens oberta, en lloc d'obrir-ne una de nova.",
    },
)
