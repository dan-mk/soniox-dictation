from __future__ import annotations

import argparse
import asyncio
import os
import signal
import sys
import threading
import time

# GNOME Wayland ignores absolute positioning for normal GTK toplevels. Prefer
# XWayland when available so compact indicator windows can be placed per monitor.
if (
    "GDK_BACKEND" not in os.environ
    and (
        os.getenv("XDG_SESSION_TYPE", "").lower() == "wayland"
        or os.getenv("WAYLAND_DISPLAY")
    )
    and os.getenv("DISPLAY")
):
    os.environ["GDK_BACKEND"] = "x11,wayland"

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from .config import SUPPORTED_PASTE_SHORTCUTS, Settings, load_settings
from .gnome_shortcuts import RecordingShortcutManager
from .inject import TextInjector, notify, wayland_notice
from .ipc import IpcServer
from .overlay import RecordingOverlay
from .soniox import transcribe_realtime


class TranscriptionThread(threading.Thread):
    def __init__(self, settings: Settings, controller: "DictationController") -> None:
        super().__init__(name="soniox-transcription", daemon=True)
        self.settings = settings
        self.controller = controller
        self._stop_event = threading.Event()

    def request_stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        try:
            text = asyncio.run(
                transcribe_realtime(
                    self.settings,
                    self._stop_event,
                    lambda update: GLib.idle_add(self.controller.on_progress, update),
                )
            )
            GLib.idle_add(self.controller.on_completed, text)
        except Exception as exc:
            GLib.idle_add(self.controller.on_failed, str(exc))


class DictationController:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.overlay = RecordingOverlay(self.stop_recording, self.cancel_recording)
        self.recording_shortcuts = RecordingShortcutManager()
        self.injector = TextInjector(settings)
        self.worker: TranscriptionThread | None = None
        self.active_paste_shortcut: str | None = None
        self.cancel_requested = False
        self.ipc = IpcServer(self.handle_ipc_command)

    def start(self) -> None:
        notice = wayland_notice()
        if notice:
            print(notice, file=sys.stderr)
        self.recording_shortcuts.disable()
        self.ipc.start()

        print(
            "Soniox Dictation rodando. Ctrl+Espaço cola com Ctrl+V; "
            "Ctrl+Shift+Espaço cola com Ctrl+Shift+V; durante a gravação, "
            "Enter finaliza e Esc cancela.",
            flush=True,
        )
        if notice:
            notify("Soniox Dictation", "Wayland detectado; veja o terminal se o atalho falhar.")

    def start_recording(self, paste_shortcut: str | None = None) -> bool:
        if self.worker is not None:
            return False

        self.active_paste_shortcut = paste_shortcut
        self.cancel_requested = False
        self.worker = TranscriptionThread(self.settings, self)
        self.overlay.start_recording()
        self.recording_shortcuts.enable()
        self.worker.start()

        return False

    def toggle_recording(self) -> bool:
        if self.worker is None:
            return self.start_recording()
        return self.stop_recording()

    def stop_recording(self) -> bool:
        if self.worker is None:
            self.recording_shortcuts.disable()
            return False
        self.recording_shortcuts.disable()
        self.overlay.set_stopping()
        self.worker.request_stop()
        return False

    def cancel_recording(self) -> bool:
        if self.worker is None:
            self.recording_shortcuts.disable()
            return False
        self.recording_shortcuts.disable()
        self.cancel_requested = True
        self.overlay.hide_now()
        self.worker.request_stop()
        return False

    def on_progress(self, _text: str) -> bool:
        return False

    def on_completed(self, text: str) -> bool:
        self.worker = None
        self.recording_shortcuts.disable()

        if self.cancel_requested:
            self.cancel_requested = False
            self.active_paste_shortcut = None
            self.overlay.hide_now()
            return False

        self.overlay.hide_for_paste()
        time.sleep(0.35)
        ok, message = self.injector.insert_text(
            text,
            self.active_paste_shortcut,
        )
        self.active_paste_shortcut = None
        time.sleep(0.2)
        self.overlay.set_done(message)
        if not ok:
            notify("Soniox Dictation", message)

        return False

    def on_failed(self, message: str) -> bool:
        self.worker = None
        self.recording_shortcuts.disable()

        if self.cancel_requested:
            self.cancel_requested = False
            self.active_paste_shortcut = None
            self.overlay.hide_now()
            return False

        self.active_paste_shortcut = None
        self.overlay.set_error(message)
        notify("Soniox Dictation: erro", message)
        return False

    def shutdown(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            self.worker.request_stop()
            self.worker.join(1.5)
        self.recording_shortcuts.disable()
        self.ipc.stop()

    def handle_ipc_command(self, command: str) -> str:
        done = threading.Event()
        response: dict[str, str] = {}

        def apply() -> bool:
            response["value"] = self._apply_ipc_command(command)
            done.set()
            return False

        GLib.idle_add(apply)
        if not done.wait(2.0):
            return "error timeout"
        return response["value"]

    def _apply_ipc_command(self, command: str) -> str:
        action, paste_shortcut, error = self._parse_ipc_command(command)
        if error:
            return error

        if action == "start":
            if self.worker is not None:
                return "ok recording"
            self.start_recording(paste_shortcut)
            return "ok started"
        if action == "stop":
            if self.worker is None:
                self.recording_shortcuts.disable()
                return "ok idle"
            self.stop_recording()
            return "ok stopping"
        if action == "cancel":
            if self.worker is None:
                self.recording_shortcuts.disable()
                return "ok idle"
            self.cancel_recording()
            return "ok cancelling"
        if action == "toggle":
            if self.worker is None:
                self.start_recording(paste_shortcut)
                return "ok started"
            self.stop_recording()
            return "ok stopping"
        if action == "status":
            return "recording" if self.worker is not None else "idle"
        if action == "quit":
            if self.worker is not None:
                self.stop_recording()
            GLib.timeout_add(100, Gtk.main_quit)
            return "ok quitting"
        return f"error comando inválido: {command!r}"

    def _parse_ipc_command(self, command: str) -> tuple[str, str | None, str | None]:
        parts = command.split()
        if not parts:
            return "", None, "error comando vazio"

        action = parts[0]
        if action not in {"start", "stop", "cancel", "toggle", "status", "quit"}:
            return action, None, f"error comando inválido: {command!r}"
        if len(parts) > 2:
            return action, None, f"error comando inválido: {command!r}"
        if len(parts) == 1:
            return action, None, None

        paste_shortcut = parts[1]
        if action not in {"start", "toggle"}:
            return action, None, "error atalho de colagem só vale para start/toggle"
        if paste_shortcut not in SUPPORTED_PASTE_SHORTCUTS:
            return action, None, f"error atalho de colagem inválido: {paste_shortcut!r}"
        return action, paste_shortcut, None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ditado Soniox em tempo real.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    parse_args(sys.argv[1:] if argv is None else argv)
    try:
        settings = load_settings()
    except Exception as exc:
        print(f"Erro de configuração: {exc}", file=sys.stderr)
        return 2

    ok, _ = Gtk.init_check(sys.argv[:1])
    if not ok:
        print("Erro: GTK não conseguiu abrir uma sessão gráfica.", file=sys.stderr)
        return 3

    controller = DictationController(settings)
    controller.start()

    def quit_app(*_: object) -> None:
        controller.shutdown()
        Gtk.main_quit()

    signal.signal(signal.SIGINT, quit_app)
    signal.signal(signal.SIGTERM, quit_app)
    GLib.timeout_add(250, lambda: True)

    try:
        Gtk.main()
    finally:
        controller.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
