from __future__ import annotations

import platform
import tkinter
from pathlib import Path

from PIL import Image

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
ICON_ICO_PATH = ASSETS_DIR / "icon.ico"
ICON_PNG_PATH = ASSETS_DIR / "icon.png"

_IS_WINDOWS = platform.system() == "Windows"


def set_window_icon(window: tkinter.Wm) -> None:
    """Applies the branded icon to a window's title bar/taskbar entry.

    `.ico` via `iconbitmap` only renders correctly on Windows — Tk doesn't
    actually understand the format elsewhere. On macOS it doesn't raise (so
    a try/except can't gate this): it silently applies the file anyway and
    renders it wrong, so the platform must be checked explicitly instead.
    """
    if not _IS_WINDOWS or not ICON_ICO_PATH.exists():
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
