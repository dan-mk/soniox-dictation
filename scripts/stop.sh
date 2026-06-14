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

if command_client status >/dev/null 2>&1; then
  if command_client quit >/dev/null 2>&1; then
    sleep 1
  fi
fi

if [ -f "$LOCK_PID" ]; then
  PID="$(cat "$LOCK_PID" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" >/dev/null 2>&1; then
    kill "$PID" >/dev/null 2>&1 || true
    sleep 0.5
  fi
  if [ -n "${PID:-}" ] && kill -0 "$PID" >/dev/null 2>&1; then
    kill -9 "$PID" >/dev/null 2>&1 || true
  fi
  rm -f "$LOCK_PID"
fi

pkill -TERM -f "$ROOT_DIR/.venv/bin/soniox-dictate" >/dev/null 2>&1 || true
pkill -TERM -f "uv run soniox-dictate" >/dev/null 2>&1 || true

if command -v systemctl >/dev/null 2>&1; then
  timeout 5s systemctl --user stop soniox-dictation.service soniox-dictation-codex.service >/dev/null 2>&1 || true
  timeout 3s systemctl --user reset-failed soniox-dictation.service soniox-dictation-codex.service >/dev/null 2>&1 || true
fi

"$ROOT_DIR/scripts/gnome-shortcut.py" cleanup-runtime >/dev/null 2>&1 || true

echo "Soniox Dictation parado."
