# SystemMon — Product Spec

## Overview
A lightweight, portable Windows desktop app (Python) that continuously monitors the reachability and latency of user-configured hosts via ping, alerting when configurable thresholds are breached, and logging history for later review.

## Core Features

### 1. Host Monitoring
- Ping method per host: **ICMP** (default) or **TCP port-check** (fallback/alternative for hosts that block ICMP).
- Each host is pinged on its own configurable interval (not a single global interval).
- Monitoring runs continuously in the background, including when the main window is minimized to the system tray.

### 2. Main Window — Status View
- **Compact by design**: the window opens small — just a narrow host list plus a Pause/Resume and Settings button — so it can sit tucked on the side of the screen as a persistent status strip, not a full dashboard.
- **Table/list view**: one row per host — name, status, current latency, rolling packet-loss %. Address and any transition detail are intentionally left out of this compact table (see below) to keep rows narrow.
- Clicking a host row grows the window to reveal that host's **latency/packet-loss history graph**, plus a small line showing its address and last transition detail (e.g. `192.168.1.1 · latency=250ms`). Deselecting shrinks the window back down. The graph itself is a plain Canvas line/loss chart (not an embedded charting library, to keep the bundle small), toggleable between Latency and Loss% modes and 10m/1h/8h time scales; timeouts render as a red tick at the bottom axis, and a dashed line marks the host's warning threshold.
- Row color coding reflects state: default color for OK/RECOVERED, amber tint for WARN, red tint for DOWN. Selecting a row is shown via a border highlight instead, so selection and status color never collide.

### 3. Settings Page
Per-host configuration:
- Name
- Address (hostname/IP)
- Ping method (ICMP or TCP + port)
- Ping interval
- Latency threshold (override; falls back to global default if unset)
- Missed-ping threshold (override; falls back to global default if unset), defined as **both**:
  - Consecutive miss count (e.g. alert after N consecutive timeouts)
  - Rolling packet-loss % over a window of last N pings

Global defaults:
- Default latency threshold
- Default missed-ping thresholds (consecutive + rolling %)
- Log retention period (days) — applies per host, pruned automatically
- Autostart on Windows login (on/off toggle — registers/unregisters via Startup folder shortcut or registry Run key)

### 4. Alerting
On threshold breach (latency or missed-ping):
- Row/tile changes color in the main table (visual).
- A Windows system tray toast notification is triggered, tagged with the same status used in the events log (`DOWN` or `WARN`) so the notification text and log entry match.
- Alerts clear/revert automatically when the host returns to normal — this transition fires its own toast tagged `RECOVERED` (see History & Logging, below), distinct from the initial `OK` baseline state.

### 5. System Tray Behavior
- Closing the main window minimizes the app to the system tray (does not quit).
- Tray icon reflects overall status (e.g. green = all hosts OK, red = at least one host down/breached).
- Tray context menu: Show window, Pause/Resume monitoring, Quit.
- Explicit "Quit" fully stops the background process.
- **Pause/Resume is global only** (all hosts at once), not per-host. It's also exposed as a visible button directly in the main window, not just the tray menu, since the tray right-click menu alone wasn't discoverable enough. Both surfaces stay in sync — whichever one is used to toggle, the other reflects the new state.

### 6. History & Logging
- **Raw ping data**: logged per host, per day as CSV files (e.g. `logs/<host>/2026-07-24.csv`), one row per ping. Status leads each row for easy grepping: `status,timestamp,latency`. Used to drive the latency history graph (plus optionally an in-memory buffer for the most recent points to avoid disk churn on every ping).
- **Events log**: a separate, low-volume log that only records state transitions — not every ping — so problems can be found without scrolling through routine OK rows. Written on: down→up, up→down, warning start/end. Uses distinct statuses from the raw log (e.g. `RECOVERED` vs plain `OK`) so bounces can be grepped separately from steady-state. Combined across all hosts into one file (e.g. `logs/events.log`), sorted by time, with host name included per line, so the whole fleet's history can be scanned at once.
- Retention is configurable (default TBD, e.g. 30 days); per-day raw CSV files are pruned by deleting whole files older than the retention window (no in-file filtering needed). Events log is pruned/rotated on the same schedule.

### 7. Persistence
- App settings (hosts, thresholds, intervals, retention, autostart flag) persisted to a local config file (e.g. `config.json`) alongside the portable app folder — no registry dependency except the optional autostart entry.

## Technical Stack
- **Language**: Python
- **UI**: CustomTkinter
- **Packaging**: PyInstaller, one-folder (portable) build — no installer, no registry writes except optional autostart toggle.
- **Ping**: `subprocess` wrapping Windows `ping.exe` for ICMP (avoids needing raw-socket/admin privileges); `socket` for TCP port-check fallback.
- **Storage**: JSON for settings/config; CSV files per host for history logs.
- **Notifications**: Windows toast via a lightweight tray/notification library compatible with the packaged exe.

## Open Items to Decide During Build
- Icon/branding assets for the tray icon and app window. Scaffolded but not enabled: a placeholder mark exists at `assets/icon.png` / `assets/icon.ico`, with loader functions in `systemmon/branding.py` (`set_window_icon`, `load_tray_icon_image`) — neither is currently called from `main.py`/`app.py`/`tray.py`. Wiring in the tray version also needs a design for how live status color (green/amber/red) is still conveyed once the icon is a fixed brand mark instead of a plain colored dot.

## Out of Scope (v1)
- Remote/multi-machine monitoring or centralized server.
- Non-Windows platforms.
- Authentication/multi-user support.
