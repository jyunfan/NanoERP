#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

TTYD_HOST="${TTYD_HOST:-127.0.0.1}"
TTYD_PORT_WAS_SET=0
if [[ "${TTYD_PORT+x}" == "x" ]]; then
  TTYD_PORT_WAS_SET=1
fi
TTYD_PORT="${TTYD_PORT:-7681}"
TTYD_CREDENTIAL="${TTYD_CREDENTIAL:-nanoerp:nanoerp}"

ttyd_supports_option() {
  ttyd --help 2>&1 | grep -q -- "$1"
}

port_is_available() {
  python3 - "$TTYD_HOST" "$1" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    try:
        sock.bind((host, port))
    except OSError:
        sys.exit(1)
PY
}

if [[ -z "${TTYD_PORT:-}" ]]; then
  TTYD_PORT=7681
fi

if [[ "$TTYD_PORT_WAS_SET" == "0" && "${TTYD_PORT}" == "7681" ]]; then
  for candidate_port in $(seq "$TTYD_PORT" "$((TTYD_PORT + 20))"); do
    if port_is_available "$candidate_port"; then
      TTYD_PORT="$candidate_port"
      break
    fi
  done
fi

if ! port_is_available "$TTYD_PORT"; then
  echo "Port ${TTYD_PORT} is already in use. Set TTYD_PORT to another value." >&2
  exit 1
fi

args=(
  -i "$TTYD_HOST" \
  -p "$TTYD_PORT" \
  -c "$TTYD_CREDENTIAL" \
  -w "$PWD" \
  -T xterm-256color \
  -t titleFixed=NanoERP \
  -t fontSize=16 \
  -t fontFamily=Menlo,monospace
)

if ttyd_supports_option "--writable"; then
  args+=(-W)
fi

echo "Starting NanoERP ttyd on http://${TTYD_HOST}:${TTYD_PORT}" >&2

exec ttyd "${args[@]}" \
  /usr/bin/env -u NO_COLOR \
    COLORTERM=truecolor \
    TERM=xterm-256color \
    FORCE_COLOR=1 \
    uv run main.py
