from __future__ import annotations

from typing import Callable, Tuple

import pystray
from PIL import Image, ImageDraw

_COLORS: dict[str, Tuple[int, int, int]] = {
    "ok": (46, 160, 67),
    "warn": (219, 154, 4),
    "down": (218, 54, 51),
    "paused": (128, 128, 128),
}


def _make_icon_image(color: Tuple[int, int, int]) -> Image.Image:
    size = 64
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((4, 4, size - 4, size - 4), fill=color)
    return image


class TrayController:
    """Tray icon + menu (Show, Pause/Resume, Quit) and toast notifications.

    pystray was chosen so one small dependency covers both the tray icon and
    native notifications (Icon.notify), instead of pulling in a separate
    toast library (see SPEC.md's "Open Items").
    """

    def __init__(
        self,
        on_show: Callable[[], None],
        on_toggle_pause: Callable[[], None],
        on_quit: Callable[[], None],
    ):
        self._on_show = on_show
        self._on_toggle_pause = on_toggle_pause
        self._on_quit = on_quit
        self._paused = False
        self._last_status = "ok"
        self._icon = pystray.Icon(
            "systemmon",
            _make_icon_image(_COLORS["ok"]),
            "SystemMon",
            menu=pystray.Menu(
                pystray.MenuItem("Show window", self._show),
                pystray.MenuItem("Pause monitoring", self._toggle_pause, checked=lambda item: self._paused),
                pystray.MenuItem("Quit", self._quit),
            ),
        )

    def run_detached(self) -> None:
        self._icon.run_detached()

    def set_status(self, status: str) -> None:
        self._last_status = status.lower()
        # Ticks stop while paused, so this shouldn't normally fire then — but
        # guard anyway rather than let a stale status clobber the gray icon.
        if not self._paused:
            self._icon.icon = _make_icon_image(_COLORS.get(self._last_status, _COLORS["ok"]))

    def set_paused(self, paused: bool) -> None:
        """Mirrors the real pause state (owned by MonitorGroup) into the checkbox and icon."""
        self._paused = paused
        color = _COLORS["paused"] if paused else _COLORS.get(self._last_status, _COLORS["ok"])
        self._icon.icon = _make_icon_image(color)

    def notify(self, title: str, message: str) -> None:
        self._icon.notify(message, title)

    def stop(self) -> None:
        self._icon.stop()

    def _show(self, icon, item) -> None:
        self._on_show()

    def _toggle_pause(self, icon, item) -> None:
        self._on_toggle_pause()

    def _quit(self, icon, item) -> None:
        self._on_quit()
