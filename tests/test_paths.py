import sys
from pathlib import Path
from unittest.mock import patch

from systemmon.paths import app_dir


def test_app_dir_resolves_to_repo_root_when_not_frozen():
    repo_root = Path(__file__).resolve().parent.parent
    assert app_dir() == repo_root
    assert (app_dir() / "systemmon").is_dir()


def test_app_dir_is_independent_of_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    repo_root = Path(__file__).resolve().parent.parent
    assert app_dir() == repo_root


def test_app_dir_uses_executable_folder_when_frozen_on_windows(tmp_path):
    fake_exe = tmp_path / "SystemMon.exe"
    fake_exe.touch()
    with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(fake_exe)), patch.object(
        sys, "platform", "win32"
    ):
        assert app_dir() == tmp_path


def test_app_dir_avoids_app_bundle_when_frozen_on_macos(tmp_path):
    # Writing config/logs next to the exe would mean writing inside the
    # signed .app bundle, which breaks its signature seal on first run (see
    # paths.py docstring) — so macOS must resolve somewhere else entirely.
    fake_exe = tmp_path / "SystemMon.app" / "Contents" / "MacOS" / "SystemMon"
    fake_exe.parent.mkdir(parents=True)
    fake_exe.touch()
    fake_home = tmp_path / "home"
    with patch.object(sys, "frozen", True, create=True), patch.object(
        sys, "executable", str(fake_exe)
    ), patch.object(sys, "platform", "darwin"), patch.object(Path, "home", return_value=fake_home):
        result = app_dir()
        assert fake_exe.parent not in result.parents
        assert result == fake_home / "Library" / "Application Support" / "SystemMon"
        assert result.is_dir()
