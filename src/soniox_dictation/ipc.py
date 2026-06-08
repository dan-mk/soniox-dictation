from __future__ import annotations

import os
import socket
import tempfile
import threading
from collections.abc import Callable


def socket_path() -> str:
    runtime_dir = os.getenv("XDG_RUNTIME_DIR") or tempfile.gettempdir()
    return os.path.join(runtime_dir, f"soniox-dictation-{os.getuid()}.sock")


class IpcClientError(RuntimeError):
    pass


def send_command(command: str, timeout: float = 2.0) -> str:
    path = socket_path()
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(timeout)
            client.connect(path)
            client.sendall(command.encode("utf-8") + b"\n")
            response = client.recv(4096)
    except OSError as exc:
        raise IpcClientError(f"Não consegui falar com o app em {path}: {exc}") from exc

    return response.decode("utf-8", errors="replace").strip()


class IpcServer:
    def __init__(self, handler: Callable[[str], str]) -> None:
        self.handler = handler
        self.path = socket_path()
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = threading.Event()

    def start(self) -> None:
        if self._socket is not None:
            return

        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(self.path)
        os.chmod(self.path, 0o600)
        server.listen(8)
        server.settimeout(0.2)

        self._socket = server
        self._running.set()
        self._thread = threading.Thread(target=self._serve, name="soniox-ipc", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
        if self._thread is not None:
            self._thread.join(1.0)
            self._thread = None
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def _serve(self) -> None:
        while self._running.is_set():
            server = self._socket
            if server is None:
                return
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue
            except OSError:
                return

            with conn:
                try:
                    raw = conn.recv(1024)
                    command = raw.decode("utf-8", errors="replace").strip()
                    response = self.handler(command)
                except Exception as exc:
                    response = f"error {exc}"
                conn.sendall(response.encode("utf-8") + b"\n")
