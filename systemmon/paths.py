from __future__ import annotations

import sys
from pathlib import Path


def app_dir() -> Path:
    """Directory config.json/logs/ live next to.

    A portable app can be launched from anywhere (a Start Menu shortcut, a
    double-click from Explorer, a shell in an unrelated directory), so this
    must not depend on the current working directory — otherwise each launch
    could scatter config/logs into whatever folder happened to be cwd at the
    time. Resolves to the folder containing the packaged exe (PyInstaller
    onefolder build) when frozen, or the repo root during development.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent
