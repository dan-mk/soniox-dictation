from __future__ import annotations

import ast
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


MEDIA_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
CUSTOM_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
CUSTOM_KEY = "custom-keybindings"


@dataclass(frozen=True)
class Shortcut:
    path: str
    name: str
    binding: str
    command: str


class RecordingShortcutManager:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(__file__).resolve().parents[2]
        key_script = self.root / "scripts" / "key-action.sh"
        command = shlex.quote(str(key_script))
        self._shortcuts = (
            Shortcut(
                path="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/soniox_dictation_recording_enter/",
                name="Soniox Dictation (Enter finaliza)",
                binding="Return",
                command=f"{command} stop",
            ),
            Shortcut(
                path="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/soniox_dictation_recording_keypad_enter/",
                name="Soniox Dictation (Enter numerico finaliza)",
                binding="KP_Enter",
                command=f"{command} stop",
            ),
            Shortcut(
                path="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/soniox_dictation_recording_escape/",
                name="Soniox Dictation (Esc cancela)",
                binding="Escape",
                command=f"{command} cancel",
            ),
        )
        self._enabled = False
        self._warned = False

    def enable(self) -> None:
        try:
            self._enable()
            self._enabled = True
        except Exception as exc:
            self._enabled = False
            try:
                self._disable()
            except Exception:
                pass
            self._warn(f"Nao consegui ativar Enter/Esc globais: {exc}")

    def disable(self) -> None:
        try:
            self._disable()
        except Exception as exc:
            if self._enabled:
                self._warn(f"Nao consegui remover Enter/Esc globais: {exc}")
        finally:
            self._enabled = False

    def _enable(self) -> None:
        bindings = self._get_bindings()
        original_bindings = list(bindings)
        for shortcut in self._shortcuts:
            if shortcut.path not in bindings:
                bindings.append(shortcut.path)
        if bindings != original_bindings:
            self._set_bindings(bindings)

        for shortcut in self._shortcuts:
            schema = f"{CUSTOM_SCHEMA}:{shortcut.path}"
            self._run_gsettings("set", schema, "name", shortcut.name)
            self._run_gsettings("set", schema, "command", shortcut.command)
            self._run_gsettings("set", schema, "binding", shortcut.binding)

    def _disable(self) -> None:
        shortcut_paths = {shortcut.path for shortcut in self._shortcuts}
        bindings = [
            item for item in self._get_bindings() if item not in shortcut_paths
        ]
        self._set_bindings(bindings)

        for shortcut in self._shortcuts:
            schema = f"{CUSTOM_SCHEMA}:{shortcut.path}"
            for key in ("name", "command", "binding"):
                subprocess.run(
                    ["gsettings", "reset", schema, key],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

    def _get_bindings(self) -> list[str]:
        return self._parse_bindings(self._run_gsettings("get", MEDIA_SCHEMA, CUSTOM_KEY))

    def _set_bindings(self, bindings: list[str]) -> None:
        value = "[" + ", ".join(repr(item) for item in bindings) + "]"
        self._run_gsettings("set", MEDIA_SCHEMA, CUSTOM_KEY, value)

    def _run_gsettings(self, *args: str) -> str:
        result = subprocess.run(
            ["gsettings", *args],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout.strip()

    def _parse_bindings(self, raw: str) -> list[str]:
        raw = raw.strip()
        if raw.startswith("@as "):
            raw = raw[4:]
        if raw == "[]":
            return []
        value = ast.literal_eval(raw)
        if not isinstance(value, list):
            raise ValueError(f"Valor inesperado em {CUSTOM_KEY}: {raw}")
        return [str(item) for item in value]

    def _warn(self, message: str) -> None:
        if self._warned:
            return
        self._warned = True
        print(f"Soniox Dictation: {message}", file=sys.stderr)
