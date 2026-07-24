from unittest.mock import patch

from pingwatch.models import GlobalSettings, Host
from pingwatch.monitor import STATUS_DOWN, STATUS_OK, STATUS_RECOVERED, STATUS_WARN, HostMonitor


def _make_monitor(transitions: list, **host_kwargs) -> HostMonitor:
    host = Host(name="test-host", address="10.0.0.1", **host_kwargs)
    settings = GlobalSettings(
        default_latency_warning_ms=100,
        default_consecutive_miss_threshold=3,
        default_rolling_loss_window=10,
        default_rolling_loss_pct=50.0,
    )

    def on_transition(host, status, detail):
        transitions.append(status)

    return HostMonitor(host, settings, on_transition)


def test_stays_ok_on_successful_pings():
    transitions: list = []
    monitor = _make_monitor(transitions)
    with patch("pingwatch.monitor.ping_icmp", return_value=10.0), patch(
        "pingwatch.logging_store.append_raw_ping"
    ):
        monitor._tick()
        monitor._tick()

    assert transitions == []
    assert monitor.state.last_status == STATUS_OK


def test_transitions_to_down_after_consecutive_misses():
    transitions: list = []
    monitor = _make_monitor(transitions)
    with patch("pingwatch.monitor.ping_icmp", return_value=None), patch(
        "pingwatch.logging_store.append_raw_ping"
    ):
        monitor._tick()
        monitor._tick()
        monitor._tick()

    assert transitions == [STATUS_DOWN]
    assert monitor.state.last_status == STATUS_DOWN


def test_transitions_to_warn_when_latency_exceeds_threshold():
    transitions: list = []
    monitor = _make_monitor(transitions)
    with patch("pingwatch.monitor.ping_icmp", return_value=250.0), patch(
        "pingwatch.logging_store.append_raw_ping"
    ):
        monitor._tick()

    assert transitions == [STATUS_WARN]


def test_recovers_after_down():
    # rolling_loss_pct=100 isolates this test to the consecutive-miss path;
    # otherwise a few stale failures still sitting in the rolling window
    # would keep tripping the loss-percentage check and mask the recovery.
    transitions: list = []
    monitor = _make_monitor(transitions, rolling_loss_pct=100)
    with patch("pingwatch.logging_store.append_raw_ping"):
        with patch("pingwatch.monitor.ping_icmp", return_value=None):
            monitor._tick()
            monitor._tick()
            monitor._tick()
        with patch("pingwatch.monitor.ping_icmp", return_value=10.0):
            monitor._tick()
            monitor._tick()

    assert transitions == [STATUS_DOWN, STATUS_RECOVERED, STATUS_OK]
