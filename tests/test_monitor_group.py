from unittest.mock import patch

from systemmon.config import AppConfig
from systemmon.models import GlobalSettings, Host
from systemmon.monitor import STATUS_DOWN, STATUS_OK, STATUS_WARN
from systemmon.monitor_group import MonitorGroup


def _config(*names: str) -> AppConfig:
    return AppConfig(
        hosts=[Host(name=n, address="10.0.0.1", interval_sec=60) for n in names],
        settings=GlobalSettings(),
    )


def test_rebuild_creates_and_starts_a_monitor_per_host():
    group = MonitorGroup(on_transition=lambda *a: None, on_tick=lambda *a: None)
    with patch("systemmon.monitor.ping_icmp", return_value=10.0):
        group.rebuild(_config("a", "b"))
        try:
            assert set(group._monitors.keys()) == {"a", "b"}
            assert all(m._thread is not None and m._thread.is_alive() for m in group._monitors.values())
        finally:
            group.stop_all()


def test_toggle_pause_pauses_and_resumes_all_monitors():
    group = MonitorGroup(on_transition=lambda *a: None, on_tick=lambda *a: None)
    with patch("systemmon.monitor.ping_icmp", return_value=10.0):
        group.rebuild(_config("a", "b"))
        try:
            assert group.paused is False
            assert group.toggle_pause() is True
            assert all(m.is_paused() for m in group._monitors.values())

            assert group.toggle_pause() is False
            assert all(not m.is_paused() for m in group._monitors.values())
        finally:
            group.stop_all()


def test_rebuild_after_pause_keeps_new_monitors_paused():
    """The bug being fixed: recreating monitors (e.g. after a Settings save)
    must respect the current pause state instead of silently resuming."""
    group = MonitorGroup(on_transition=lambda *a: None, on_tick=lambda *a: None)
    with patch("systemmon.monitor.ping_icmp", return_value=10.0):
        group.rebuild(_config("a"))
        try:
            group.toggle_pause()
            assert group.paused is True

            group.rebuild(_config("a", "b"))
            assert all(m.is_paused() for m in group._monitors.values())
        finally:
            group.stop_all()


def test_worst_status_prioritizes_down_over_warn_over_ok():
    group = MonitorGroup(on_transition=lambda *a: None, on_tick=lambda *a: None)
    with patch("systemmon.monitor.ping_icmp", return_value=10.0):
        group.rebuild(_config("a", "b", "c"))
        try:
            assert group.worst_status() == "ok"

            group._monitors["a"].state.last_status = STATUS_WARN
            assert group.worst_status() == "warn"

            group._monitors["b"].state.last_status = STATUS_DOWN
            assert group.worst_status() == "down"

            group._monitors["a"].state.last_status = STATUS_OK
            group._monitors["b"].state.last_status = STATUS_OK
            assert group.worst_status() == "ok"
        finally:
            group.stop_all()
