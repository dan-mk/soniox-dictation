#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export UV_CACHE_DIR="${UV_CACHE_DIR:-"$ROOT_DIR/.uv-cache"}"
PASTE_SHORTCUT="${1:-}"

if [ "$#" -gt 1 ]; then
  echo "Uso: $0 [ctrl+v|ctrl+shift+v]" >&2
  exit 2
fi

if [ "$PASTE_SHORTCUT" != "" ] && [ "$PASTE_SHORTCUT" != "ctrl+v" ] && [ "$PASTE_SHORTCUT" != "ctrl+shift+v" ]; then
  echo "Atalho de colagem inválido: $PASTE_SHORTCUT" >&2
  exit 2
fi

command_client() {
  local command="$1"
  local paste_shortcut="${2:-}"
  if [ -x "$ROOT_DIR/.venv/bin/soniox-dictate-command" ]; then
    if [ "$paste_shortcut" = "" ]; then
      timeout 4s "$ROOT_DIR/.venv/bin/soniox-dictate-command" "$command"
    else
      timeout 4s "$ROOT_DIR/.venv/bin/soniox-dictate-command" "$command" "$paste_shortcut"
    fi
  else
    if [ "$paste_shortcut" = "" ]; then
      timeout 10s uv run soniox-dictate-command "$command"
    else
      timeout 10s uv run soniox-dictate-command "$command" "$paste_shortcut"
    fi
  fi
}

if command_client toggle "$PASTE_SHORTCUT" >/dev/null 2>&1; then
  exit 0
fi

nohup "$ROOT_DIR/scripts/autostart-run.sh" >/dev/null 2>&1 &

for _ in $(seq 1 30); do
  sleep 0.2
  if command_client start "$PASTE_SHORTCUT" >/dev/null 2>&1; then
    exit 0
  fi
done

echo "Não consegui iniciar/controlar o Soniox Dictation." >&2
exit 1
