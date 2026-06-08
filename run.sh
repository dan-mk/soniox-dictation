#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

export UV_CACHE_DIR="${UV_CACHE_DIR:-"$PWD/.uv-cache"}"
LOCK_FILE="/tmp/soniox-dictation-${UID:-user}.lock"

if command -v flock >/dev/null 2>&1; then
  exec 9>"$LOCK_FILE"
  if ! flock -n 9; then
    echo "Soniox Dictation já está rodando." >&2
    exit 0
  fi
  printf '%s\n' "$$" > "$LOCK_FILE.pid"
fi

if [ ! -f .venv/pyvenv.cfg ] || ! grep -q "include-system-site-packages = true" .venv/pyvenv.cfg; then
  uv venv --system-site-packages --clear
fi

uv sync
exec uv run soniox-dictate "$@"
