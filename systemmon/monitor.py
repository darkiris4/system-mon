from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Deque, Optional

from . import logging_store
from .models import GlobalSettings, Host
from .ping import ping_icmp, tcp_check

# Statuses shared by the raw log, events log, and tray notifications so they
# can all be grepped/matched the same way (see SPEC.md section 6).
STATUS_OK = "OK"
STATUS_WARN = "WARN"
STATUS_DOWN = "DOWN"
STATUS_RECOVERED = "RECOVERED"


@dataclass
class HostState:
    last_status: str = STATUS_OK
    last_latency_ms: Optional[float] = None
    consecutive_misses: int = 0
    recent_results: Deque[bool] = field(default_factory=lambda: deque(maxlen=200))


class HostMonitor:
    """Runs the ping loop for a single host on its own thread, at its own interval."""

    def __init__(
        self,
        host: Host,
        settings: GlobalSettings,
        on_transition: Callable[[Host, str, str], None],
        on_tick: Optional[Callable[[Host, Optional[float], float, str], None]] = None,
    ):
        self.host = host
        self.settings = settings
        self.on_transition = on_transition
        self.on_tick = on_tick
        self.state = HostState()
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def pause(self) -> None:
        self._pause_event.set()

    def resume(self) -> None:
        self._pause_event.clear()

    def is_paused(self) -> bool:
        return self._pause_event.is_set()

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if not self._pause_event.is_set():
                self._tick()
            self._stop_event.wait(self.host.interval_sec)

    def _tick(self) -> None:
        latency_ms = self._ping_once()
        success = latency_ms is not None
        self.state.recent_results.append(success)
        self.state.last_latency_ms = latency_ms
        self.state.consecutive_misses = 0 if success else self.state.consecutive_misses + 1

        loss_pct = self._rolling_loss_pct()
        status = self._evaluate_status(loss_pct)
        logging_store.append_raw_ping(self.host.name, status, latency_ms)

        if self.on_tick:
            self.on_tick(self.host, latency_ms, loss_pct, status)

        if status != self.state.last_status:
            detail = f"latency={latency_ms:.1f}ms" if latency_ms is not None else "timeout"
            self.state.last_status = status
            self.on_transition(self.host, status, detail)

    def _ping_once(self) -> Optional[float]:
        if self.host.method == "tcp":
            return tcp_check(self.host.address, self.host.port or 0)
        return ping_icmp(self.host.address)

    def _rolling_loss_pct(self) -> float:
        window = self.host.rolling_loss_window or self.settings.default_rolling_loss_window
        recent = list(self.state.recent_results)[-window:]
        if not recent:
            return 0.0
        return 100 * (1 - sum(recent) / len(recent))

    def _evaluate_status(self, loss_pct: float) -> str:
        miss_threshold = self.host.consecutive_miss_threshold or self.settings.default_consecutive_miss_threshold
        loss_pct_threshold = self.host.rolling_loss_pct or self.settings.default_rolling_loss_pct
        latency_threshold = self.host.latency_warning_ms or self.settings.default_latency_warning_ms

        if self.state.consecutive_misses >= miss_threshold:
            return STATUS_DOWN

        if loss_pct >= loss_pct_threshold:
            return STATUS_DOWN

        if self.state.last_latency_ms is not None and self.state.last_latency_ms >= latency_threshold:
            return STATUS_WARN

        if self.state.last_status in (STATUS_DOWN, STATUS_WARN):
            return STATUS_RECOVERED

        return STATUS_OK
