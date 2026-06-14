#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACTION="${1:-}"

cd "$ROOT_DIR"
export UV_CACHE_DIR="${UV_CACHE_DIR:-"$ROOT_DIR/.uv-cache"}"

if [ "$ACTION" != "stop" ] && [ "$ACTION" != "cancel" ]; then
  echo "Uso: $0 stop|cancel" >&2
  exit 2
fi

if [ -x "$ROOT_DIR/.venv/bin/soniox-dictate-command" ]; then
  timeout 4s "$ROOT_DIR/.venv/bin/soniox-dictate-command" "$ACTION" >/dev/null 2>&1 || true
else
  timeout 10s uv run soniox-dictate-command "$ACTION" >/dev/null 2>&1 || true
fi
