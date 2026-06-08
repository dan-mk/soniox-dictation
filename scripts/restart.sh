#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${XDG_CACHE_HOME:-"$HOME/.cache"}/soniox-dictation"

cd "$ROOT_DIR"
mkdir -p "$LOG_DIR"

"$ROOT_DIR/scripts/stop.sh"
nohup "$ROOT_DIR/scripts/autostart-run.sh" >> "$LOG_DIR/manual-restart.log" 2>&1 &
echo "Soniox Dictation reiniciado."
