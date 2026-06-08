#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${XDG_CACHE_HOME:-"$HOME/.cache"}/soniox-dictation"
LOG_FILE="$LOG_DIR/autostart.log"

mkdir -p "$LOG_DIR"
cd "$ROOT_DIR"

exec ./run.sh >> "$LOG_FILE" 2>&1
