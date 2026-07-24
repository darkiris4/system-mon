from pathlib import Path

from systemmon.config import AppConfig, load_config, save_config
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
