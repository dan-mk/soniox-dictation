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
from .xdotool import XdotoolKeyboard, XdotoolKeyboardError
from .ydotool import YdotoolKeyboard, YdotoolKeyboardError


class TextInjector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._xdotool: XdotoolKeyboard | None = (
            XdotoolKeyboard()
            if not self._is_wayland and shutil.which("xdotool")
            else None
        )
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

    def capture_target_window(self) -> str | None:
        """Memoriza a janela focada agora (X11), para reativá-la antes de colar."""
        if self._xdotool is None:
            return None
        return self._xdotool.capture_active_window()

    def set_clipboard(self, text: str) -> bool:
        """Copia o texto para o clipboard. Deve rodar na thread principal do GTK
        para que o loop fique livre e consiga servir o clipboard durante o paste."""
        text = text.strip()
        if not text:
            return False
        self._set_clipboard(text)
        return True

    def paste_only(
        self,
        paste_shortcut: str | None = None,
        target_window: str | None = None,
    ) -> tuple[bool, str]:
        """Dispara a tecla de colar. Pode (e deve) rodar fora da thread principal,
        senão o app não responde quando o app de destino pede o clipboard."""
        shortcut = paste_shortcut or DEFAULT_PASTE_SHORTCUT
        errors: list[str] = []

        if self._xdotool is not None:
            try:
                self._xdotool.paste(shortcut, target_window)
                return True, "Texto colado com xdotool."
            except XdotoolKeyboardError as exc:
                errors.append(f"xdotool falhou: {exc}")

        if self._ydotool is not None:
            try:
                self._ydotool.paste(shortcut)
                return True, "Texto colado com ydotool."
            except YdotoolKeyboardError as exc:
                errors.append(f"ydotool falhou: {exc}")

        if self._xdotool is None and self._ydotool is None:
            errors.append("nenhum injetor (xdotool/ydotool) disponível.")

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
