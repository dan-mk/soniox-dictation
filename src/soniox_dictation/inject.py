from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from .config import Settings
from .portal import PortalKeyboard, PortalKeyboardError


@dataclass(frozen=True)
class FocusHandle:
    backend: str


class TextInjector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._portal: PortalKeyboard | None = PortalKeyboard() if self._is_wayland else None
        self._portal_prepare_started = False

    @property
    def _is_wayland(self) -> bool:
        return os.getenv("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(os.getenv("WAYLAND_DISPLAY"))

    def capture_focus(self) -> FocusHandle:
        if self._is_wayland and self._portal is not None:
            return FocusHandle("portal")
        return FocusHandle("clipboard")

    def prepare(self) -> None:
        if self._portal is None or self._portal_prepare_started:
            return
        self._portal_prepare_started = True

        def prepare_portal() -> None:
            try:
                self._portal.prepare()
            except PortalKeyboardError as exc:
                notify("Soniox Dictation: portal indisponível", str(exc))

        threading.Thread(target=prepare_portal, name="soniox-portal-prepare", daemon=True).start()

    def insert_text(self, text: str, focus: FocusHandle) -> tuple[bool, str]:
        text = text.strip()
        if not text:
            return False, "Transcrição vazia."

        self._set_clipboard(text)
        time.sleep(0.12)
        if self.settings.copy_only:
            return False, "Texto copiado para o clipboard."

        portal_error = ""
        if focus.backend == "portal" and self._portal is not None:
            try:
                self._portal.paste(self.settings.portal_paste_shortcut)
                return True, "Texto colado com RemoteDesktop portal."
            except PortalKeyboardError as exc:
                portal_error = str(exc)

        if portal_error:
            return False, f"RemoteDesktop portal falhou; texto ficou no clipboard. {portal_error}"
        return False, "Não consegui digitar automaticamente; texto ficou no clipboard."

    def _set_clipboard(self, text: str) -> None:
        if self._is_wayland and shutil.which("wl-copy"):
            subprocess.run(["wl-copy"], input=text, text=True, check=True)
            return

        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        old_text = clipboard.wait_for_text() or ""
        clipboard.set_text(text, -1)
        clipboard.store()

        if self.settings.restore_clipboard:
            GLib.timeout_add(1500, self._restore_clipboard_if_unchanged, text, old_text)

    def _restore_clipboard_if_unchanged(self, expected: str, previous: str) -> bool:
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        if clipboard.wait_for_text() == expected:
            clipboard.set_text(previous, -1)
            clipboard.store()
        return False


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
    if os.getenv("XDG_SESSION_TYPE", "").lower() != "wayland" and not os.getenv("WAYLAND_DISPLAY"):
        return None
    return (
        "Sessão Wayland detectada. Se o atalho ou a colagem não funcionarem em "
        "apps nativos Wayland, autorize o RemoteDesktop portal."
    )


def settle_focus() -> None:
    time.sleep(0.05)
