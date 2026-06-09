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
from .ydotool import YdotoolKeyboard, YdotoolKeyboardError


@dataclass(frozen=True)
class FocusHandle:
    backends: tuple[str, ...]


class TextInjector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._portal: PortalKeyboard | None = (
            PortalKeyboard()
            if self._is_wayland and settings.inject_backend in {"auto", "portal"}
            else None
        )
        self._ydotool: YdotoolKeyboard | None = (
            YdotoolKeyboard(settings.ydotool_command, settings.ydotool_socket)
            if (
                settings.inject_backend == "ydotool"
                or (self._is_wayland and settings.inject_backend == "auto")
            )
            and self._has_ydotool_command()
            else None
        )
        self._portal_prepare_started = False

    @property
    def _is_wayland(self) -> bool:
        return os.getenv("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(
            os.getenv("WAYLAND_DISPLAY")
        )

    def _has_ydotool_command(self) -> bool:
        if os.path.isabs(self.settings.ydotool_command):
            return os.access(self.settings.ydotool_command, os.X_OK)
        return shutil.which(self.settings.ydotool_command) is not None

    def capture_focus(self) -> FocusHandle:
        if self.settings.inject_backend == "clipboard":
            return FocusHandle(("clipboard",))
        if self.settings.inject_backend == "ydotool":
            return FocusHandle(("ydotool", "clipboard"))
        if self.settings.inject_backend == "portal":
            return FocusHandle(("portal", "clipboard"))

        backends: list[str] = []
        if self._ydotool is not None:
            backends.append("ydotool")
        if self._is_wayland and self._portal is not None:
            backends.append("portal")
        backends.append("clipboard")
        return FocusHandle(tuple(backends))

    def prepare(self) -> None:
        if self._portal is None or self._portal_prepare_started:
            return
        if self.settings.inject_backend == "auto" and self._ydotool is not None:
            return
        self._portal_prepare_started = True

        def prepare_portal() -> None:
            try:
                self._portal.prepare()
            except PortalKeyboardError as exc:
                notify("Soniox Dictation: portal indisponível", str(exc))

        threading.Thread(
            target=prepare_portal,
            name="soniox-portal-prepare",
            daemon=True,
        ).start()

    def insert_text(self, text: str, focus: FocusHandle) -> tuple[bool, str]:
        text = text.strip()
        if not text:
            return False, "Transcrição vazia."

        self._set_clipboard(text)
        time.sleep(0.12)
        if self.settings.copy_only:
            return False, "Texto copiado para o clipboard."

        errors: list[str] = []
        for backend in focus.backends:
            if backend == "ydotool":
                if self._ydotool is None:
                    errors.append("ydotool indisponível.")
                    continue
                try:
                    self._ydotool.paste(self.settings.portal_paste_shortcut)
                    return True, "Texto colado com ydotool."
                except YdotoolKeyboardError as exc:
                    errors.append(f"ydotool falhou: {exc}")
                    continue

            if backend == "portal":
                if self._portal is None:
                    errors.append("RemoteDesktop portal indisponível.")
                    continue
                try:
                    self._portal.paste(self.settings.portal_paste_shortcut)
                    return True, "Texto colado com RemoteDesktop portal."
                except PortalKeyboardError as exc:
                    errors.append(f"RemoteDesktop portal falhou: {exc}")
                    continue

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


def wayland_notice(inject_backend: str = "portal") -> str | None:
    if os.getenv("XDG_SESSION_TYPE", "").lower() != "wayland" and not os.getenv(
        "WAYLAND_DISPLAY"
    ):
        return None
    if inject_backend == "ydotool":
        return (
            "Sessão Wayland detectada. Backend ydotool ativo; se a colagem "
            "automática falhar, confira ydotool/ydotoold."
        )
    if inject_backend == "portal":
        return (
            "Sessão Wayland detectada. Backend RemoteDesktop portal ativo; "
            "autorize o controle remoto/teclado se o GNOME pedir."
        )
    return (
        "Sessão Wayland detectada. Se a colagem automática não funcionar, confira "
        "ydotool/ydotoold ou autorize o RemoteDesktop portal."
    )


def settle_focus() -> None:
    time.sleep(0.05)
