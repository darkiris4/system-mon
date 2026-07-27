from unittest.mock import patch

from systemmon.config import AppConfig
from systemmon.models import GlobalSettings, Host
from systemmon.monitor import STATUS_DOWN, STATUS_OK, STATUS_WARN, HostMonitor
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


def test_toggle_pause_logs_one_event_per_click():
    group = MonitorGroup(on_transition=lambda *a: None, on_tick=lambda *a: None)
    with patch.object(HostMonitor, "start", lambda self: None), patch(
        "systemmon.monitor_group.logging_store.append_event"
    ) as append_event:
        group.rebuild(_config("a"))

        group.toggle_pause()
        append_event.assert_called_once_with("", "PAUSED")

        append_event.reset_mock()
        group.toggle_pause()
        append_event.assert_called_once_with("", "RESUMED")


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


def test_rebuild_preserves_state_for_unchanged_hosts():
    """The bug being fixed: a Settings save used to recreate every HostMonitor
    from scratch, resetting last_status/consecutive_misses/rolling results to
    a fresh OK baseline — silently masking a host that was actually still
    DOWN, and swallowing the RECOVERED transition for one that had just come
    back up, on every save regardless of which host was actually edited.

    HostMonitor.start is stubbed out so this exercises rebuild()'s state
    hand-off in isolation, without a live ping thread racing the assertions.
    """
    group = MonitorGroup(on_transition=lambda *a: None, on_tick=lambda *a: None)
    with patch.object(HostMonitor, "start", lambda self: None):
        group.rebuild(_config("a", "b"))
        group._monitors["a"].state.last_status = STATUS_DOWN
        group._monitors["a"].state.consecutive_misses = 5

        # Simulate an unrelated Settings save (e.g. editing host "b", or a
        # global default) that still includes host "a" unchanged.
        group.rebuild(_config("a", "b"))

        assert group._monitors["a"].state.last_status == STATUS_DOWN
        assert group._monitors["a"].state.consecutive_misses == 5


def test_rebuild_gives_a_new_host_fresh_state():
    group = MonitorGroup(on_transition=lambda *a: None, on_tick=lambda *a: None)
    with patch.object(HostMonitor, "start", lambda self: None):
        group.rebuild(_config("a"))
        group._monitors["a"].state.last_status = STATUS_DOWN

        group.rebuild(_config("a", "b"))

        assert group._monitors["b"].state.last_status == STATUS_OK
        assert group._monitors["b"].state.consecutive_misses == 0


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
