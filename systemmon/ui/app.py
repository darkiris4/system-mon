from __future__ import annotations

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

_SELECTED_ROW_COLOR = "#2b2b40"
_UNSELECTED_ROW_COLOR = "transparent"

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
        self.geometry("780x640")

        self._rows: dict[str, dict] = {}
        self._history_provider = history_provider
        self._selected_host: Optional[str] = None

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=8, pady=(8, 0))
        ctk.CTkButton(toolbar, text="Settings", width=90, command=on_open_settings).pack(side="right")

        header = ctk.CTkFrame(self)
        header.pack(fill="x", padx=8, pady=(8, 0))
        for i, text in enumerate(["Name", "Address", "Status", "Latency", "Detail"]):
            ctk.CTkLabel(header, text=text, font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=i, sticky="w", padx=8
            )

        self._table = ctk.CTkScrollableFrame(self, height=180)
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

    def _add_row(self, host: Host) -> None:
        row_index = len(self._rows)
        row_frame = ctk.CTkFrame(self._table, fg_color=_UNSELECTED_ROW_COLOR)
        row_frame.grid(row=row_index, column=0, columnspan=5, sticky="ew", pady=1)
        for i in range(5):
            row_frame.grid_columnconfigure(i, weight=1, uniform="cols")

        name_label = ctk.CTkLabel(row_frame, text=host.name, anchor="w")
        address_label = ctk.CTkLabel(row_frame, text=host.address, anchor="w")
        status_label = ctk.CTkLabel(row_frame, text="...", anchor="w")
        latency_label = ctk.CTkLabel(row_frame, text="-", anchor="w")
        detail_label = ctk.CTkLabel(row_frame, text="", anchor="w")

        widgets = [name_label, address_label, status_label, latency_label, detail_label]
        for i, widget in enumerate(widgets):
            widget.grid(row=0, column=i, sticky="w", padx=8, pady=4)

        for widget in (row_frame, *widgets):
            widget.bind("<Button-1>", lambda _event, name=host.name: self.select_host(name))

        self._rows[host.name] = {
            "frame": row_frame,
            "status": status_label,
            "latency": latency_label,
            "detail": detail_label,
        }

        if self._selected_host == host.name:
            row_frame.configure(fg_color=_SELECTED_ROW_COLOR)

    def select_host(self, host_name: str) -> None:
        if self._selected_host and self._selected_host in self._rows:
            self._rows[self._selected_host]["frame"].configure(fg_color=_UNSELECTED_ROW_COLOR)
        self._selected_host = host_name
        if host_name in self._rows:
            self._rows[host_name]["frame"].configure(fg_color=_SELECTED_ROW_COLOR)
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
        color = _STATUS_COLORS.get(status, "#999999")
        row["status"].configure(text=status, text_color=color)
        row["detail"].configure(text=detail)

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
