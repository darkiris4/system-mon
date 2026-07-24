from __future__ import annotations

import platform
import sys

_APP_NAME = "PingWatch"
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def is_supported() -> bool:
    return platform.system() == "Windows"


def _executable_command() -> str:
    if getattr(sys, "frozen", False):
        # Running from a PyInstaller build: sys.executable *is* the app exe.
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{sys.argv[0]}"'


def set_autostart(enabled: bool) -> None:
    """Registers/unregisters PingWatch in the per-user registry Run key.

    A registry value (rather than a Startup folder shortcut) keeps this a
    one-line write/delete with no extra dependency, matching the "no registry
    dependency except the optional autostart entry" goal in SPEC.md section 7.
    """
    if not is_supported():
        return

    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _executable_command())
        else:
            try:
                winreg.DeleteValue(key, _APP_NAME)
            except FileNotFoundError:
                pass


def is_autostart_enabled() -> bool:
    if not is_supported():
        return False

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, _APP_NAME)
            return True
    except FileNotFoundError:
        return False
