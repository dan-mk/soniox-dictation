from __future__ import annotations

import threading
import uuid

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gio, GLib  # noqa: E402


BUS_NAME = "org.freedesktop.portal.Desktop"
OBJECT_PATH = "/org/freedesktop/portal/desktop"
REMOTE_DESKTOP_IFACE = "org.freedesktop.portal.RemoteDesktop"
REQUEST_IFACE = "org.freedesktop.portal.Request"
KEYBOARD_DEVICE = 1
KEY_RELEASED = 0
KEY_PRESSED = 1
KEYSYM_CONTROL_L = 0xFFE3
KEYSYM_SHIFT_L = 0xFFE1
KEYSYM_V = ord("v")


class PortalKeyboardError(RuntimeError):
    pass


class PortalKeyboard:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._bus: Gio.DBusConnection | None = None
        self._session_handle: str | None = None

    def paste(self, shortcut: str = "ctrl+v") -> None:
        self.prepare()
        assert self._session_handle is not None

        sequence = [(KEYSYM_CONTROL_L, KEY_PRESSED)]
        if shortcut == "ctrl+shift+v":
            sequence.append((KEYSYM_SHIFT_L, KEY_PRESSED))
        sequence.extend([(KEYSYM_V, KEY_PRESSED), (KEYSYM_V, KEY_RELEASED)])
        if shortcut == "ctrl+shift+v":
            sequence.append((KEYSYM_SHIFT_L, KEY_RELEASED))
        sequence.append((KEYSYM_CONTROL_L, KEY_RELEASED))

        for keysym, state in sequence:
            self._notify_keysym(keysym, state)
            GLib.usleep(60_000)

    def prepare(self) -> None:
        self._ensure_session()

    def _ensure_session(self) -> None:
        with self._lock:
            if self._session_handle is not None:
                return

            self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            create_results = self._call_request(
                "CreateSession",
                GLib.Variant(
                    "(a{sv})",
                    ({
                        "handle_token": GLib.Variant("s", self._token()),
                        "session_handle_token": GLib.Variant("s", self._token()),
                    },),
                ),
            )
            session_handle = self._plain(create_results.get("session_handle"))
            if not isinstance(session_handle, str) or not session_handle:
                raise PortalKeyboardError("RemoteDesktop portal não retornou session_handle.")

            self._call_request(
                "SelectDevices",
                GLib.Variant(
                    "(oa{sv})",
                    (
                        session_handle,
                        {
                            "handle_token": GLib.Variant("s", self._token()),
                            "types": GLib.Variant("u", KEYBOARD_DEVICE),
                        },
                    ),
                ),
            )
            self._call_request(
                "Start",
                GLib.Variant(
                    "(osa{sv})",
                    (
                        session_handle,
                        "",
                        {
                            "handle_token": GLib.Variant("s", self._token()),
                        },
                    ),
                ),
                timeout_seconds=120,
            )
            self._session_handle = session_handle

    def _call_request(
        self,
        method: str,
        parameters: GLib.Variant,
        timeout_seconds: int = 60,
    ) -> dict:
        bus = self._require_bus()
        result = bus.call_sync(
            BUS_NAME,
            OBJECT_PATH,
            REMOTE_DESKTOP_IFACE,
            method,
            parameters,
            GLib.VariantType("(o)"),
            Gio.DBusCallFlags.NONE,
            timeout_seconds * 1000,
            None,
        )
        request_handle = result.unpack()[0]
        return self._wait_response(request_handle, timeout_seconds)

    def _wait_response(self, request_handle: str, timeout_seconds: int) -> dict:
        bus = self._require_bus()
        loop = GLib.MainLoop()
        response_data: dict[str, object] = {}

        def on_response(
            _connection: Gio.DBusConnection,
            _sender_name: str,
            _object_path: str,
            _interface_name: str,
            _signal_name: str,
            parameters: GLib.Variant,
        ) -> None:
            response, results = parameters.unpack()
            response_data["response"] = response
            response_data["results"] = results
            loop.quit()

        def on_timeout() -> bool:
            response_data["timeout"] = True
            loop.quit()
            return False

        subscription = bus.signal_subscribe(
            BUS_NAME,
            REQUEST_IFACE,
            "Response",
            request_handle,
            None,
            Gio.DBusSignalFlags.NONE,
            on_response,
        )
        timeout_id = GLib.timeout_add_seconds(timeout_seconds, on_timeout)

        try:
            loop.run()
        finally:
            bus.signal_unsubscribe(subscription)
            if not response_data.get("timeout"):
                GLib.source_remove(timeout_id)

        if response_data.get("timeout"):
            raise PortalKeyboardError("Timeout aguardando resposta do RemoteDesktop portal.")

        response = int(response_data.get("response", 2))
        if response != 0:
            raise PortalKeyboardError(f"Permissão do RemoteDesktop portal negada/cancelada ({response}).")

        results = response_data.get("results", {})
        return results if isinstance(results, dict) else {}

    def _notify_keysym(self, keysym: int, state: int) -> None:
        bus = self._require_bus()
        if self._session_handle is None:
            raise PortalKeyboardError("Sessão do RemoteDesktop portal não foi iniciada.")

        bus.call_sync(
            BUS_NAME,
            OBJECT_PATH,
            REMOTE_DESKTOP_IFACE,
            "NotifyKeyboardKeysym",
            GLib.Variant("(oa{sv}iu)", (self._session_handle, {}, keysym, state)),
            None,
            Gio.DBusCallFlags.NONE,
            5000,
            None,
        )

    def _require_bus(self) -> Gio.DBusConnection:
        if self._bus is None:
            raise PortalKeyboardError("D-Bus da sessão não foi inicializado.")
        return self._bus

    @staticmethod
    def _token() -> str:
        return "soniox_" + uuid.uuid4().hex

    @staticmethod
    def _plain(value: object) -> object:
        return value.unpack() if isinstance(value, GLib.Variant) else value
