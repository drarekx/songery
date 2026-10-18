#!/bin/bash
# Instal·lador de Cançoners (també serveix per actualitzar-lo).
#   curl -fsSL https://raw.githubusercontent.com/drarekx/songery/main/install.sh | bash
set -euo pipefail

REPO="drarekx/songery"
URL="https://github.com/$REPO/releases/latest/download/Canconers.zip"
APP="Cançoners.app"

negreta() { printf "\033[1m%s\033[0m\n" "$*"; }
error() { printf "\033[31mError:\033[0m %s\n" "$*" >&2; exit 1; }

[[ "$(uname)" == "Darwin" ]] || error "Cançoners només funciona en macOS."
major=$(sw_vers -productVersion | cut -d. -f1)
(( major >= 12 )) || error "Cançoners necessita macOS 12 (Monterey) o posterior. Tens $(sw_vers -productVersion)."
[[ "$(uname -m)" == "arm64" ]] || error "Aquesta versió de Cançoners és per a Macs amb Apple Silicon (M1 o posterior)."

negreta "Descarregant Cançoners…"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
curl -fL --progress-bar "$URL" -o "$tmp/Canconers.zip" || error "No s'ha pogut descarregar $URL"
ditto -x -k "$tmp/Canconers.zip" "$tmp"
[[ -d "$tmp/$APP" ]] || error "El fitxer descarregat no conté $APP"

# Tanca la còpia oberta perquè es pugui substituir (les dades no es toquen).
if pgrep -f "$APP/Contents/MacOS/" >/dev/null; then
    negreta "Tancant Cançoners…"
    pkill -f "$APP/Contents/MacOS/" 2>/dev/null || true
    sleep 1
fi

desti="/Applications"
if [[ ! -w "$desti" ]]; then
    desti="$HOME/Applications"
    mkdir -p "$desti"
fi
rm -rf "$desti/$APP"
mv "$tmp/$APP" "$desti/"
xattr -dr com.apple.quarantine "$desti/$APP" 2>/dev/null || true
negreta "Instal·lat a $desti/$APP"

navegador=0
for app in "Google Chrome" "Microsoft Edge" "Brave Browser" "Chromium"; do
    [[ -d "/Applications/$app.app" || -d "$HOME/Applications/$app.app" ]] && navegador=1
done
if (( ! navegador )); then
    echo
    echo "Per generar els PDF, Cançoners fa servir Chrome, Edge o Brave. Com que no n'hi ha cap,"
    echo "la primera vegada baixarà el motor de PDF de Google (uns 90 MB)."
fi

open "$desti/$APP"
negreta "Fet! Cançoners s'obre al navegador i té una icona a la barra de menú."
echo "Les teves dades són a ~/Library/Application Support/Cançoners."
echo "Per actualitzar-lo, torna a executar aquesta mateixa ordre."
