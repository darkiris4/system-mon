from __future__ import annotations

from typing import Iterable

import customtkinter as ctk

from ..models import Host

_STATUS_COLORS = {
    "OK": "#2ea043",
    "WARN": "#db9a04",
    "DOWN": "#da3633",
    "RECOVERED": "#2ea043",
}


class PingWatchApp(ctk.CTk):
    """Main window: one row per host (name, address, status, latency, detail).

    Selecting a row for the latency history graph and the settings page are
    not built yet — this is a scaffold that establishes wiring for status
    updates coming from the background monitor threads.
    """

    def __init__(self, hosts: Iterable[Host]):
        super().__init__()
        self.title("PingWatch")
        self.geometry("760x420")

        self._rows: dict[str, dict[str, ctk.CTkLabel]] = {}

        header = ctk.CTkFrame(self)
        header.pack(fill="x", padx=8, pady=(8, 0))
        for i, text in enumerate(["Name", "Address", "Status", "Latency", "Detail"]):
            ctk.CTkLabel(header, text=text, font=ctk.CTkFont(weight="bold")).grid(
                row=0, column=i, sticky="w", padx=8
            )

        self._table = ctk.CTkScrollableFrame(self)
        self._table.pack(fill="both", expand=True, padx=8, pady=8)

        for host in hosts:
            self._add_row(host)

    def _add_row(self, host: Host) -> None:
        row_index = len(self._rows)
        name_label = ctk.CTkLabel(self._table, text=host.name)
        address_label = ctk.CTkLabel(self._table, text=host.address)
        status_label = ctk.CTkLabel(self._table, text="...")
        latency_label = ctk.CTkLabel(self._table, text="-")
        detail_label = ctk.CTkLabel(self._table, text="")

        for i, widget in enumerate([name_label, address_label, status_label, latency_label, detail_label]):
            widget.grid(row=row_index, column=i, sticky="w", padx=8, pady=2)

        self._rows[host.name] = {"status": status_label, "latency": latency_label, "detail": detail_label}

    def update_host_status(self, host_name: str, status: str, detail: str) -> None:
        """Called via `after(0, ...)` from the main thread only — Tk isn't thread-safe."""
        row = self._rows.get(host_name)
        if not row:
            return
        color = _STATUS_COLORS.get(status, "#999999")
        row["status"].configure(text=status, text_color=color)
        row["detail"].configure(text=detail)
