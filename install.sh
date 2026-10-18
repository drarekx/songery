#!/bin/bash
# Instal·lador de Cançoners (també serveix per actualitzar-lo).
#   curl -fsSL https://raw.githubusercontent.com/drarekx/songery/main/install.sh | bash
set -euo pipefail

REPO="drarekx/songery"
URL="https://github.com/$REPO/releases/latest/download/Canconers.zip"
APP="Cançoners.app"
EQUIP="3HWTS4AVPU"  # Team ID de la signatura (Developer ID) de les versions publicades
DADES="$HOME/Library/Application Support/Cançoners"

negreta() { printf "\033[1m%s\033[0m\n" "$*"; }
error() { printf "\033[31mError:\033[0m %s\n" "$*" >&2; exit 1; }

[[ "$(uname)" == "Darwin" ]] || error "Cançoners només funciona en macOS."
major=$(sw_vers -productVersion | cut -d. -f1)
(( major >= 12 )) || error "Cançoners necessita macOS 12 (Monterey) o posterior. Tens $(sw_vers -productVersion)."
[[ "$(uname -m)" == "arm64" ]] || error "Aquesta versió de Cançoners és per a Macs amb Apple Silicon (M1 o posterior)."

versio=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest" 2>/dev/null | sed -nE 's/.*"tag_name": *"v?([^"]+)".*/\1/p' | head -1 || true)
negreta "Descarregant Cançoners ${versio:-(última versió)}…"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
curl -fL --progress-bar "$URL" -o "$tmp/Canconers.zip" || error "No s'ha pogut descarregar $URL"
ditto -x -k "$tmp/Canconers.zip" "$tmp"
[[ -d "$tmp/$APP" ]] || error "El fitxer descarregat no conté $APP"

# Només s'instal·la si la signatura és vàlida i és la nostra.
negreta "Comprovant la signatura…"
codesign --verify --deep --strict "$tmp/$APP" 2>/dev/null || error "La signatura de l'app descarregada no és vàlida. No s'ha instal·lat res."
codesign -dv "$tmp/$APP" 2>&1 | grep -q "TeamIdentifier=$EQUIP" || error "L'app descarregada no està signada per l'equip esperat. No s'ha instal·lat res."

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
# La versió anterior es guarda fins que la nova arrenca bé.
anterior=""
if [[ -d "$desti/$APP" ]]; then
    # La versió nova ho dirà en obrir-se (i de quina venia).
    versio_anterior=$(defaults read "$desti/$APP/Contents/Info" CFBundleShortVersionString 2>/dev/null || true)
    mkdir -p "$DADES"
    printf '{"de": "%s"}\n' "${versio_anterior:-?}" > "$DADES/actualitzada.json"
    anterior="$tmp/anterior.app"
    mv "$desti/$APP" "$anterior"
fi
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

# Obre la versió nova i espera que el servidor respongui. Si no arrenca, torna a l'anterior.
negreta "Obrint la versió nova…"
inici=$(date +%s)
open "$desti/$APP"
arrencada=0
for _ in $(seq 60); do
    sleep 1
    if [[ -f "$DADES/servidor.json" ]] && (( $(stat -f %m "$DADES/servidor.json") >= inici )); then
        url=$(sed -E 's/.*"url": *"([^"]+)".*/\1/' "$DADES/servidor.json")
        if curl -fs -o /dev/null --max-time 2 "$url"; then arrencada=1; break; fi
    fi
done
if (( ! arrencada )) && [[ -n "$anterior" ]]; then
    pkill -f "$APP/Contents/MacOS/" 2>/dev/null || true
    sleep 1
    rm -rf "$desti/$APP" "$DADES/actualitzada.json"
    mv "$anterior" "$desti/$APP"
    open "$desti/$APP"
    error "La versió nova no ha arrencat i s'ha tornat a l'anterior. Les còpies de seguretat de les dades són a $DADES/copies."
fi
negreta "Fet! Cançoners s'obre al navegador i té una icona a la barra de menú."
echo "Les teves dades són a ~/Library/Application Support/Cançoners."
echo "Per actualitzar-lo, torna a executar aquesta mateixa ordre."
