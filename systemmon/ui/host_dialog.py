from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from ..branding import set_window_icon
from ..models import Host


class HostDialog(ctk.CTkToplevel):
    """Modal add/edit form for a single host's per-host settings (SPEC.md section 3)."""

    def __init__(self, parent, on_save: Callable[[Host], None], host: Optional[Host] = None):
        super().__init__(parent)
        self.title("Edit Host" if host else "Add Host")
        set_window_icon(self)
        self.geometry("380x480")
        self.transient(parent)
        self.grab_set()

        self._on_save = on_save

        self._error_label = ctk.CTkLabel(self, text="", text_color="#da3633")
        self._error_label.pack(fill="x", padx=12, pady=(8, 0))

        self._name_entry = self._add_field("Name", host.name if host else "")
        self._address_entry = self._add_field("Address", host.address if host else "")

        method_row = ctk.CTkFrame(self, fg_color="transparent")
        method_row.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(method_row, text="Method", width=170, anchor="w").pack(side="left")
        self._method_var = ctk.StringVar(value=(host.method if host else "icmp"))
        ctk.CTkSegmentedButton(
            method_row, values=["icmp", "tcp"], variable=self._method_var, command=self._on_method_change
        ).pack(side="right")

        self._port_entry = self._add_field("Port (TCP only)", str(host.port) if host and host.port else "")
        self._interval_entry = self._add_field("Ping interval (sec)", str(host.interval_sec if host else 5))

        ctk.CTkLabel(self, text="Overrides — blank uses the global default", text_color="#888888").pack(
            anchor="w", padx=12, pady=(12, 0)
        )
        self._latency_entry = self._add_field(
            "Latency warning (ms)",
            "" if not host or host.latency_warning_ms is None else str(host.latency_warning_ms),
        )
        self._miss_entry = self._add_field(
            "Consecutive miss threshold",
            "" if not host or host.consecutive_miss_threshold is None else str(host.consecutive_miss_threshold),
        )
        self._window_entry = self._add_field(
            "Rolling loss window (# pings)",
            "" if not host or host.rolling_loss_window is None else str(host.rolling_loss_window),
        )
        self._loss_pct_entry = self._add_field(
            "Rolling loss %",
            "" if not host or host.rolling_loss_pct is None else str(host.rolling_loss_pct),
        )

        self._on_method_change(self._method_var.get())

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=12, pady=12)
        ctk.CTkButton(button_row, text="Cancel", fg_color="gray40", command=self.destroy).pack(
            side="right", padx=(6, 0)
        )
        ctk.CTkButton(button_row, text="Save", command=self._save).pack(side="right")

    def _add_field(self, label: str, initial: str) -> ctk.CTkEntry:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(row, text=label, width=170, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(row)
        entry.insert(0, initial)
        entry.pack(side="right", fill="x", expand=True)
        return entry

    def _on_method_change(self, method: str) -> None:
        self._port_entry.configure(state="normal" if method == "tcp" else "disabled")

    @staticmethod
    def _parse_optional_int(text: str) -> Optional[int]:
        text = text.strip()
        return int(text) if text else None

    @staticmethod
    def _parse_optional_float(text: str) -> Optional[float]:
        text = text.strip()
        return float(text) if text else None

    def _save(self) -> None:
        name = self._name_entry.get().strip()
        address = self._address_entry.get().strip()
        method = self._method_var.get()

        if not name:
            self._error_label.configure(text="Name is required.")
            return
        if not address:
            self._error_label.configure(text="Address is required.")
            return

        try:
            port = self._parse_optional_int(self._port_entry.get())
            interval_sec = int(self._interval_entry.get().strip() or 5)
            latency_warning_ms = self._parse_optional_int(self._latency_entry.get())
            consecutive_miss_threshold = self._parse_optional_int(self._miss_entry.get())
            rolling_loss_window = self._parse_optional_int(self._window_entry.get())
            rolling_loss_pct = self._parse_optional_float(self._loss_pct_entry.get())
        except ValueError:
            self._error_label.configure(text="Numeric fields must contain valid numbers.")
            return

        if method == "tcp" and not port:
            self._error_label.configure(text="Port is required for TCP method.")
            return

        self._on_save(
            Host(
                name=name,
                address=address,
                method=method,
                port=port,
                interval_sec=interval_sec,
                latency_warning_ms=latency_warning_ms,
                consecutive_miss_threshold=consecutive_miss_threshold,
                rolling_loss_window=rolling_loss_window,
                rolling_loss_pct=rolling_loss_pct,
            )
        )
        self.destroy()
