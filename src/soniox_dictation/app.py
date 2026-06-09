from __future__ import annotations

import argparse
import asyncio
import signal
import sys
import threading
import time

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from .config import Settings, load_settings
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
        self.injector = TextInjector(settings)
        self.worker: TranscriptionThread | None = None
        self.focus = None
        self.cancel_requested = False
        self.ipc = IpcServer(self.handle_ipc_command)

    def start(self) -> None:
        notice = wayland_notice()
        if notice:
            print(notice, file=sys.stderr)
        self.ipc.start()

        print(
            "Soniox Dictation rodando. Ctrl+Espaço inicia; Enter finaliza; Esc cancela.",
            flush=True,
        )
        if notice:
            notify("Soniox Dictation", "Wayland detectado; veja o terminal se o atalho falhar.")
        self.injector.prepare()

    def start_recording(self) -> bool:
        if self.worker is not None:
            return False

        self.focus = self.injector.capture_focus()
        self.cancel_requested = False
        self.overlay.start_recording()

        self.worker = TranscriptionThread(self.settings, self)
        self.worker.start()

        return False

    def toggle_recording(self) -> bool:
        if self.worker is None:
            return self.start_recording()
        return self.stop_recording()

    def stop_recording(self) -> bool:
        if self.worker is None:
            return False
        self.overlay.set_stopping()
        self.worker.request_stop()
        return False

    def cancel_recording(self) -> bool:
        if self.worker is None:
            return False
        self.cancel_requested = True
        self.overlay.hide_now()
        self.worker.request_stop()
        return False

    def on_progress(self, _text: str) -> bool:
        return False

    def on_completed(self, text: str) -> bool:
        self.worker = None

        if self.cancel_requested:
            self.cancel_requested = False
            self.focus = None
            self.overlay.hide_now()
            return False

        self.overlay.hide_for_paste()
        time.sleep(0.35)
        ok, message = self.injector.insert_text(text, self.focus)
        time.sleep(0.2)
        self.overlay.set_done(message)
        if not ok:
            notify("Soniox Dictation", message)

        return False

    def on_failed(self, message: str) -> bool:
        self.worker = None

        if self.cancel_requested:
            self.cancel_requested = False
            self.focus = None
            self.overlay.hide_now()
            return False

        self.overlay.set_error(message)
        notify("Soniox Dictation: erro", message)
        return False

    def shutdown(self) -> None:
        if self.worker is not None and self.worker.is_alive():
            self.worker.request_stop()
            self.worker.join(1.5)
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
        if command == "start":
            if self.worker is not None:
                return "ok recording"
            self.start_recording()
            return "ok started"
        if command == "stop":
            if self.worker is None:
                return "ok idle"
            self.stop_recording()
            return "ok stopping"
        if command == "toggle":
            if self.worker is None:
                self.start_recording()
                return "ok started"
            self.stop_recording()
            return "ok stopping"
        if command == "status":
            return "recording" if self.worker is not None else "idle"
        if command == "quit":
            if self.worker is not None:
                self.stop_recording()
            GLib.timeout_add(100, Gtk.main_quit)
            return "ok quitting"
        return f"error comando inválido: {command!r}"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ditado Soniox em tempo real.")
    parser.add_argument("--debug", action="store_true", help="ativa logs e mensagens extras")
    parser.add_argument(
        "--copy-only",
        action="store_true",
        help="não tenta colar/digitar; apenas deixa a transcrição no clipboard",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        settings = load_settings(debug=args.debug, copy_only=args.copy_only)
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
