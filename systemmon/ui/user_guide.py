from __future__ import annotations

import customtkinter as ctk

from ..branding import set_window_icon
from ..paths import app_dir

# (tab label, body) pairs. Kept as plain strings (no markup) since this is
# rendered self-contained in-app via a CTkTextbox — no network access, no
# external docs, so nothing here may assume the user can follow a link out.
# Labels double as the tab strip text, so they're kept short.
_SECTIONS = [
    (
        "Overview",
        "SystemMon watches a list of hosts you configure and checks whether "
        "each one is reachable, on its own schedule. Each host is checked "
        "either by ICMP ping or by opening a TCP connection to a specific "
        "port, whichever you choose per host.",
    ),
    (
        "Main Window",
        "The window opens small: one row per host, showing name, status, "
        "current latency, and rolling packet-loss %. Click a row to expand "
        "it into a latency/loss history graph with the host's address and "
        "last status-change detail; click it again to collapse. Row color "
        "reflects status — default color for OK, amber for WARN, red for "
        "DOWN. Closing the window (the X button) does not quit the app — it "
        "minimizes to the tray. Use Quit from the tray menu to fully exit.",
    ),
    (
        "Hosts",
        "Settings menu > Settings... > Hosts tab > Add Host. Each host has:\n"
        "  - Name — label shown in the list and logs\n"
        "  - Address — hostname or IP\n"
        "  - Method — ICMP ping, or TCP (checks that a specific port accepts "
        "a connection; useful for hosts/firewalls that block ICMP)\n"
        "  - Port — required for TCP method\n"
        "  - Ping interval — how often this host is checked, in seconds\n"
        "  - Overrides — latency warning, consecutive-miss threshold, "
        "rolling-loss window, and rolling-loss % — each optional; leave "
        "blank to use the global default from the Global Defaults tab",
    ),
    (
        "Status Logic",
        "A host is marked DOWN if either of these is true:\n"
        "  - It has missed N consecutive checks in a row (the "
        "consecutive-miss threshold)\n"
        "  - Its packet loss over the last W checks (the rolling-loss "
        "window) is at or above the rolling-loss % threshold\n"
        "Otherwise, it's marked WARN if the latest latency is at or above "
        "the latency-warning threshold. When a host that was DOWN or WARN "
        "returns to normal, that one transition is logged and notified as "
        "RECOVERED, then it goes back to showing OK.\n\n"
        "Global defaults out of the box: 150ms latency warning, 3 "
        "consecutive misses, a 20-check rolling window, 20% rolling loss.",
    ),
    (
        "Tray & Alerts",
        "The tray icon's color mirrors the worst status across all hosts "
        "(green/amber/red), and turns gray while monitoring is paused. "
        "Right-click it for Show window, Pause/Resume monitoring, and Quit. "
        "A notification pops up whenever a host transitions to WARN, DOWN, "
        "or RECOVERED.\n\n"
        "Windows hides new tray icons in the overflow area (the \"^\" arrow) "
        "by default — that's a Windows setting, not something this app "
        "controls. Drag the icon out, or go to Settings > Personalization > "
        "Taskbar > \"Select which icons appear on the taskbar\" to make it "
        "always visible.",
    ),
    (
        "Pause/Resume",
        "Pauses or resumes monitoring for every host at once (there's no "
        "per-host pause). Available both as a button in the main window and "
        "from the tray menu — whichever one you use, the other updates to "
        "match, and the tray icon turns gray while paused.",
    ),
    (
        "Autostart",
        "Settings > Global Defaults > Autostart adds (or removes) a per-user "
        "entry so SystemMon launches automatically at login. Windows only.",
    ),
    (
        "Logs & Data",
        "Two kinds of logs are kept, both plain text/CSV so they can be "
        "opened or grepped directly:\n"
        "  - Per-host raw logs — one file per host per day, one row per "
        "check (status, timestamp, latency)\n"
        "  - A combined events log — only status changes across all hosts, "
        "one line each, so you can scan history without wading through "
        "routine OK rows\n"
        f"Current location on this machine:\n{app_dir() / 'logs'}\n\n"
        "Old logs are deleted automatically after the retention period set "
        "in Global Defaults (30 days by default). Settings and host "
        "configuration are stored in config.json next to the logs folder.",
    ),
    (
        "Troubleshooting",
        "\"Windows protected your PC\" / unknown publisher warning when "
        "launching: expected for this build — the executable isn't "
        "code-signed. Click \"More info\" then \"Run anyway\".\n\n"
        "Tray icon missing: check the taskbar overflow area first (see the "
        "Tray & Alerts tab) before assuming the app isn't running — check "
        "Task Manager for SystemMon.",
    ),
]


class UserGuideWindow(ctk.CTkToplevel):
    """Self-contained user guide, one tab per topic (no external links/network
    calls — this must work on machines with no internet access, see SPEC.md)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("SystemMon User Guide")
        set_window_icon(self)
        self.geometry("760x560")
        self.transient(parent)
        self.grab_set()

        body_font = ctk.CTkFont(size=13)

        # Matches the Hosts/Global Defaults tab layout in SettingsWindow, so
        # the guide looks like the rest of the app rather than a stray dialog.
        tabs = ctk.CTkTabview(self, segmented_button_font=ctk.CTkFont(size=11))
        tabs.pack(fill="both", expand=True, padx=12, pady=(12, 8))

        for label, body in _SECTIONS:
            tabs.add(label)
            textbox = ctk.CTkTextbox(tabs.tab(label), wrap="word", font=body_font)
            textbox.pack(fill="both", expand=True)
            textbox.insert("end", body)
            textbox.configure(state="disabled")

        tabs.set(_SECTIONS[0][0])

        ctk.CTkButton(self, text="Close", command=self.destroy).pack(pady=(0, 12))
