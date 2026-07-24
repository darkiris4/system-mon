from __future__ import annotations

import tkinter
from pathlib import Path

from PIL import Image

# Scaffolding for the "icon/branding" open item in SPEC.md — a placeholder
# mark exists here, but nothing in main.py/app.py/tray.py calls into this
# module yet. The tray icon still draws a live status-colored dot instead of
# a static brand mark, and the window uses Tk's default icon. Wire these in
# once real branding assets replace the placeholder.
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ICON_ICO_PATH = ASSETS_DIR / "icon.ico"
ICON_PNG_PATH = ASSETS_DIR / "icon.png"


def set_window_icon(window: tkinter.Wm) -> None:
    """Applies the branded icon to a window's title bar/taskbar entry.

    `.ico` via `iconbitmap` is a Windows-only Tk feature (the shipped
    target); on other platforms this silently no-ops instead of raising,
    since dev/testing happens on non-Windows machines too.
    """
    if not ICON_ICO_PATH.exists():
        return
    try:
        window.iconbitmap(str(ICON_ICO_PATH))
    except tkinter.TclError:
        pass


def load_tray_icon_image() -> Image.Image:
    """Loads the static branded mark for the tray icon.

    Not currently used by TrayController, which draws a colored dot
    reflecting live host status (green/amber/red) rather than a fixed brand
    mark — swapping to this would need a design for how status is still
    conveyed (e.g. a colored badge over this mark) before it is enabled.
    """
    return Image.open(ICON_PNG_PATH)
