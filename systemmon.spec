# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for SystemMon.

Build (from the repo root, with the venv activated):
    pyinstaller systemmon.spec

Produces a one-folder (portable) build at dist/SystemMon/ containing
SystemMon.exe and its dependencies — no installer, per SPEC.md's packaging
goal. config.json and logs/ are created next to the exe on first run
(systemmon/paths.py resolves relative to it, not the cwd).

PyInstaller does not cross-compile: running this on macOS/Linux produces a
build for that platform, not a Windows .exe. The actual Windows package must
be built by running this same command on Windows (or a Windows CI runner).
"""

import os
import sys

import customtkinter

customtkinter_assets = os.path.join(os.path.dirname(customtkinter.__file__), "assets")

a = Analysis(
    [os.path.join(SPECPATH, "run.py")],
    pathex=[SPECPATH],
    binaries=[],
    datas=[
        (customtkinter_assets, "customtkinter/assets"),
        (os.path.join(SPECPATH, "assets"), "assets"),
    ],
    # pystray picks its backend module (_win32/_darwin/_xorg/...) at runtime
    # based on sys.platform via a dynamic import PyInstaller's static
    # analysis can't follow, so every backend has to be listed explicitly or
    # the one actually needed at runtime silently won't be bundled.
    hiddenimports=[
        "pystray._win32",
        "pystray._darwin",
        "pystray._xorg",
        "pystray._appindicator",
        "pystray._gtk",
        "pystray._dummy",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SystemMon",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Not set: branding (assets/icon.ico) is scaffolded but intentionally not
    # enabled yet (see SPEC.md open items). Set icon="assets/icon.ico" here
    # once that's ready — it only affects the exe's own file icon, not the
    # in-app window/tray icon, which are separate and still unwired too.
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SystemMon",
)

if sys.platform == "darwin":
    # Without this, macOS Finder has no way to tell the raw Mach-O binary
    # apart from a shell command, so double-clicking (or `open`) runs it
    # inside Terminal instead of launching it as a windowed app.
    app = BUNDLE(
        coll,
        name="SystemMon.app",
        icon=None,
        bundle_identifier="com.systemmon.app",
    )
