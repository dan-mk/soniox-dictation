#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK_PID="/tmp/soniox-dictation-${UID:-user}.lock.pid"

cd "$ROOT_DIR"
export UV_CACHE_DIR="${UV_CACHE_DIR:-"$ROOT_DIR/.uv-cache"}"

command_client() {
  local command="$1"
  if [ -x "$ROOT_DIR/.venv/bin/soniox-dictate-command" ]; then
    timeout 4s "$ROOT_DIR/.venv/bin/soniox-dictate-command" "$command"
  else
    timeout 10s uv run soniox-dictate-command "$command"
  fi
}

if command_client status 2>/dev/null; then
  exit 0
fi

if [ -f "$LOCK_PID" ]; then
  PID="$(cat "$LOCK_PID" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" >/dev/null 2>&1; then
    echo "rodando sem responder ao socket (pid $PID)"
    exit 0
  fi
fi

echo "parado"
