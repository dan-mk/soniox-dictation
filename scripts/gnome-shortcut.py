#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import shlex
import subprocess
from pathlib import Path


MEDIA_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
CUSTOM_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
CUSTOM_KEY = "custom-keybindings"
SHORTCUTS = (
    {
        "path": "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/soniox_dictation/",
        "name": "Soniox Dictation (Ctrl+V)",
        "binding": "<Control>space",
        "paste_shortcut": "ctrl+v",
    },
    {
        "path": "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/soniox_dictation_shift/",
        "name": "Soniox Dictation (Ctrl+Shift+V)",
        "binding": "<Control><Shift>space",
        "paste_shortcut": "ctrl+shift+v",
    },
)
RUNTIME_SHORTCUT_PATHS = (
    "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/soniox_dictation_recording_enter/",
    "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/soniox_dictation_recording_keypad_enter/",
    "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/soniox_dictation_recording_escape/",
)


def run_gsettings(*args: str) -> str:
    result = subprocess.run(
        ["gsettings", *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def parse_bindings(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("@as "):
        raw = raw[4:]
    if raw == "[]":
        return []
    value = ast.literal_eval(raw)
    if not isinstance(value, list):
        raise ValueError(f"Valor inesperado em {CUSTOM_KEY}: {raw}")
    return [str(item) for item in value]


def get_bindings() -> list[str]:
    return parse_bindings(run_gsettings("get", MEDIA_SCHEMA, CUSTOM_KEY))


def set_bindings(bindings: list[str]) -> None:
    value = "[" + ", ".join(repr(item) for item in bindings) + "]"
    run_gsettings("set", MEDIA_SCHEMA, CUSTOM_KEY, value)


def install() -> None:
    root = Path(__file__).resolve().parents[1]
    toggle_script = root / "scripts" / "toggle.sh"

    bindings = get_bindings()
    original_bindings = list(bindings)
    for shortcut in SHORTCUTS:
        if shortcut["path"] not in bindings:
            bindings.append(shortcut["path"])
    if bindings != original_bindings:
        set_bindings(bindings)

    for shortcut in SHORTCUTS:
        schema = f"{CUSTOM_SCHEMA}:{shortcut['path']}"
        command = (
            f"{shlex.quote(str(toggle_script))} "
            f"{shlex.quote(shortcut['paste_shortcut'])}"
        )
        run_gsettings("set", schema, "name", shortcut["name"])
        run_gsettings("set", schema, "command", command)
        run_gsettings("set", schema, "binding", shortcut["binding"])

    for shortcut in SHORTCUTS:
        print(
            "Atalho GNOME instalado: "
            f"{shortcut['binding']} -> {toggle_script} {shortcut['paste_shortcut']}"
        )


def cleanup_runtime() -> None:
    shortcut_paths = set(RUNTIME_SHORTCUT_PATHS)
    bindings = [item for item in get_bindings() if item not in shortcut_paths]
    set_bindings(bindings)

    for path in RUNTIME_SHORTCUT_PATHS:
        schema = f"{CUSTOM_SCHEMA}:{path}"
        for key in ("name", "command", "binding"):
            subprocess.run(["gsettings", "reset", schema, key], check=False)

    print("Atalhos temporarios removidos.")


def uninstall() -> None:
    shortcut_paths = {shortcut["path"] for shortcut in SHORTCUTS}
    shortcut_paths.update(RUNTIME_SHORTCUT_PATHS)
    bindings = [item for item in get_bindings() if item not in shortcut_paths]
    set_bindings(bindings)

    for shortcut in SHORTCUTS:
        schema = f"{CUSTOM_SCHEMA}:{shortcut['path']}"
        for key in ("name", "command", "binding"):
            subprocess.run(["gsettings", "reset", schema, key], check=False)
    for path in RUNTIME_SHORTCUT_PATHS:
        schema = f"{CUSTOM_SCHEMA}:{path}"
        for key in ("name", "command", "binding"):
            subprocess.run(["gsettings", "reset", schema, key], check=False)

    print("Atalhos GNOME removidos.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Instala/remove atalho GNOME para o Soniox Dictation.")
    parser.add_argument("action", choices=["install", "uninstall", "cleanup-runtime"])
    args = parser.parse_args()

    if args.action == "install":
        install()
    elif args.action == "uninstall":
        uninstall()
    else:
        cleanup_runtime()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
