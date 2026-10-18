#!/usr/bin/env bash
# Compila el CSS de Tailwind (v3) sense Node: baixa el CLI autònom la primera vegada.
#   ./eines/css.sh            compila i minifica static/app.css
#   ./eines/css.sh --watch    recompila en desar plantilles o JS
set -euo pipefail
cd "$(dirname "$0")/.."
VERSIO=3.4.17
BINARI=eines/tailwindcss
if [ ! -x "$BINARI" ]; then
  case "$(uname -s)-$(uname -m)" in
    Darwin-arm64) PLATAFORMA=macos-arm64 ;;
    Darwin-x86_64) PLATAFORMA=macos-x64 ;;
    Linux-x86_64) PLATAFORMA=linux-x64 ;;
    Linux-aarch64) PLATAFORMA=linux-arm64 ;;
    *) echo "Plataforma no suportada: baixa el binari de https://github.com/tailwindlabs/tailwindcss/releases/tag/v$VERSIO" >&2; exit 1 ;;
  esac
  curl -sfL -o "$BINARI" "https://github.com/tailwindlabs/tailwindcss/releases/download/v$VERSIO/tailwindcss-$PLATAFORMA"
  chmod +x "$BINARI"
fi
if [ "${1:-}" = "--watch" ]; then
  exec "$BINARI" -i canconer/static/src/app.css -o canconer/static/app.css --watch
fi
"$BINARI" -i canconer/static/src/app.css -o canconer/static/app.css --minify
