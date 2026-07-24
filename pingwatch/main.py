from __future__ import annotations

from . import autostart, logging_store
from .config import AppConfig, load_config, save_config
from .models import Host
from .monitor import STATUS_DOWN, STATUS_RECOVERED, STATUS_WARN, HostMonitor
from .tray import TrayController
from .ui.app import PingWatchApp
from .ui.settings_page import SettingsWindow


def main() -> None:
    config = load_config()
    if not config.hosts:
        config.hosts.append(Host(name="Router", address="192.168.1.1"))
        save_config(config)

    logging_store.prune_old_logs(config.settings.retention_days)
    if autostart.is_supported():
        autostart.set_autostart(config.settings.autostart)

    monitors: dict[str, HostMonitor] = {}

    def worst_status() -> str:
        statuses = [m.state.last_status for m in monitors.values()]
        if any(s == STATUS_DOWN for s in statuses):
            return "down"
        if any(s == STATUS_WARN for s in statuses):
            return "warn"
        return "ok"

    def on_transition(host: Host, status: str, detail: str) -> None:
        logging_store.append_event(host.name, status, detail)
        app.after(0, app.update_host_status, host.name, status, detail)
        tray.set_status(worst_status())
        if status in (STATUS_DOWN, STATUS_WARN, STATUS_RECOVERED):
            tray.notify(f"{host.name}: {status}", detail)

    def rebuild_monitors(new_config: AppConfig) -> None:
        for m in monitors.values():
            m.stop()
        monitors.clear()
        for host in new_config.hosts:
            monitors[host.name] = HostMonitor(host, new_config.settings, on_transition)
        for m in monitors.values():
            m.start()

    def apply_new_config(new_config: AppConfig) -> None:
        nonlocal config
        config = new_config
        save_config(config)
        logging_store.prune_old_logs(config.settings.retention_days)
        if autostart.is_supported():
            autostart.set_autostart(config.settings.autostart)
        rebuild_monitors(config)
        app.set_hosts(config.hosts)

    def open_settings() -> None:
        SettingsWindow(app, config, on_save=apply_new_config)

    def get_history(host_name: str):
        host = next((h for h in config.hosts if h.name == host_name), None)
        if host is None:
            return [], None
        warning_ms = host.latency_warning_ms or config.settings.default_latency_warning_ms
        return logging_store.read_recent_raw(host_name), warning_ms

    app = PingWatchApp(config.hosts, on_open_settings=open_settings, history_provider=get_history)

    def on_show() -> None:
        app.deiconify()
        app.lift()

    def on_toggle_pause() -> None:
        for m in monitors.values():
            m.resume() if m.is_paused() else m.pause()

    def on_quit() -> None:
        for m in monitors.values():
            m.stop()
        tray.stop()
        app.destroy()

    tray = TrayController(on_show, on_toggle_pause, on_quit)
    app.protocol("WM_DELETE_WINDOW", app.withdraw)

    rebuild_monitors(config)

    tray.run_detached()
    app.mainloop()


if __name__ == "__main__":
    main()
