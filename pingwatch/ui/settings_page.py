from __future__ import annotations

import copy
from typing import Callable, List

import customtkinter as ctk

from ..config import AppConfig
from ..models import GlobalSettings, Host
from .host_dialog import HostDialog


class SettingsWindow(ctk.CTkToplevel):
    """Settings page: per-host configuration plus global defaults (SPEC.md section 3).

    Edits are staged locally and only committed (via on_save) when the user
    clicks Save, so Cancel discards the whole session's edits including any
    host add/edit/delete done in this window.
    """

    def __init__(self, parent, config: AppConfig, on_save: Callable[[AppConfig], None]):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("580x560")
        self.transient(parent)
        self.grab_set()

        self._on_save = on_save
        self._hosts: List[Host] = copy.deepcopy(config.hosts)

        self._error_label = ctk.CTkLabel(self, text="", text_color="#da3633")
        self._error_label.pack(fill="x", padx=12, pady=(8, 0))

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=12, pady=8)
        tabs.add("Hosts")
        tabs.add("Global Defaults")

        self._build_hosts_tab(tabs.tab("Hosts"))
        self._build_defaults_tab(tabs.tab("Global Defaults"), config.settings)

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(fill="x", padx=12, pady=12)
        ctk.CTkButton(button_row, text="Cancel", fg_color="gray40", command=self.destroy).pack(
            side="right", padx=(6, 0)
        )
        ctk.CTkButton(button_row, text="Save", command=self._save).pack(side="right")

    # -- Hosts tab --------------------------------------------------------

    def _build_hosts_tab(self, tab) -> None:
        self._host_list_frame = ctk.CTkScrollableFrame(tab)
        self._host_list_frame.pack(fill="both", expand=True, pady=(0, 8))
        ctk.CTkButton(tab, text="Add Host", command=self._add_host).pack(anchor="w")
        self._render_host_rows()

    def _render_host_rows(self) -> None:
        for widget in self._host_list_frame.winfo_children():
            widget.destroy()
        for index, host in enumerate(self._hosts):
            row = ctk.CTkFrame(self._host_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            port_suffix = f":{host.port}" if host.method == "tcp" and host.port else ""
            ctk.CTkLabel(
                row, text=f"{host.name}  ({host.address}, {host.method}{port_suffix})", anchor="w"
            ).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(row, text="Edit", width=60, command=lambda i=index: self._edit_host(i)).pack(
                side="right", padx=(4, 0)
            )
            ctk.CTkButton(
                row, text="Delete", width=60, fg_color="#da3633", command=lambda i=index: self._delete_host(i)
            ).pack(side="right")

    def _add_host(self) -> None:
        def save(host: Host) -> None:
            self._hosts.append(host)
            self._render_host_rows()

        HostDialog(self, on_save=save)

    def _edit_host(self, index: int) -> None:
        def save(host: Host) -> None:
            self._hosts[index] = host
            self._render_host_rows()

        HostDialog(self, on_save=save, host=self._hosts[index])

    def _delete_host(self, index: int) -> None:
        del self._hosts[index]
        self._render_host_rows()

    # -- Global Defaults tab ------------------------------------------------

    def _build_defaults_tab(self, tab, settings: GlobalSettings) -> None:
        self._latency_entry = self._add_field(
            tab, "Default latency warning (ms)", str(settings.default_latency_warning_ms)
        )
        self._miss_entry = self._add_field(
            tab, "Default consecutive miss threshold", str(settings.default_consecutive_miss_threshold)
        )
        self._window_entry = self._add_field(
            tab, "Default rolling loss window (# pings)", str(settings.default_rolling_loss_window)
        )
        self._loss_pct_entry = self._add_field(
            tab, "Default rolling loss %", str(settings.default_rolling_loss_pct)
        )
        self._retention_entry = self._add_field(tab, "Log retention (days)", str(settings.retention_days))

        autostart_row = ctk.CTkFrame(tab, fg_color="transparent")
        autostart_row.pack(fill="x", pady=6)
        self._autostart_var = ctk.BooleanVar(value=settings.autostart)
        ctk.CTkCheckBox(
            autostart_row, text="Start automatically on Windows login", variable=self._autostart_var
        ).pack(anchor="w")

    def _add_field(self, tab, label: str, initial: str) -> ctk.CTkEntry:
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.pack(fill="x", pady=6)
        ctk.CTkLabel(row, text=label, width=260, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(row)
        entry.insert(0, initial)
        entry.pack(side="right", fill="x", expand=True)
        return entry

    def _save(self) -> None:
        try:
            settings = GlobalSettings(
                default_latency_warning_ms=int(self._latency_entry.get().strip()),
                default_consecutive_miss_threshold=int(self._miss_entry.get().strip()),
                default_rolling_loss_window=int(self._window_entry.get().strip()),
                default_rolling_loss_pct=float(self._loss_pct_entry.get().strip()),
                retention_days=int(self._retention_entry.get().strip()),
                autostart=self._autostart_var.get(),
            )
        except ValueError:
            self._error_label.configure(text="Global defaults must contain valid numbers.")
            return

        self._on_save(AppConfig(hosts=self._hosts, settings=settings))
        self.destroy()
