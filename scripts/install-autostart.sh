#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AUTOSTART_DIR="${XDG_CONFIG_HOME:-"$HOME/.config"}/autostart"
AUTOSTART_FILE="$AUTOSTART_DIR/soniox-dictation.desktop"
LOG_DIR="${XDG_CACHE_HOME:-"$HOME/.cache"}/soniox-dictation"
LOG_FILE="$LOG_DIR/autostart.log"
RUNNER="$ROOT_DIR/scripts/autostart-run.sh"

mkdir -p "$AUTOSTART_DIR" "$LOG_DIR"

cat > "$AUTOSTART_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Soniox Dictation
Comment=Ditado por voz com Soniox em tempo real
Exec=/bin/bash "$RUNNER"
Icon=audio-input-microphone
Terminal=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
EOF

chmod 0644 "$AUTOSTART_FILE"

echo "Autostart instalado em: $AUTOSTART_FILE"
echo "Logs em: $LOG_FILE"
