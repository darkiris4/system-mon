from __future__ import annotations

import datetime as dt
import tkinter as tk
from typing import Callable, List, Optional

import customtkinter as ctk

from ..logging_store import RawPoint

_LINE_COLOR = "#2ea043"
_LOSS_LINE_COLOR = "#3b82f6"
_TIMEOUT_COLOR = "#da3633"
_WARN_LINE_COLOR = "#db9a04"
_AXIS_COLOR = "#888888"
_GRID_COLOR = "#333333"
_BG_COLOR = "#1e1e1e"

_PAD_LEFT, _PAD_RIGHT, _PAD_TOP, _PAD_BOTTOM = 44, 10, 10, 20
_LOSS_BUCKET_COUNT = 60

_TIME_SCALES = {"10m": 600, "1h": 3600, "8h": 8 * 3600}


class LatencyGraph(ctk.CTkFrame):
    """Latency/packet-loss history chart for the currently selected host (SPEC.md section 2).

    Renders on a plain tkinter Canvas rather than pulling in a charting
    library (e.g. matplotlib) — this was an open item in SPEC.md and a
    hand-rolled renderer is enough for this view while keeping the
    PyInstaller bundle small.
    """

    def __init__(self, parent, on_time_scale_change: Callable[[], None], height: int = 200):
        super().__init__(parent)
        self._on_time_scale_change = on_time_scale_change

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=8, pady=(4, 0))

        self._title_label = ctk.CTkLabel(header, text="", anchor="w")
        self._title_label.pack(fill="x", padx=8, pady=(0, 4))

        # Controls get their own row below the title rather than sharing one
        # row — title + both toggles together need more width than this
        # panel's host window (a narrow, tucked-on-the-side strip) has.
        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.pack(fill="x", padx=8)

        self._mode_var = ctk.StringVar(value="Latency")
        ctk.CTkSegmentedButton(
            controls,
            values=["Latency", "Loss"],
            variable=self._mode_var,
            command=self._handle_mode_change,
        ).pack(side="left", padx=(0, 8))

        self._time_scale_var = ctk.StringVar(value="1h")
        ctk.CTkSegmentedButton(
            controls,
            values=list(_TIME_SCALES.keys()),
            variable=self._time_scale_var,
            command=self._handle_time_scale_change,
        ).pack(side="left")

        self._canvas = tk.Canvas(self, height=height, bg=_BG_COLOR, highlightthickness=0)
        self._canvas.pack(fill="both", expand=True, padx=8, pady=8)
        self._canvas.bind("<Configure>", lambda _event: self._redraw())

        self._host_name: Optional[str] = None
        self._points: List[RawPoint] = []
        self._warning_ms: Optional[float] = None
        self._loss_pct_threshold: Optional[float] = None
        self._as_of: Optional[dt.datetime] = None

    @property
    def time_scale_seconds(self) -> int:
        return _TIME_SCALES[self._time_scale_var.get()]

    def _handle_time_scale_change(self, _value: str) -> None:
        self._on_time_scale_change()

    def _handle_mode_change(self, _value: str) -> None:
        self._update_title()
        self._redraw()

    def show(
        self,
        host_name: str,
        points: List[RawPoint],
        warning_ms: Optional[float],
        loss_pct_threshold: Optional[float],
    ) -> None:
        self._host_name = host_name
        self._points = points
        self._warning_ms = warning_ms
        self._loss_pct_threshold = loss_pct_threshold
        self._as_of = dt.datetime.now()
        self._update_title()
        self._redraw()

    def clear(self) -> None:
        self._host_name = None
        self._points = []
        self._as_of = None
        self._title_label.configure(text="")
        self._canvas.delete("all")

    def _update_title(self) -> None:
        metric = "packet loss" if self._mode_var.get() == "Loss" else "latency"
        self._title_label.configure(
            text=f"{self._host_name} — {metric} (last {self._time_scale_var.get()})"
        )

    def _redraw(self) -> None:
        canvas = self._canvas
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 1 or height <= 1:
            return

        if self._as_of is None:
            return

        now = self._as_of
        since = now - dt.timedelta(seconds=self.time_scale_seconds)
        plot_w = max(1, width - _PAD_LEFT - _PAD_RIGHT)
        plot_h = max(1, height - _PAD_TOP - _PAD_BOTTOM)
        t_span = max(1.0, (now - since).total_seconds())

        def x_for(timestamp: dt.datetime) -> float:
            return _PAD_LEFT + (timestamp - since).total_seconds() / t_span * plot_w

        points = [p for p in self._points if since <= p[0] <= now]

        if self._mode_var.get() == "Loss":
            self._draw_loss(canvas, points, since, now, plot_w, plot_h, x_for)
        else:
            self._draw_latency(canvas, points, plot_w, plot_h, x_for)

        canvas.create_text(_PAD_LEFT, _PAD_TOP + plot_h + 12, text=since.strftime("%H:%M"), anchor="w", fill=_AXIS_COLOR)
        canvas.create_text(
            _PAD_LEFT + plot_w, _PAD_TOP + plot_h + 12, text=now.strftime("%H:%M"), anchor="e", fill=_AXIS_COLOR
        )

    def _draw_latency(self, canvas: tk.Canvas, points: List[RawPoint], plot_w: float, plot_h: float, x_for) -> None:
        latencies = [p[1] for p in points if p[1] is not None]
        max_latency = max(latencies) if latencies else 1.0
        if self._warning_ms:
            max_latency = max(max_latency, self._warning_ms)
        max_latency = (max_latency * 1.1) or 1.0

        def y_for(latency_ms: float) -> float:
            return _PAD_TOP + plot_h - (latency_ms / max_latency * plot_h)

        for frac in (0.0, 0.5, 1.0):
            y = _PAD_TOP + plot_h * (1 - frac)
            canvas.create_line(_PAD_LEFT, y, _PAD_LEFT + plot_w, y, fill=_GRID_COLOR)
            canvas.create_text(_PAD_LEFT - 6, y, text=f"{max_latency * frac:.0f}ms", anchor="e", fill=_AXIS_COLOR)

        if self._warning_ms and self._warning_ms <= max_latency:
            y = y_for(self._warning_ms)
            canvas.create_line(_PAD_LEFT, y, _PAD_LEFT + plot_w, y, fill=_WARN_LINE_COLOR, dash=(4, 2))

        if not points:
            canvas.create_text(_PAD_LEFT + plot_w / 2, _PAD_TOP + plot_h / 2, text="No data yet", fill=_AXIS_COLOR)
            return

        # Timeouts break the line and get a short red tick along the bottom axis.
        prev_xy = None
        for timestamp, latency_ms, _status in points:
            x = x_for(timestamp)
            if latency_ms is None:
                canvas.create_line(x, _PAD_TOP + plot_h, x, _PAD_TOP + plot_h - 6, fill=_TIMEOUT_COLOR, width=2)
                prev_xy = None
                continue
            y = y_for(latency_ms)
            if prev_xy is not None:
                canvas.create_line(prev_xy[0], prev_xy[1], x, y, fill=_LINE_COLOR, width=2)
            prev_xy = (x, y)

    def _draw_loss(
        self,
        canvas: tk.Canvas,
        points: List[RawPoint],
        since: dt.datetime,
        now: dt.datetime,
        plot_w: float,
        plot_h: float,
        x_for,
    ) -> None:
        for frac in (0.0, 0.5, 1.0):
            y = _PAD_TOP + plot_h * (1 - frac)
            canvas.create_line(_PAD_LEFT, y, _PAD_LEFT + plot_w, y, fill=_GRID_COLOR)
            canvas.create_text(_PAD_LEFT - 6, y, text=f"{frac * 100:.0f}%", anchor="e", fill=_AXIS_COLOR)

        if self._loss_pct_threshold is not None:
            y = _PAD_TOP + plot_h - (self._loss_pct_threshold / 100 * plot_h)
            canvas.create_line(_PAD_LEFT, y, _PAD_LEFT + plot_w, y, fill=_WARN_LINE_COLOR, dash=(4, 2))

        if not points:
            canvas.create_text(_PAD_LEFT + plot_w / 2, _PAD_TOP + plot_h / 2, text="No data yet", fill=_AXIS_COLOR)
            return

        # Packet loss is inherently an aggregate, not a per-ping value, so it's
        # bucketed by time (rather than plotted per-ping like latency).
        bucket_span = (now - since) / _LOSS_BUCKET_COUNT
        buckets: List[List[RawPoint]] = [[] for _ in range(_LOSS_BUCKET_COUNT)]
        for point in points:
            index = int((point[0] - since) / bucket_span)
            index = min(max(index, 0), _LOSS_BUCKET_COUNT - 1)
            buckets[index].append(point)

        prev_xy = None
        for i, bucket in enumerate(buckets):
            if not bucket:
                prev_xy = None
                continue
            bucket_center = since + bucket_span * (i + 0.5)
            loss_pct = 100 * sum(1 for p in bucket if p[1] is None) / len(bucket)
            x = x_for(bucket_center)
            y = _PAD_TOP + plot_h - (loss_pct / 100 * plot_h)
            if prev_xy is not None:
                canvas.create_line(prev_xy[0], prev_xy[1], x, y, fill=_LOSS_LINE_COLOR, width=2)
            canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=_LOSS_LINE_COLOR, outline="")
            prev_xy = (x, y)
