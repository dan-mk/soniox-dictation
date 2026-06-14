#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${XDG_CACHE_HOME:-"$HOME/.cache"}/soniox-dictation"

cd "$ROOT_DIR"
mkdir -p "$LOG_DIR"

"$ROOT_DIR/scripts/stop.sh"

if command -v systemd-run >/dev/null 2>&1 && timeout 3s systemctl --user show-environment >/dev/null 2>&1; then
  timeout 3s systemctl --user import-environment \
    DISPLAY \
    WAYLAND_DISPLAY \
    XDG_CURRENT_DESKTOP \
    XDG_SESSION_TYPE \
    DBUS_SESSION_BUS_ADDRESS >/dev/null 2>&1 || true
  if timeout 5s systemd-run \
    --user \
    --unit=soniox-dictation \
    --collect \
    --working-directory="$ROOT_DIR" \
    "$ROOT_DIR/scripts/autostart-run.sh" >/dev/null; then
    echo "Soniox Dictation reiniciado."
    exit 0
  fi
fi

nohup "$ROOT_DIR/scripts/autostart-run.sh" >> "$LOG_DIR/manual-restart.log" 2>&1 &
echo "Soniox Dictation reiniciado."
