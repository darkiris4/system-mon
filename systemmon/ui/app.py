from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox
from typing import Callable, Iterable, List, Optional, Tuple

import customtkinter as ctk

from .. import __version__
from ..branding import set_window_icon
from ..logging_store import RawPoint
from ..models import Host
from .graph import LatencyGraph
from .user_guide import UserGuideWindow

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
# does not accept "transparent", and this way the same value works for both.
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
#
# Address and Detail are deliberately not columns here: this table is meant
# to be a small, permanently-visible status strip (tucked on the side of the
# screen), not a full data grid. That info moves to a single label shown next
# to the graph when a host is selected, instead of taking up column width in
# every row all the time.
_COLUMNS = ["Name", "Status", "Latency", "Loss%"]
_COLUMN_WIDTHS = [130, 70, 75, 55]
_CELL_PADX = 8
# Each cell's text must be truncated to fit, or a long value (e.g. a hostname)
# grows just that row's column — every other row and the header keep their
# original width, so only that one row drifts out of alignment. CTkLabel's
# `width=` alone doesn't prevent this: its inner text label is a sibling of
# the fixed-size canvas within the same grid cell, so unbounded text still
# forces the cell to grow regardless of the canvas's configured width.
_CELL_WIDTH = [w - 2 * _CELL_PADX for w in _COLUMN_WIDTHS]
_TABLE_CONTENT_WIDTH = sum(_COLUMN_WIDTHS) + len(_COLUMNS) * 2 * _CELL_PADX

HistoryProvider = Callable[[str, int], Tuple[List[RawPoint], Optional[float], Optional[float]]]


class SystemMonApp(ctk.CTk):
    """Compact status strip meant to sit tucked on the side of the screen.

    The window opens small — just the host list — and only grows to reveal
    the latency graph when a row is clicked, shrinking back down when
    deselected. Selecting a row (click anywhere on it) loads that host's
    recent raw ping history via `history_provider`; a periodic refresh keeps
    it current while a host stays selected.
    """

    def __init__(
        self,
        hosts: Iterable[Host],
        on_open_settings: Callable[[], None],
        on_toggle_pause: Callable[[], bool],
        history_provider: Optional[HistoryProvider] = None,
        initial_paused: bool = False,
    ):
        super().__init__()
        self.title(f"SystemMon v{__version__}")
        set_window_icon(self)
        self._build_menu_bar(on_open_settings)

        self._rows: dict[str, dict] = {}
        self._history_provider = history_provider
        self._selected_host: Optional[str] = None
        self._on_toggle_pause = on_toggle_pause
        self._paused = False
        # Match CTkLabel's actual default font (not plain tkinter's, which
        # resolves to a much smaller size) so truncation measures correctly.
        _default_font = ctk.CTkFont()
        self._cell_font = tkfont.Font(family=_default_font.cget("family"), size=_default_font.cget("size"))

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=8, pady=(8, 0))
        self._pause_button = ctk.CTkButton(
            toolbar, text="Resume" if initial_paused else "Pause", width=70, command=self._handle_toggle_pause
        )
        self._pause_button.pack(side="left")

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
        self._table = ctk.CTkScrollableFrame(self, height=130, corner_radius=0)
        self._table.pack(fill="x", padx=8, pady=8)

        self._detail_label = ctk.CTkLabel(
            self, anchor="w", justify="left", wraplength=_TABLE_CONTENT_WIDTH, text=""
        )
        self._graph = LatencyGraph(self, on_time_scale_change=self._refresh_graph)

        self.set_hosts(hosts)

        # Measure the window's natural size with and without the graph/detail
        # label shown, so growing/shrinking on selection uses real numbers
        # (font metrics, theme padding) instead of hand-guessed pixel counts.
        self.update_idletasks()
        self._compact_size = (self.winfo_reqwidth(), self.winfo_reqheight())
        self._detail_label.pack(fill="x", padx=8, pady=(0, 4))
        self._graph.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.update_idletasks()
        self._expanded_size = (self.winfo_reqwidth(), self.winfo_reqheight())
        self._graph.pack_forget()
        self._detail_label.pack_forget()

        self.geometry(f"{self._compact_size[0]}x{self._compact_size[1]}")
        self.minsize(self._compact_size[0], 150)

        if self._history_provider:
            self.after(2000, self._periodic_refresh)

    def _build_menu_bar(self, on_open_settings: Callable[[], None]) -> None:
        menubar = tk.Menu(self)
        self.configure(menu=menubar)

        settings_menu = tk.Menu(menubar, tearoff=False)
        settings_menu.add_command(label="Settings...", command=on_open_settings)
        menubar.add_cascade(label="Settings", menu=settings_menu)

        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="User Guide", command=self._show_user_guide)
        help_menu.add_command(label="About SystemMon", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About SystemMon",
            f"SystemMon v{__version__}\n\n"
            "A lightweight, portable app that keeps an eye on the reachability "
            "and latency of hosts you care about.\n\n"
            "Author: Mike \"Cpup\" Hamilton",
        )

    def _show_user_guide(self) -> None:
        UserGuideWindow(self)

    def _handle_toggle_pause(self) -> None:
        # on_toggle_pause is responsible for pushing the resulting label text
        # back via set_paused_label — it's the same callback the tray uses,
        # so both surfaces stay in sync regardless of which one was clicked.
        self._on_toggle_pause()

    def set_paused_label(self, paused: bool) -> None:
        """Keeps the button in sync even when toggled from the tray menu instead."""
        self._pause_button.configure(text="Resume" if paused else "Pause")

    def set_monitoring_paused(self, paused: bool) -> None:
        """Overlays "Paused" on every row's Status column, without touching the
        underlying status_value — ticks stop while paused, so there's nothing
        else to repaint rows from until resume, when this restores the real
        per-host status immediately rather than waiting for the next tick."""
        self._paused = paused
        for host_name, row in self._rows.items():
            self._paint_status(host_name, row["status_value"])

    def set_hosts(self, hosts: Iterable[Host]) -> None:
        """Rebuilds the table from scratch — used on startup and after Settings is saved."""
        for widget in self._table.winfo_children():
            widget.destroy()
        self._rows.clear()
        for host in hosts:
            self._add_row(host)
        if self._selected_host not in self._rows:
            self._selected_host = None
            self._update_detail_label(None)
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
        status_label = ctk.CTkLabel(row_frame, text="...", anchor="w", width=_CELL_WIDTH[1])
        latency_label = ctk.CTkLabel(row_frame, text="-", anchor="w", width=_CELL_WIDTH[2])
        loss_label = ctk.CTkLabel(row_frame, text="-", anchor="w", width=_CELL_WIDTH[3])

        widgets = [name_label, status_label, latency_label, loss_label]
        for i, widget in enumerate(widgets):
            widget.grid(row=0, column=i, sticky="w", padx=_CELL_PADX, pady=4)

        for widget in (row_frame, *widgets):
            widget.bind("<Button-1>", lambda _event, name=host.name: self.select_host(name))

        self._rows[host.name] = {
            "frame": row_frame,
            "status": status_label,
            "latency": latency_label,
            "loss": loss_label,
            "status_value": "OK",
            "address": host.address,
            "last_detail": "",
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
        """Selecting the already-selected row collapses the detail view instead."""
        new_selection: Optional[str] = None if host_name == self._selected_host else host_name
        previous = self._selected_host
        self._selected_host = new_selection
        if previous and previous in self._rows:
            self._style_row(previous)
        if new_selection and new_selection in self._rows:
            self._style_row(new_selection)
        self._update_detail_label(new_selection)
        self._update_graph_visibility()
        self._refresh_graph()

    def _update_detail_label(self, host_name: Optional[str]) -> None:
        row = self._rows.get(host_name) if host_name else None
        if not row:
            self._detail_label.configure(text="")
            return
        text = row["address"]
        if row["last_detail"]:
            text += f"   ·   {row['last_detail']}"
        self._detail_label.configure(text=text)

    def _update_graph_visibility(self) -> None:
        was_visible = self._graph.winfo_ismapped()
        should_be_visible = bool(self._selected_host)
        if should_be_visible and not was_visible:
            self._detail_label.pack(fill="x", padx=8, pady=(0, 4))
            self._graph.pack(fill="both", expand=True, padx=8, pady=(0, 8))
            self.geometry(f"{self._expanded_size[0]}x{self._expanded_size[1]}")
        elif not should_be_visible and was_visible:
            self._graph.pack_forget()
            self._detail_label.pack_forget()
            self.geometry(f"{self._compact_size[0]}x{self._compact_size[1]}")

    def update_host_status(self, host_name: str, status: str, detail: str) -> None:
        """Called via `after(0, ...)` from the main thread only — Tk isn't thread-safe."""
        row = self._rows.get(host_name)
        if not row:
            return
        row["last_detail"] = detail
        self._paint_status(host_name, status)
        if host_name == self._selected_host:
            self._update_detail_label(host_name)

    def update_host_metrics(
        self, host_name: str, latency_ms: Optional[float], loss_pct: float, status: str
    ) -> None:
        """Called via `after(0, ...)` on every ping (not just status transitions)."""
        row = self._rows.get(host_name)
        if not row:
            return
        row["latency"].configure(text="timeout" if latency_ms is None else f"{latency_ms:.0f} ms")
        row["loss"].configure(text=f"{loss_pct:.0f}%")
        # Keeps the status label truthful even when nothing transitions (e.g.
        # a host that's healthy from its very first ping never fires
        # on_transition, since that path is reserved for notification-worthy
        # changes and would otherwise leave the placeholder "..." forever).
        self._paint_status(host_name, status)

    def _paint_status(self, host_name: str, status: str) -> None:
        row = self._rows.get(host_name)
        if not row:
            return
        row["status_value"] = status
        if self._paused:
            row["status"].configure(text=self._fit_text("Paused", 1), text_color="#999999")
        else:
            color = _STATUS_COLORS.get(status, "#999999")
            row["status"].configure(text=self._fit_text(status, 1), text_color=color)
        self._style_row(host_name)

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
