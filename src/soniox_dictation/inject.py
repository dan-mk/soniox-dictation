from __future__ import annotations

import os
import shutil
import subprocess
import time

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # noqa: E402

from .config import DEFAULT_PASTE_SHORTCUT, Settings
from .ydotool import YdotoolKeyboard, YdotoolKeyboardError


class TextInjector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._ydotool: YdotoolKeyboard | None = (
            YdotoolKeyboard(settings.ydotool_command, settings.ydotool_socket)
            if self._has_ydotool_command()
            else None
        )

    @property
    def _is_wayland(self) -> bool:
        return os.getenv("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(
            os.getenv("WAYLAND_DISPLAY")
        )

    def _has_ydotool_command(self) -> bool:
        if os.path.isabs(self.settings.ydotool_command):
            return os.access(self.settings.ydotool_command, os.X_OK)
        return shutil.which(self.settings.ydotool_command) is not None

    def insert_text(
        self,
        text: str,
        paste_shortcut: str | None = None,
    ) -> tuple[bool, str]:
        text = text.strip()
        if not text:
            return False, "Transcrição vazia."

        self._set_clipboard(text)
        time.sleep(0.12)

        errors: list[str] = []
        if self._ydotool is None:
            errors.append("ydotool indisponível.")
        else:
            try:
                self._ydotool.paste(paste_shortcut or DEFAULT_PASTE_SHORTCUT)
                return True, "Texto colado com ydotool."
            except YdotoolKeyboardError as exc:
                errors.append(f"ydotool falhou: {exc}")

        if errors:
            return (
                False,
                f"Não consegui colar automaticamente; texto ficou no clipboard. {' '.join(errors)}",
            )
        return False, "Não consegui digitar automaticamente; texto ficou no clipboard."

    def _set_clipboard(self, text: str) -> None:
        if self._is_wayland and shutil.which("wl-copy"):
            subprocess.run(["wl-copy"], input=text, text=True, check=True)
            return

        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()


def notify(summary: str, body: str = "") -> None:
    if not shutil.which("notify-send"):
        return
    try:
        subprocess.Popen(
            ["notify-send", summary, body],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        pass


def wayland_notice() -> str | None:
    if os.getenv("XDG_SESSION_TYPE", "").lower() != "wayland" and not os.getenv(
        "WAYLAND_DISPLAY"
    ):
        return None
    return (
        "Sessão Wayland detectada. A colagem automática usa ydotool; "
        "se falhar, confira ydotool/ydotoold."
    )


def settle_focus() -> None:
    time.sleep(0.05)
