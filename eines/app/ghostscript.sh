#!/usr/bin/env bash
# Compila Ghostscript des del codi font oficial per posar-lo dins de Cançoners.app (PDF en CMYK).
#   ./eines/app/ghostscript.sh        →  eines/ghostscript/gs (un sol binari, amb els recursos a dins)
#
# Es fa servir el codi font tal com el publica Artifex (llicència AGPL-3.0); les biblioteques que
# necessita (freetype, lcms2, libjpeg, libpng, zlib…) són les que porta el mateix paquet, així el
# binari només depèn del sistema. Només cal fer-ho un cop (o quan es canviï de versió).
set -euo pipefail
cd "$(dirname "$0")/../.."
VERSIO=10.08.0
ETIQUETA=gs${VERSIO//./}
DESTI=eines/ghostscript
URL=https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/$ETIQUETA

if [[ -x "$DESTI/gs" && "$("$DESTI/gs" --version)" == "$VERSIO" ]]; then
  echo "Ghostscript $("$DESTI/gs" --version) ja compilat a $DESTI/gs"
  exit 0
fi

mkdir -p "$DESTI"
treball=$(mktemp -d)
trap 'rm -rf "$treball"' EXIT
echo "▸ Baixant Ghostscript ${VERSIO}…"
curl -fsSL "$URL/ghostscript-$VERSIO.tar.gz" -o "$treball/gs.tar.gz"
curl -fsSL "$URL/SHA512SUMS" -o "$treball/SHA512SUMS"
esperat=$(grep " ghostscript-$VERSIO.tar.gz\$" "$treball/SHA512SUMS" | cut -d' ' -f1)
obtingut=$(shasum -a 512 "$treball/gs.tar.gz" | cut -d' ' -f1)
[[ -n "$esperat" && "$esperat" == "$obtingut" ]] || { echo "La suma SHA-512 del codi font no coincideix." >&2; exit 1; }

echo "▸ Compilant (uns minuts)…"
tar -xzf "$treball/gs.tar.gz" -C "$treball"
cd "$treball/ghostscript-$VERSIO"
export CFLAGS="-O2 -mmacosx-version-min=12.0" LDFLAGS="-mmacosx-version-min=12.0"
./configure --quiet --disable-cups --disable-gtk --without-x --disable-fontconfig --disable-dbus \
  --without-libidn --without-libpaper --without-tesseract --without-pdftoraster --without-ijs \
  > "$treball/configure.log" 2>&1 || { tail -20 "$treball/configure.log" >&2; exit 1; }
make -j"$(sysctl -n hw.ncpu)" gs > "$treball/make.log" 2>&1 || { tail -30 "$treball/make.log" >&2; exit 1; }
cd - >/dev/null
cp "$treball/ghostscript-$VERSIO/bin/gs" "$DESTI/gs"
cp "$treball/ghostscript-$VERSIO/LICENSE" "$DESTI/LICENSE"
echo "$URL/ghostscript-$VERSIO.tar.gz" > "$DESTI/CODI_FONT"
echo "✓ $DESTI/gs ($("$DESTI/gs" --version))"
otool -L "$DESTI/gs" | tail -n +2
