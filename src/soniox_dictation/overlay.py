from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402


INDICATOR_MARGIN = 16
INDICATOR_WIDTH = 278
INDICATOR_HEIGHT = 64
WINDOW_TITLE_PREFIX = "Soniox Dictation"


CSS = b"""
#overlay {
    background: transparent;
}
#bubble {
    background: rgba(17, 24, 39, 0.94);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 8px;
}
label {
    color: #f7fafc;
    font-family: Inter, system-ui, sans-serif;
}
#row {
    padding: 12px 16px;
}
#dot {
    background: #ef4444;
    border-radius: 6px;
    min-height: 12px;
    min-width: 12px;
}
#title {
    font-size: 15px;
    font-weight: 700;
}
#timer {
    color: #d1d5db;
    font-family: ui-monospace, monospace;
    font-size: 14px;
}
"""


def _install_css(screen: Gdk.Screen | None) -> None:
    if screen is None:
        return
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS)
    Gtk.StyleContext.add_provider_for_screen(
        screen,
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )


def _get_monitor_workarea(screen: Gdk.Screen, monitor_index: int) -> Gdk.Rectangle:
    workarea = screen.get_monitor_workarea(monitor_index)
    if workarea.width > 0 and workarea.height > 0:
        return workarea
    return screen.get_monitor_geometry(monitor_index)


class _IndicatorWindow(Gtk.Window):
    def __init__(
        self,
        on_stop_requested: Callable[[], None] | None = None,
        on_cancel_requested: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self._on_stop_requested = on_stop_requested
        self._on_cancel_requested = on_cancel_requested
        self._is_recording = False

        self.set_decorated(False)
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        self.set_keep_above(True)
        self.set_accept_focus(True)
        self.set_focus_on_map(False)
        self.set_skip_taskbar_hint(False)
        self.set_skip_pager_hint(False)
        self.set_default_size(INDICATOR_WIDTH, INDICATOR_HEIGHT)
        self.set_resizable(False)
        self.add_events(Gdk.EventMask.KEY_PRESS_MASK)
        self.connect("key-press-event", self._on_key_press)
        self.connect("delete-event", self._on_delete_event)

        screen = Gdk.Screen.get_default()
        if screen is not None:
            rgba_visual = screen.get_rgba_visual()
            if rgba_visual is not None:
                self.set_visual(rgba_visual)
        self.set_app_paintable(True)

        self._box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._box.set_name("overlay")
        self.add(self._box)

        self._bubble = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._bubble.set_name("bubble")
        self._bubble.set_size_request(INDICATOR_WIDTH, INDICATOR_HEIGHT)
        self._bubble.set_halign(Gtk.Align.FILL)
        self._bubble.set_valign(Gtk.Align.FILL)

        self._row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._row.set_name("row")
        self._row.set_valign(Gtk.Align.CENTER)
        self._row.set_halign(Gtk.Align.CENTER)

        self._dot = Gtk.Box()
        self._dot.set_name("dot")
        self._dot.set_valign(Gtk.Align.CENTER)

        self._title = Gtk.Label(label="Gravando", xalign=0.5)
        self._title.set_name("title")
        self._timer = Gtk.Label(label="00:00", xalign=0.5)
        self._timer.set_name("timer")

        self._row.pack_start(self._dot, False, False, 0)
        self._row.pack_start(self._title, False, False, 0)
        self._row.pack_start(self._timer, False, False, 0)
        self._bubble.pack_start(self._row, True, True, 0)
        self._box.pack_start(self._bubble, True, True, 0)

        self.set_title("Gravando")

    def show_on_monitor(self, screen: Gdk.Screen, monitor_index: int) -> None:
        workarea = _get_monitor_workarea(screen, monitor_index)
        width = min(INDICATOR_WIDTH, max(workarea.width, 1))
        height = min(INDICATOR_HEIGHT, max(workarea.height, 1))
        x = workarea.x + min(INDICATOR_MARGIN, max(workarea.width - width, 0))
        y = workarea.y + min(INDICATOR_MARGIN, max(workarea.height - height, 0))

        self.unfullscreen()
        self.unmaximize()
        self.set_default_size(width, height)
        self.move(x, y)
        self.resize(width, height)
        self.show_all()

    def set_recording(self, is_recording: bool) -> None:
        self._is_recording = is_recording

    def set_title(self, text: str) -> None:
        super().set_title(f"{WINDOW_TITLE_PREFIX} - {text}")
        self._title.set_text(text)

    def set_timer(self, text: str) -> None:
        self._timer.set_text(text)

    def hide_overlay(self) -> None:
        self.hide()
        self.unmaximize()

    def _on_key_press(self, _widget: Gtk.Widget, event: Gdk.EventKey) -> bool:
        if not self._is_recording:
            return False
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_ISO_Enter):
            if self._on_stop_requested is not None:
                self._on_stop_requested()
            return True
        if event.keyval == Gdk.KEY_Escape:
            if self._on_cancel_requested is not None:
                self._on_cancel_requested()
            return True
        return False

    def _on_delete_event(self, *_args: object) -> bool:
        if self._is_recording and self._on_cancel_requested is not None:
            self._on_cancel_requested()
        else:
            self.hide_overlay()
        return True


class RecordingOverlay:
    def __init__(
        self,
        on_stop_requested: Callable[[], None] | None = None,
        on_cancel_requested: Callable[[], None] | None = None,
    ) -> None:
        self._on_stop_requested = on_stop_requested
        self._on_cancel_requested = on_cancel_requested
        self._windows: list[_IndicatorWindow] = []
        self._seconds = 0
        self._timer_id = 0
        self._is_recording = False

        _install_css(Gdk.Screen.get_default())

    def start_recording(self) -> None:
        self._seconds = 0
        self._is_recording = True
        self._ensure_windows()
        for window in self._windows:
            window.set_tooltip_text(None)
            window.set_recording(True)
            window.set_title("Gravando")
            window.set_timer("00:00")
        self._show_all_monitors()
        self._start_timer()

    def set_stopping(self) -> None:
        self._is_recording = False
        self._stop_timer()
        for window in self._windows:
            window.set_recording(False)
            window.set_title("Finalizando")

    def set_done(self, _message: str) -> None:
        self._is_recording = False
        self._stop_timer()
        for window in self._windows:
            window.set_recording(False)
            window.set_title("Concluído")
        GLib.timeout_add(1000, self._hide_once)

    def set_error(self, _message: str) -> None:
        self._is_recording = False
        self._stop_timer()
        for window in self._windows:
            window.set_recording(False)
            window.set_title("Erro")
        GLib.timeout_add(4500, self._hide_once)

    def hide_for_paste(self) -> None:
        self.hide_now()

    def hide_now(self) -> None:
        self._is_recording = False
        self._stop_timer()
        self._hide_windows()
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)

    def _ensure_windows(self) -> None:
        screen = Gdk.Screen.get_default()
        monitor_count = screen.get_n_monitors() if screen is not None else 1
        monitor_count = max(monitor_count, 1)

        while len(self._windows) < monitor_count:
            self._windows.append(
                _IndicatorWindow(self._on_stop_requested, self._on_cancel_requested)
            )
        while len(self._windows) > monitor_count:
            window = self._windows.pop()
            window.hide_overlay()
            window.destroy()

    def _show_all_monitors(self) -> None:
        screen = Gdk.Screen.get_default()
        if screen is None:
            return
        for monitor_index, window in enumerate(self._windows):
            window.show_on_monitor(screen, monitor_index)

    def _tick(self) -> bool:
        self._seconds += 1
        minutes, seconds = divmod(self._seconds, 60)
        text = f"{minutes:02d}:{seconds:02d}"
        for window in self._windows:
            window.set_timer(text)
        return True

    def _start_timer(self) -> None:
        self._stop_timer()
        self._timer_id = GLib.timeout_add_seconds(1, self._tick)

    def _stop_timer(self) -> None:
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = 0

    def _hide_once(self) -> bool:
        self._hide_windows()
        return False

    def _hide_windows(self) -> None:
        for window in self._windows:
            window.set_recording(False)
            window.hide_overlay()
