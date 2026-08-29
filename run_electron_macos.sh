#!/bin/sh
# Daily launcher (macOS/Linux counterpart of run_electron_utf8.bat).
set -eu
cd "$(dirname "$0")"

export PYTHONUTF8=1 PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1
export RAG_ENABLED_FOR_LOCAL=0 VTS_ENABLED=0 VTS_HEARTBEAT_ENABLED=0 VTS_RECONNECT_ENABLED=0
export AMADEUS_PYTHON="$(pwd)/.venv/bin/python3"

# Refuse to start over a stale backend (vite would bind elsewhere and the
# Electron window would attach to the wrong frontend).
for port in 17777 5173; do
  if command -v lsof >/dev/null && lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[amadeus] port $port is busy; free it first:" >&2
    lsof -nP -iTCP:"$port" -sTCP:LISTEN >&2
    exit 1
  fi
done

cd electron && npm run electron:dev
