#!/bin/bash
# Torna a fer les captures (docs/imatges) i els vídeos (docs/videos) del README.
# Engega l'app amb unes dades de demostració a part (els cançoners de base, de domini públic) i la
# controla amb un Chromium invisible. Cal ffmpeg (brew install ffmpeg) i Chrome, Edge o Brave.
#
#   bash eines/captures/fes.sh              # tot
#   bash eines/captures/fes.sh captures     # només les captures
#   bash eines/captures/fes.sh videos       # només els vídeos
set -euo pipefail

ARREL="$(cd "$(dirname "$0")/../.." && pwd)"
AQUI="$ARREL/eines/captures"
PYTHON="$ARREL/.venv/bin/python"
PORT="${CAPTURES_PORT:-5391}"
QUE="${1:-tot}"

command -v ffmpeg > /dev/null || { echo "Cal ffmpeg: brew install ffmpeg" >&2; exit 1; }

export CAPTURES_URL="http://127.0.0.1:$PORT"
export CAPTURES_TREBALL="$(mktemp -d -t canconer-captures)"
mkdir -p "$ARREL/docs/imatges" "$ARREL/docs/videos"

CANCONER_DADES="$CAPTURES_TREBALL/dades" "$PYTHON" "$ARREL/app.py" --port "$PORT" --sense-recarrega \
  > "$CAPTURES_TREBALL/servidor.log" 2>&1 &
SERVIDOR=$!
trap 'kill $SERVIDOR 2> /dev/null; wait $SERVIDOR 2> /dev/null || true; rm -rf "$CAPTURES_TREBALL"' EXIT
for _ in $(seq 50); do curl -s -o /dev/null "$CAPTURES_URL/" && break; sleep 0.2; done

# Els cançoners de base: l'adreça on redirigeix acaba amb l'id del cançoner nou.
for clau in nadales populars; do
  curl -s -o /dev/null -w "%{redirect_url}" -X POST "$CAPTURES_URL/canconer/base/$clau" | awk -F/ '{printf "%s", $NF}' \
    > "$CAPTURES_TREBALL/id-$clau.txt"
done

cd "$AQUI"
if [ "$QUE" != captures ]; then
  "$PYTHON" video_1_primera_canco.py
  "$PYTHON" video_2_acords_i_transport.py   # fa servir el cançoner del vídeo 1
  "$PYTHON" video_3_imprimir.py
fi
if [ "$QUE" != videos ]; then
  "$PYTHON" captures.py
fi
echo "Fet: docs/imatges i docs/videos"
