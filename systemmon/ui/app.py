from __future__ import annotations

import tkinter.font as tkfont
from typing import Callable, Iterable, List, Optional, Tuple

import customtkinter as ctk

from ..logging_store import RawPoint
from ..models import Host
from .graph import LatencyGraph

_STATUS_COLORS = {
    "OK": "#2ea043",
    "WARN": "#db9a04",
    "DOWN": "#da3633",
    "RECOVERED": "#2ea043",
}

# Row background reflects the host's current status; OK/RECOVERED get no
# tint so only anomalies stand out. Selection is shown via border color
# instead of swapping fg_color, so the two states don't collide. "OK" uses
# CTkFrame's own default theme color rather than "transparent" — border_color
# doesn't accept "transparent", and this way the same value works for both.
_ROW_DEFAULT_COLOR = ("gray86", "gray17")
_STATUS_ROW_COLORS = {
    "OK": _ROW_DEFAULT_COLOR,
    "WARN": "#3a2f0a",
    "DOWN": "#3a1414",
    "RECOVERED": _ROW_DEFAULT_COLOR,
}
_SELECTED_BORDER_COLOR = "#3b82f6"

# Fixed pixel widths shared by the header and every row frame. Proportional
# (weight-based) columns don't work here because the header and rows live in
# different container widgets — a plain frame vs. CTkScrollableFrame's inner
# frame, which is narrower by its scrollbar's width — so equal-weight columns
# in each would resolve to different pixel widths and drift out of alignment.
_COLUMNS = ["Name", "Address", "Status", "Latency", "Loss%", "Detail"]
_COLUMN_WIDTHS = [140, 140, 80, 90, 70, 180]
_CELL_PADX = 8
# Each cell's text must be truncated to fit, or a long value (e.g. a hostname)
# grows just that row's column — every other row and the header keep their
# original width, so only that one row drifts out of alignment. CTkLabel's
# `width=` alone doesn't prevent this: its inner text label is a sibling of
# the fixed-size canvas within the same grid cell, so unbounded text still
# forces the cell to grow regardless of the canvas's configured width.
_CELL_WIDTH = [w - 2 * _CELL_PADX for w in _COLUMN_WIDTHS]

HistoryProvider = Callable[[str, int], Tuple[List[RawPoint], Optional[float], Optional[float]]]


class SystemMonApp(ctk.CTk):
    """Main window: host table on top, selected host's latency graph below.

    Selecting a row (click anywhere on it) loads that host's recent raw
    ping history via `history_provider` and renders it in the graph panel;
    a periodic refresh keeps it current while a host stays selected.
    """

    def __init__(
        self,
        hosts: Iterable[Host],
        on_open_settings: Callable[[], None],
        history_provider: Optional[HistoryProvider] = None,
    ):
        super().__init__()
        self.title("SystemMon")
        self.geometry("840x640")

        self._rows: dict[str, dict] = {}
        self._history_provider = history_provider
        self._selected_host: Optional[str] = None
        # Match CTkLabel's actual default font (not plain tkinter's, which
        # resolves to a much smaller size) so truncation measures correctly.
        _default_font = ctk.CTkFont()
        self._cell_font = tkfont.Font(family=_default_font.cget("family"), size=_default_font.cget("size"))

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=8, pady=(8, 0))
        ctk.CTkButton(toolbar, text="Settings", width=90, command=on_open_settings).pack(side="right")

        header = ctk.CTkFrame(self, corner_radius=0)
        header.pack(fill="x", padx=8, pady=(8, 0))
        for i, text in enumerate(_COLUMNS):
            header.grid_columnconfigure(i, minsize=_COLUMN_WIDTHS[i], weight=0)
            ctk.CTkLabel(
                header, text=text, font=ctk.CTkFont(weight="bold"), anchor="w", width=_CELL_WIDTH[i]
            ).grid(row=0, column=i, sticky="w", padx=_CELL_PADX)

        # corner_radius=0 removes CTkScrollableFrame's internal border_spacing
        # inset (equal to corner_radius by default) that would otherwise push
        # its content a few pixels right of the header, which has no such inset.
        self._table = ctk.CTkScrollableFrame(self, height=180, corner_radius=0)
        self._table.pack(fill="x", padx=8, pady=8)

        self._graph = LatencyGraph(self, on_time_scale_change=self._refresh_graph)

        self.set_hosts(hosts)

        if self._history_provider:
            self.after(2000, self._periodic_refresh)

    def set_hosts(self, hosts: Iterable[Host]) -> None:
        """Rebuilds the table from scratch — used on startup and after Settings is saved."""
        for widget in self._table.winfo_children():
            widget.destroy()
        self._rows.clear()
        for host in hosts:
            self._add_row(host)
        if self._selected_host not in self._rows:
            self._selected_host = None
            self._graph.clear()
        self._update_graph_visibility()

    def _fit_text(self, text: str, column_index: int) -> str:
        """Truncates with an ellipsis so a long value can't grow this cell's column."""
        max_width = _CELL_WIDTH[column_index]
        if self._cell_font.measure(text) <= max_width:
            return text
        ellipsis = "…"
        trimmed = text
        while trimmed and self._cell_font.measure(trimmed + ellipsis) > max_width:
            trimmed = trimmed[:-1]
        return (trimmed + ellipsis) if trimmed else ellipsis

    def _add_row(self, host: Host) -> None:
        row_index = len(self._rows)
        row_frame = ctk.CTkFrame(self._table, corner_radius=0, border_width=2)
        row_frame.grid(row=row_index, column=0, columnspan=len(_COLUMNS), sticky="ew", pady=1)
        for i in range(len(_COLUMNS)):
            row_frame.grid_columnconfigure(i, minsize=_COLUMN_WIDTHS[i], weight=0)

        name_label = ctk.CTkLabel(row_frame, text=self._fit_text(host.name, 0), anchor="w", width=_CELL_WIDTH[0])
        address_label = ctk.CTkLabel(
            row_frame, text=self._fit_text(host.address, 1), anchor="w", width=_CELL_WIDTH[1]
        )
        status_label = ctk.CTkLabel(row_frame, text="...", anchor="w", width=_CELL_WIDTH[2])
        latency_label = ctk.CTkLabel(row_frame, text="-", anchor="w", width=_CELL_WIDTH[3])
        loss_label = ctk.CTkLabel(row_frame, text="-", anchor="w", width=_CELL_WIDTH[4])
        detail_label = ctk.CTkLabel(row_frame, text="", anchor="w", width=_CELL_WIDTH[5])

        widgets = [name_label, address_label, status_label, latency_label, loss_label, detail_label]
        for i, widget in enumerate(widgets):
            widget.grid(row=0, column=i, sticky="w", padx=_CELL_PADX, pady=4)

        for widget in (row_frame, *widgets):
            widget.bind("<Button-1>", lambda _event, name=host.name: self.select_host(name))

        self._rows[host.name] = {
            "frame": row_frame,
            "status": status_label,
            "latency": latency_label,
            "loss": loss_label,
            "detail": detail_label,
            "status_value": "OK",
        }
        self._style_row(host.name)

    def _style_row(self, host_name: str) -> None:
        row = self._rows.get(host_name)
        if not row:
            return
        fg = _STATUS_ROW_COLORS.get(row["status_value"], _STATUS_ROW_COLORS["OK"])
        is_selected = host_name == self._selected_host
        row["frame"].configure(fg_color=fg, border_color=_SELECTED_BORDER_COLOR if is_selected else fg)

    def select_host(self, host_name: str) -> None:
        previous = self._selected_host
        self._selected_host = host_name
        if previous and previous in self._rows:
            self._style_row(previous)
        if host_name in self._rows:
            self._style_row(host_name)
        self._update_graph_visibility()
        self._refresh_graph()

    def _update_graph_visibility(self) -> None:
        if self._selected_host:
            if not self._graph.winfo_ismapped():
                self._graph.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        else:
            self._graph.pack_forget()

    def update_host_status(self, host_name: str, status: str, detail: str) -> None:
        """Called via `after(0, ...)` from the main thread only — Tk isn't thread-safe."""
        row = self._rows.get(host_name)
        if not row:
            return
        row["status_value"] = status
        color = _STATUS_COLORS.get(status, "#999999")
        row["status"].configure(text=self._fit_text(status, 2), text_color=color)
        row["detail"].configure(text=self._fit_text(detail, 5))
        self._style_row(host_name)

    def update_host_metrics(self, host_name: str, latency_ms: Optional[float], loss_pct: float) -> None:
        """Called via `after(0, ...)` on every ping (not just status transitions)."""
        row = self._rows.get(host_name)
        if not row:
            return
        row["latency"].configure(text="timeout" if latency_ms is None else f"{latency_ms:.0f} ms")
        row["loss"].configure(text=f"{loss_pct:.0f}%")

    def _refresh_graph(self) -> None:
        if not self._selected_host or not self._history_provider:
            return
        points, warning_ms, loss_pct_threshold = self._history_provider(
            self._selected_host, self._graph.time_scale_seconds
        )
        self._graph.show(self._selected_host, points, warning_ms, loss_pct_threshold)

    def _periodic_refresh(self) -> None:
        self._refresh_graph()
        self.after(2000, self._periodic_refresh)
