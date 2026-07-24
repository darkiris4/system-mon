from __future__ import annotations

from typing import Callable, Dict, Optional

from .config import AppConfig
from .models import Host
from .monitor import STATUS_DOWN, STATUS_WARN, HostMonitor

TransitionCallback = Callable[[Host, str, str], None]
TickCallback = Callable[[Host, Optional[float], float, str], None]


class MonitorGroup:
    """Owns the running HostMonitor threads and the single global paused flag.

    Pause state used to live in two disconnected places — each HostMonitor's
    own pause_event, toggled per-monitor, and the tray's own checkbox flag —
    which could drift out of sync (e.g. a Settings save recreating monitors
    always unpaused, regardless of the tray's displayed state). Centralizing
    both the flag and the rebuild logic here makes "paused" a single fact.
    """

    def __init__(self, on_transition: TransitionCallback, on_tick: TickCallback):
        self._on_transition = on_transition
        self._on_tick = on_tick
        self._monitors: Dict[str, HostMonitor] = {}
        self.paused = False

    def rebuild(self, config: AppConfig) -> None:
        for monitor in self._monitors.values():
            monitor.stop()
        self._monitors = {
            host.name: HostMonitor(host, config.settings, self._on_transition, on_tick=self._on_tick)
            for host in config.hosts
        }
        for monitor in self._monitors.values():
            if self.paused:
                monitor.pause()
            monitor.start()

    def toggle_pause(self) -> bool:
        self.paused = not self.paused
        for monitor in self._monitors.values():
            monitor.pause() if self.paused else monitor.resume()
        return self.paused

    def stop_all(self) -> None:
        for monitor in self._monitors.values():
            monitor.stop()

    def worst_status(self) -> str:
        statuses = [m.state.last_status for m in self._monitors.values()]
        if any(s == STATUS_DOWN for s in statuses):
            return "down"
        if any(s == STATUS_WARN for s in statuses):
            return "warn"
        return "ok"
