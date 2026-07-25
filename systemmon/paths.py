from __future__ import annotations

import sys
from pathlib import Path


def app_dir() -> Path:
    """Directory config.json/logs/ live in.

    A portable app can be launched from anywhere (a Start Menu shortcut, a
    double-click from Explorer, a shell in an unrelated directory), so this
    must not depend on the current working directory — otherwise each launch
    could scatter config/logs into whatever folder happened to be cwd at the
    time. Resolves to the folder containing the packaged exe (PyInstaller
    onefolder build) when frozen on Windows/Linux, or the repo root during
    development.

    macOS is the odd one out: the packaged build is a code-signed .app
    bundle, and writing config/logs next to the exe means writing inside
    that bundle — which invalidates its signature seal the moment the app
    first runs, turning a normal "unidentified developer" Gatekeeper prompt
    into a hard "sealed resource is missing or invalid" rejection with no
    override. So on macOS this resolves outside the bundle instead, to the
    platform's standard per-user app data location.
    """
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            path = Path.home() / "Library" / "Application Support" / "SystemMon"
        else:
            path = Path(sys.executable).resolve().parent
    else:
        path = Path(__file__).resolve().parent.parent
    path.mkdir(parents=True, exist_ok=True)
    return path
