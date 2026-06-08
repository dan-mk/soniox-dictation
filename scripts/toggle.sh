#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export UV_CACHE_DIR="${UV_CACHE_DIR:-"$ROOT_DIR/.uv-cache"}"

command_client() {
  local command="$1"
  if [ -x "$ROOT_DIR/.venv/bin/soniox-dictate-command" ]; then
    "$ROOT_DIR/.venv/bin/soniox-dictate-command" "$command"
  else
    uv run soniox-dictate-command "$command"
  fi
}

if command_client toggle >/dev/null 2>&1; then
  exit 0
fi

nohup "$ROOT_DIR/scripts/autostart-run.sh" >/dev/null 2>&1 &

for _ in $(seq 1 30); do
  sleep 0.2
  if command_client start >/dev/null 2>&1; then
    exit 0
  fi
done

echo "Não consegui iniciar/controlar o Soniox Dictation." >&2
exit 1
