from __future__ import annotations

import datetime as dt
import tkinter as tk
from typing import List, Optional

import customtkinter as ctk

from ..logging_store import RawPoint

_LINE_COLOR = "#2ea043"
_TIMEOUT_COLOR = "#da3633"
_WARN_LINE_COLOR = "#db9a04"
_AXIS_COLOR = "#888888"
_GRID_COLOR = "#333333"
_BG_COLOR = "#1e1e1e"

_PAD_LEFT, _PAD_RIGHT, _PAD_TOP, _PAD_BOTTOM = 44, 10, 10, 20


class LatencyGraph(ctk.CTkFrame):
    """Latency history chart for the currently selected host (SPEC.md section 2).

    Renders on a plain tkinter Canvas rather than pulling in a charting
    library (e.g. matplotlib) — this was an open item in SPEC.md and a
    hand-rolled line/timeout-marker renderer is enough for a sparkline-style
    view while keeping the PyInstaller bundle small.
    """

    def __init__(self, parent, height: int = 200):
        super().__init__(parent)
        self._title_label = ctk.CTkLabel(self, text="Select a host to view latency history", anchor="w")
        self._title_label.pack(fill="x", padx=8, pady=(4, 0))

        self._canvas = tk.Canvas(self, height=height, bg=_BG_COLOR, highlightthickness=0)
        self._canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self._canvas.bind("<Configure>", lambda _event: self._redraw())

        self._points: List[RawPoint] = []
        self._warning_ms: Optional[float] = None

    def show(self, host_name: str, points: List[RawPoint], warning_ms: Optional[float]) -> None:
        self._points = points
        self._warning_ms = warning_ms
        self._title_label.configure(text=f"{host_name} — latency (last hour)")
        self._redraw()

    def clear(self) -> None:
        self._points = []
        self._warning_ms = None
        self._title_label.configure(text="Select a host to view latency history")
        self._canvas.delete("all")

    def _redraw(self) -> None:
        canvas = self._canvas
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1 or height <= 1:
            return

        if not self._points:
            canvas.create_text(width / 2, height / 2, text="No data yet", fill=_AXIS_COLOR)
            return

        plot_w = max(1, width - _PAD_LEFT - _PAD_RIGHT)
        plot_h = max(1, height - _PAD_TOP - _PAD_BOTTOM)

        latencies = [p[1] for p in self._points if p[1] is not None]
        max_latency = max(latencies) if latencies else 1.0
        if self._warning_ms:
            max_latency = max(max_latency, self._warning_ms)
        max_latency = (max_latency * 1.1) or 1.0

        t0 = self._points[0][0].timestamp()
        t1 = self._points[-1][0].timestamp()
        t_span = max(1.0, t1 - t0)

        def x_for(timestamp: dt.datetime) -> float:
            return _PAD_LEFT + (timestamp.timestamp() - t0) / t_span * plot_w

        def y_for(latency_ms: float) -> float:
            return _PAD_TOP + plot_h - (latency_ms / max_latency * plot_h)

        for frac in (0.0, 0.5, 1.0):
            y = _PAD_TOP + plot_h * (1 - frac)
            canvas.create_line(_PAD_LEFT, y, _PAD_LEFT + plot_w, y, fill=_GRID_COLOR)
            canvas.create_text(_PAD_LEFT - 6, y, text=f"{max_latency * frac:.0f}ms", anchor="e", fill=_AXIS_COLOR)

        if self._warning_ms and self._warning_ms <= max_latency:
            y = y_for(self._warning_ms)
            canvas.create_line(_PAD_LEFT, y, _PAD_LEFT + plot_w, y, fill=_WARN_LINE_COLOR, dash=(4, 2))

        # Timeouts break the line and get a short red tick along the bottom axis.
        prev_xy = None
        for timestamp, latency_ms, _status in self._points:
            x = x_for(timestamp)
            if latency_ms is None:
                canvas.create_line(x, _PAD_TOP + plot_h, x, _PAD_TOP + plot_h - 6, fill=_TIMEOUT_COLOR, width=2)
                prev_xy = None
                continue
            y = y_for(latency_ms)
            if prev_xy is not None:
                canvas.create_line(prev_xy[0], prev_xy[1], x, y, fill=_LINE_COLOR, width=2)
            prev_xy = (x, y)

        canvas.create_text(
            _PAD_LEFT, _PAD_TOP + plot_h + 12, text=self._points[0][0].strftime("%H:%M"), anchor="w", fill=_AXIS_COLOR
        )
        canvas.create_text(
            _PAD_LEFT + plot_w,
            _PAD_TOP + plot_h + 12,
            text=self._points[-1][0].strftime("%H:%M"),
            anchor="e",
            fill=_AXIS_COLOR,
        )
