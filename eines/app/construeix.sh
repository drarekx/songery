#!/usr/bin/env bash
# Construeix Cançoners.app i Cançoners.dmg (a dist/).
#
#   ./eines/app/construeix.sh
#
# Signatura i notarització (opcionals, automàtiques si estan configurades):
#   - Si al clauer hi ha un certificat «Developer ID Application», l'app i el .dmg se signen amb ell.
#     Se'n pot triar un de concret amb CANCONER_SIGNATURA="Developer ID Application: Nom (EQUIP)".
#   - Amb CANCONER_NOTARITZA=1 i el perfil de notarització «canconers», el .dmg s'envia a Apple i es grapa
#     el resultat. No cal si s'instal·la amb install.sh (curl no marca l'app com a descarregada).
#     Es crea una sola vegada amb:
#       xcrun notarytool store-credentials canconers --apple-id EL_TEU_APPLE_ID --team-id EQUIP
set -euo pipefail
cd "$(dirname "$0")/../.."
ARREL=$(pwd)
APP="dist/Cançoners.app"
DMG="dist/Cançoners.dmg"
VERSIO=$(cat eines/app/VERSIO)

PYTHON=${PYTHON:-/opt/homebrew/bin/python3.12}
if [ ! -x .venv-app/bin/python ]; then
  echo "▸ Preparant l'entorn de construcció…"
  "$PYTHON" -m venv .venv-app
fi
.venv-app/bin/pip install -q --upgrade pip
.venv-app/bin/pip install -q -r requirements.txt pyinstaller rumps pillow
# ScriptingBridge (de la mateixa versió que el PyObjC de rumps): per trobar la pestanya de Cançoners a Chrome.
.venv-app/bin/pip install -q "pyobjc-framework-ScriptingBridge==$(.venv-app/bin/python -m pip show pyobjc-core | awk '/^Version/{print $2}')"

echo "▸ Icones…"
.venv-app/bin/python eines/app/icones.py >/dev/null

echo "▸ Ghostscript (PDF en CMYK)…"
./eines/app/ghostscript.sh

echo "▸ Empaquetant amb PyInstaller…"
rm -rf build "$APP" "$DMG"
.venv-app/bin/pyinstaller --noconfirm --clean --log-level WARN --distpath dist --workpath build eines/app/canconers.spec

# Fitxers que no calen dins de l'app (fonts de Tailwind i mapes de depuració).
rm -rf "$APP/Contents/Resources/canconer/static/src"
find "$APP/Contents/Resources/canconer/static/dist" -name "*.map" -delete

IDENTITAT=${CANCONER_SIGNATURA:-$(security find-identity -v -p codesigning | grep -o '"Developer ID Application: [^"]*"' | head -1 | tr -d '"' || true)}
if [ -n "${IDENTITAT}" ]; then
  echo "▸ Signant amb «${IDENTITAT}»…"
  # Els executables solts (Ghostscript) es signen un per un: --deep no els troba.
  find "$APP/Contents" -type f -name gs -perm -u+x -print0 | xargs -0 -I{} \
    codesign --force --timestamp --options runtime --sign "${IDENTITAT}" {}
  codesign --force --deep --timestamp --options runtime --entitlements eines/app/permisos.plist --sign "${IDENTITAT}" "$APP"
  codesign --verify --deep --strict "$APP"
else
  echo "▸ Sense certificat «Developer ID Application»: signatura local (els altres Macs mostraran un avís)."
  codesign --force --deep --sign - "$APP"
fi

echo "▸ Creant el .dmg…"
TEMP=$(mktemp -d)
cp -R "$APP" "$TEMP/"
ln -s /Applications "$TEMP/Aplicacions"
hdiutil create -quiet -volname "Cançoners $VERSIO" -srcfolder "$TEMP" -ov -format UDZO "$DMG"
rm -rf "$TEMP"
[ -n "${IDENTITAT}" ] && codesign --force --timestamp --sign "${IDENTITAT}" "$DMG"

if [ "${CANCONER_NOTARITZA:-0}" = "1" ] && [ -n "${IDENTITAT}" ] && xcrun notarytool history --keychain-profile canconers >/dev/null 2>&1; then
  echo "▸ Enviant a notaritzar (pot trigar uns minuts)…"
  xcrun notarytool submit "$DMG" --keychain-profile canconers --wait
  xcrun stapler staple "$DMG"
  xcrun stapler staple "$APP"
  spctl --assess --type open --context context:primary-signature -v "$DMG" || true
else
  echo "▸ Sense notarització (no cal per instal·lar amb install.sh; per notaritzar: CANCONER_NOTARITZA=1)."
fi

echo
echo "✓ $APP"
echo "✓ $DMG ($(du -h "$DMG" | cut -f1))"
