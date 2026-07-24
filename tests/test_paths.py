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


def test_app_dir_uses_executable_folder_when_frozen(tmp_path):
    fake_exe = tmp_path / "SystemMon.exe"
    fake_exe.touch()
    with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", str(fake_exe)):
        assert app_dir() == tmp_path
