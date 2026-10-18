#!/usr/bin/env bash
# Publica una versió nova de Cançoners a GitHub Releases.
#
#   1. Canvia el número de versió a eines/app/VERSIO
#   2. ./eines/app/publica.sh
#      (amb --ja-construida publica l'app que ja hi ha a dist/, sense tornar-la a construir)
#
# Construeix l'app, la comprimeix (Canconers.zip) i crea la release vX.Y.Z amb el .zip i el .dmg.
# Qui la tingui instal·lada l'actualitza amb l'opció «Actualitza» de la barra de menú o tornant a
# executar:  curl -fsSL https://raw.githubusercontent.com/drarekx/songery/main/install.sh | bash
set -euo pipefail
cd "$(dirname "$0")/../.."
VERSIO=$(cat eines/app/VERSIO)
ETIQUETA="v$VERSIO"

if gh release view "$ETIQUETA" >/dev/null 2>&1; then
  echo "La versió $ETIQUETA ja està publicada. Canvia el número a eines/app/VERSIO." >&2
  exit 1
fi

if [ "${1:-}" != "--ja-construida" ]; then
  ./eines/app/construeix.sh
fi
[ -d "dist/Cançoners.app" ] || { echo "No hi ha cap app a dist/." >&2; exit 1; }

echo "▸ Comprimint…"
rm -f dist/Canconers.zip
ditto -c -k --sequesterRsrc --keepParent "dist/Cançoners.app" dist/Canconers.zip

echo "▸ Publicant $ETIQUETA a GitHub…"
gh release create "$ETIQUETA" dist/Canconers.zip "dist/Cançoners.dmg#Cançoners.dmg" \
  --title "Cançoners $VERSIO" \
  --notes "Instal·lació o actualització:

\`\`\`
curl -fsSL https://raw.githubusercontent.com/drarekx/songery/main/install.sh | bash
\`\`\`

Per a Macs amb Apple Silicon (M1 o posterior) i macOS 12 o posterior."

echo "✓ Publicada: $(gh release view "$ETIQUETA" --json url -q .url)"
