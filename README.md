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

Grab the latest Windows build (no install needed):
[SystemMon-windows.zip](https://github.com/darkiris4/system-mon/releases/download/windows-latest/SystemMon-windows.zip)

Unzip anywhere and run `SystemMon.exe`. `config.json` and `logs/` are created next to the exe, not wherever it happens to be launched from.

This link always points at the latest build from `main` (see [Building](#building) below) — it's a rolling build for testing, not a versioned release.

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

Produces a portable one-folder build at `dist/SystemMon/`. PyInstaller does not cross-compile, so this must be run on Windows to produce a Windows build — `.github/workflows/build-windows.yml` does this automatically on every push to `main` and publishes the result as a public release under the `windows-latest` tag.

## Design notes

See [SPEC.md](SPEC.md) for the full product spec and the reasoning behind various design decisions.
