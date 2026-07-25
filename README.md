# SystemMon

A lightweight, portable Windows desktop app that keeps an eye on the reachability and latency of hosts you care about. It opens as a small status strip you can tuck on the side of your screen — click a host for a closer look with a latency/packet-loss history graph.

## Features

- Per-host ICMP or TCP port-check monitoring, each on its own ping interval
- Compact status view: name, status, live latency, rolling packet-loss %
- Click a host to see its latency/loss history graph (10m/1h/8h windows)
- Configurable thresholds — latency, consecutive misses, rolling packet loss % — globally or per host
- Tray icon reflects overall status; toast notifications on state changes
- Pause/resume monitoring from the main window or the tray, kept in sync
- Per-host-per-day CSV logs, plus a combined `events.log` for quick troubleshooting without wading through routine pings
- Optional autostart on Windows login

## Download

Grab the latest build (no install needed):
- Windows: [SystemMon-windows.zip](https://github.com/darkiris4/system-mon/releases/download/windows-latest/SystemMon-windows.zip)
- macOS: [SystemMon-macos.zip](https://github.com/darkiris4/system-mon/releases/download/macos-latest/SystemMon-macos.zip)

Unzip anywhere and run `SystemMon.exe` (Windows) or `SystemMon.app` (macOS). `config.json` and `logs/` are created next to it, not wherever it happens to be launched from.

The macOS build is unsigned and not notarized, so Gatekeeper will refuse a plain double-click the first time. Right-click `SystemMon.app` and choose **Open**, or run `xattr -dr com.apple.quarantine SystemMon.app` first.

These links always point at the latest build from `main` (see [Building](#building) below) — rolling builds for testing, not versioned releases.

## Development

Requires Python 3.12+.

```
python -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows
pip install -r requirements-dev.txt
python run.py
```

Run the test suite with `pytest`.

## Building

```
pyinstaller systemmon.spec
```

Produces a portable one-folder build at `dist/SystemMon/` (Windows/Linux) or a `dist/SystemMon.app` bundle (macOS). PyInstaller does not cross-compile, so each platform's build must run on that platform — `.github/workflows/build-windows.yml` and `.github/workflows/build-macos.yml` do this automatically on every push to `main` and publish the results as public releases under the `windows-latest` and `macos-latest` tags, respectively.

## Design notes

See [SPEC.md](SPEC.md) for the full product spec and the reasoning behind various design decisions.
