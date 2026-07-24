from __future__ import annotations

import datetime as dt
from typing import Optional

from . import autostart, logging_store
from .config import AppConfig, load_config, save_config
from .models import Host
from .monitor import STATUS_DOWN, STATUS_RECOVERED, STATUS_WARN
from .monitor_group import MonitorGroup
from .tray import TrayController
from .ui.app import SystemMonApp
from .ui.settings_page import SettingsWindow


def main() -> None:
    config = load_config()
    if not config.hosts:
        config.hosts.append(Host(name="Router", address="192.168.1.1"))
        save_config(config)

    logging_store.prune_old_logs(config.settings.retention_days)
    if autostart.is_supported():
        autostart.set_autostart(config.settings.autostart)

    def on_transition(host: Host, status: str, detail: str) -> None:
        logging_store.append_event(host.name, status, detail)
        app.after(0, app.update_host_status, host.name, status, detail)
        tray.set_status(monitors.worst_status())
        if status in (STATUS_DOWN, STATUS_WARN, STATUS_RECOVERED):
            tray.notify(f"{host.name}: {status}", detail)

    def on_tick(host: Host, latency_ms: Optional[float], loss_pct: float) -> None:
        app.after(0, app.update_host_metrics, host.name, latency_ms, loss_pct)

    monitors = MonitorGroup(on_transition=on_transition, on_tick=on_tick)

    def apply_new_config(new_config: AppConfig) -> None:
        nonlocal config
        config = new_config
        save_config(config)
        logging_store.prune_old_logs(config.settings.retention_days)
        if autostart.is_supported():
            autostart.set_autostart(config.settings.autostart)
        monitors.rebuild(config)
        app.set_hosts(config.hosts)

    def open_settings() -> None:
        SettingsWindow(app, config, on_save=apply_new_config)

    def get_history(host_name: str, window_seconds: int):
        host = next((h for h in config.hosts if h.name == host_name), None)
        if host is None:
            return [], None, None
        warning_ms = host.latency_warning_ms or config.settings.default_latency_warning_ms
        loss_pct_threshold = host.rolling_loss_pct or config.settings.default_rolling_loss_pct
        since = dt.datetime.now() - dt.timedelta(seconds=window_seconds)
        points = logging_store.read_recent_raw(host_name, since=since)
        return points, warning_ms, loss_pct_threshold

    app = SystemMonApp(config.hosts, on_open_settings=open_settings, history_provider=get_history)

    def on_show() -> None:
        app.deiconify()
        app.lift()

    def on_toggle_pause() -> None:
        tray.set_paused(monitors.toggle_pause())

    def on_quit() -> None:
        monitors.stop_all()
        tray.stop()
        app.destroy()

    tray = TrayController(on_show, on_toggle_pause, on_quit)
    app.protocol("WM_DELETE_WINDOW", app.withdraw)

    monitors.rebuild(config)

    tray.run_detached()
    app.mainloop()


if __name__ == "__main__":
    main()
