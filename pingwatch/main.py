from __future__ import annotations

from . import logging_store
from .config import load_config, save_config
from .models import Host
from .monitor import STATUS_DOWN, STATUS_RECOVERED, STATUS_WARN, HostMonitor
from .tray import TrayController
from .ui.app import PingWatchApp


def main() -> None:
    config = load_config()
    if not config.hosts:
        config.hosts.append(Host(name="Router", address="192.168.1.1"))
        save_config(config)

    logging_store.prune_old_logs(config.settings.retention_days)

    app = PingWatchApp(config.hosts)

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

    monitors.update(
        {host.name: HostMonitor(host, config.settings, on_transition) for host in config.hosts}
    )

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

    for m in monitors.values():
        m.start()

    tray.run_detached()
    app.mainloop()


if __name__ == "__main__":
    main()
