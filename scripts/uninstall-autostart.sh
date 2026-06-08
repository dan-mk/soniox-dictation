#!/usr/bin/env bash
set -euo pipefail

AUTOSTART_FILE="${XDG_CONFIG_HOME:-"$HOME/.config"}/autostart/soniox-dictation.desktop"

if [ -f "$AUTOSTART_FILE" ]; then
  rm "$AUTOSTART_FILE"
  echo "Autostart removido: $AUTOSTART_FILE"
else
  echo "Autostart não estava instalado."
fi
