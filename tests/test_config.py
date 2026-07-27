from pathlib import Path

from systemmon.config import (
    HOST_ADDED,
    HOST_EDITED,
    HOST_REMOVED,
    SETTINGS_CHANGED,
    AppConfig,
    diff_events,
    load_config,
    save_config,
)
from systemmon.models import GlobalSettings, Host


def test_round_trip_save_and_load(tmp_path: Path):
    config = AppConfig(
        hosts=[Host(name="Router", address="192.168.1.1"), Host(name="Web", address="example.com", method="tcp", port=443)],
        settings=GlobalSettings(retention_days=14),
    )
    path = tmp_path / "config.json"

    save_config(config, path)
    loaded = load_config(path)

    assert loaded == config


def test_load_missing_file_returns_defaults(tmp_path: Path):
    loaded = load_config(tmp_path / "does-not-exist.json")
    assert loaded == AppConfig()


def test_save_uses_atomic_replace_and_leaves_no_tmp_file(tmp_path: Path):
    path = tmp_path / "config.json"
    save_config(AppConfig(), path)

    assert path.exists()
    assert not path.with_suffix(".tmp").exists()


def test_diff_events_is_empty_for_identical_configs():
    config = AppConfig(hosts=[Host(name="Router", address="192.168.1.1")], settings=GlobalSettings())
    assert diff_events(config, config) == []


def test_diff_events_reports_host_added():
    old = AppConfig(hosts=[])
    new = AppConfig(hosts=[Host(name="Web", address="example.com", method="tcp", port=443)])

    events = diff_events(old, new)

    assert events == [(HOST_ADDED, "Web", "example.com, tcp:443")]


def test_diff_events_reports_host_removed():
    old = AppConfig(hosts=[Host(name="Router", address="192.168.1.1")])
    new = AppConfig(hosts=[])

    events = diff_events(old, new)

    assert events == [(HOST_REMOVED, "Router", "192.168.1.1, icmp")]


def test_diff_events_reports_host_edited_with_changed_fields():
    old = AppConfig(hosts=[Host(name="Web", address="1.1.1.1", method="tcp", port=443)])
    new = AppConfig(hosts=[Host(name="Web", address="1.1.1.1", method="tcp", port=9999)])

    events = diff_events(old, new)

    assert events == [(HOST_EDITED, "Web", "port: 443 -> 9999")]


def test_diff_events_reports_settings_changed():
    old = AppConfig(settings=GlobalSettings(retention_days=30))
    new = AppConfig(settings=GlobalSettings(retention_days=14))

    events = diff_events(old, new)

    assert events == [(SETTINGS_CHANGED, "", "retention_days: 30 -> 14")]


def test_diff_events_treats_rename_as_remove_and_add():
    old = AppConfig(hosts=[Host(name="Router", address="192.168.1.1")])
    new = AppConfig(hosts=[Host(name="Router2", address="192.168.1.1")])

    events = diff_events(old, new)

    assert (HOST_REMOVED, "Router", "192.168.1.1, icmp") in events
    assert (HOST_ADDED, "Router2", "192.168.1.1, icmp") in events
    assert len(events) == 2
