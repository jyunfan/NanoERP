#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

TTYD_HOST="${TTYD_HOST:-127.0.0.1}"
TTYD_PORT="${TTYD_PORT:-7681}"
TTYD_CREDENTIAL="${TTYD_CREDENTIAL:-nanoerp:nanoerp}"

exec ttyd \
  -i "$TTYD_HOST" \
  -p "$TTYD_PORT" \
  -W \
  -c "$TTYD_CREDENTIAL" \
  -w "$PWD" \
  -T xterm-256color \
  -t titleFixed=NanoERP \
  -t fontSize=16 \
  -t fontFamily=Menlo,monospace \
  /usr/bin/env -u NO_COLOR \
    COLORTERM=truecolor \
    TERM=xterm-256color \
    FORCE_COLOR=1 \
    uv run main.py
