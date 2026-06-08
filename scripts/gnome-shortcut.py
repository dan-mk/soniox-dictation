#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import subprocess
from pathlib import Path


MEDIA_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
CUSTOM_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
CUSTOM_KEY = "custom-keybindings"
SHORTCUT_PATH = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/soniox_dictation/"
BINDING = "<Control>space"


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
    command = str(root / "scripts" / "toggle.sh")

    bindings = get_bindings()
    if SHORTCUT_PATH not in bindings:
        bindings.append(SHORTCUT_PATH)
        set_bindings(bindings)

    schema = f"{CUSTOM_SCHEMA}:{SHORTCUT_PATH}"
    run_gsettings("set", schema, "name", "Soniox Dictation")
    run_gsettings("set", schema, "command", command)
    run_gsettings("set", schema, "binding", BINDING)

    print(f"Atalho GNOME instalado: {BINDING} -> {command}")


def uninstall() -> None:
    bindings = [item for item in get_bindings() if item != SHORTCUT_PATH]
    set_bindings(bindings)

    schema = f"{CUSTOM_SCHEMA}:{SHORTCUT_PATH}"
    for key in ("name", "command", "binding"):
        subprocess.run(["gsettings", "reset", schema, key], check=False)

    print("Atalho GNOME removido.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Instala/remove atalho GNOME para o Soniox Dictation.")
    parser.add_argument("action", choices=["install", "uninstall"])
    args = parser.parse_args()

    if args.action == "install":
        install()
    else:
        uninstall()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
